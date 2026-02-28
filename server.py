#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
server.py - Единый сервер для запуска Telegram бота и Mini App
Запускает одновременно:
- Telegram бота (long polling)
- Flask веб-сервер для Mini App и админ панели
"""

import os
import sys
import time
import threading
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# ============================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================

# Создаем папку для логов
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Настройка логгера
log_file = os.path.join(log_dir, 'server.log')
handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logger = logging.getLogger('Server')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Добавляем вывод в консоль
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console)

# ============================================
# ИМПОРТЫ
# ============================================

try:
    # Импортируем компоненты из bot.py
    from bot import (
        bot, app,  # Telegram бот и Flask приложение
        stats, users, subs, attacks,  # Данные
        save_data,  # Функция сохранения
        ADMIN_ID, FLOOD_URLS  # Конфиги
    )
    logger.info("✅ Модули из bot.py успешно импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта bot.py: {e}")
    logger.error("Убедитесь, что bot.py находится в той же папке")
    sys.exit(1)

# ============================================
# КОНФИГУРАЦИЯ СЕРВЕРА
# ============================================

# Порт для веб-сервера (bothost.ru использует порт 5000 по умолчанию)
WEB_PORT = int(os.environ.get('PORT', 5000))

# Хост (0.0.0.0 для доступа извне)
WEB_HOST = '0.0.0.0'

# Режим отладки (выключен для продакшена)
DEBUG = False

# ============================================
# КЛАСС УПРАВЛЕНИЯ СЕРВЕРОМ
# ============================================

class ServerManager:
    def __init__(self):
        self.bot_thread = None
        self.web_thread = None
        self.running = True
        self.start_time = datetime.now()
        
    def run_bot(self):
        """Запуск Telegram бота в отдельном потоке"""
        thread_name = threading.current_thread().name
        logger.info(f"🤖 Запуск Telegram бота в потоке {thread_name}")
        
        while self.running:
            try:
                logger.info("🔄 Бот начинает polling...")
                bot.infinity_polling(timeout=30, long_polling_timeout=30)
            except Exception as e:
                logger.error(f"❌ Ошибка в работе бота: {e}")
                if self.running:
                    logger.info("⏳ Перезапуск бота через 5 секунд...")
                    time.sleep(5)
                else:
                    break
                    
        logger.info("🛑 Поток бота остановлен")
    
    def run_web(self):
        """Запуск веб-сервера Flask в отдельном потоке"""
        thread_name = threading.current_thread().name
        logger.info(f"🌐 Запуск веб-сервера в потоке {thread_name}")
        
        try:
            # Для bothost.ru нужно слушать все интерфейсы
            logger.info(f"🚀 Веб-сервер запущен на http://{WEB_HOST}:{WEB_PORT}")
            logger.info(f"📱 Mini App доступен по адресу: http://localhost:{WEB_PORT}")
            logger.info(f"🔗 Для внешнего доступа используйте домен bothost.ru")
            
            # Запускаем Flask приложение
            app.run(
                host=WEB_HOST,
                port=WEB_PORT,
                debug=DEBUG,
                threaded=True,
                use_reloader=False  # Отключаем перезагрузчик
            )
        except Exception as e:
            logger.error(f"❌ Критическая ошибка веб-сервера: {e}")
            self.running = False
    
    def start(self):
        """Запуск всех компонентов"""
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК СЕРВЕРА PIZZADELIVERY")
        logger.info("=" * 60)
        
        # Информация о системе
        logger.info(f"📊 Статистика:")
        logger.info(f"  👥 Пользователей: {stats.get('total_users', 0)}")
        logger.info(f"  🔥 Атак: {stats.get('total_attacks', 0)}")
        logger.info(f"  🛠 Сервисов: {len(FLOOD_URLS)}")
        logger.info(f"  👑 Админ ID: {ADMIN_ID}")
        
        # Создаем и запускаем потоки
        logger.info("🔄 Создание потоков...")
        
        # Поток для бота
        self.bot_thread = threading.Thread(
            target=self.run_bot,
            name="BotThread",
            daemon=True
        )
        
        # Поток для веб-сервера
        self.web_thread = threading.Thread(
            target=self.run_web,
            name="WebThread",
            daemon=True
        )
        
        # Запускаем потоки
        logger.info("▶️ Запуск потоков...")
        self.bot_thread.start()
        self.web_thread.start()
        
        logger.info("✅ Все компоненты запущены")
        logger.info("=" * 60)
        
        # Держим главный поток живым
        try:
            while self.running:
                # Проверяем состояние потоков каждые 10 секунд
                time.sleep(10)
                
                if not self.bot_thread.is_alive():
                    logger.warning("⚠️ Поток бота не отвечает, перезапуск...")
                    self.bot_thread = threading.Thread(
                        target=self.run_bot,
                        name="BotThread",
                        daemon=True
                    )
                    self.bot_thread.start()
                
                if not self.web_thread.is_alive():
                    logger.warning("⚠️ Поток веб-сервера не отвечает, перезапуск...")
                    self.web_thread = threading.Thread(
                        target=self.run_web,
                        name="WebThread",
                        daemon=True
                    )
                    self.web_thread.start()
                
                # Автосохранение данных каждые 60 секунд
                try:
                    save_data()
                    logger.debug("💾 Данные автосохранены")
                except Exception as e:
                    logger.error(f"❌ Ошибка автосохранения: {e}")
                    
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        """Корректное завершение работы"""
        logger.info("🛑 Получен сигнал завершения...")
        self.running = False
        
        logger.info("💾 Сохранение данных...")
        try:
            save_data()
            logger.info("✅ Данные сохранены")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения данных: {e}")
        
        # Останавливаем бота
        logger.info("🤖 Остановка бота...")
        try:
            bot.stop_polling()
        except:
            pass
        
        # Останавливаем веб-сервер
        logger.info("🌐 Остановка веб-сервера...")
        try:
            # Функция остановки Flask
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
        except:
            pass
        
        logger.info("👋 Сервер завершил работу")
        logger.info("=" * 60)

# ============================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ МОНИТОРИНГА
# ============================================

def get_server_status():
    """Получение статуса сервера"""
    uptime = datetime.now() - server.start_time
    return {
        "status": "running" if server.running else "stopped",
        "uptime": str(uptime).split('.')[0],
        "bot_alive": server.bot_thread.is_alive() if server.bot_thread else False,
        "web_alive": server.web_thread.is_alive() if server.web_thread else False,
        "stats": {
            "users": stats.get('total_users', 0),
            "attacks": stats.get('total_attacks', 0),
            "requests": stats.get('total_requests', 0)
        }
    }

# ============================================
# ЗАПУСК СЕРВЕРА
# ============================================

if __name__ == "__main__":
    # Создаем менеджер сервера
    server = ServerManager()
    
    # Обработка сигналов для корректного завершения
    import signal
    
    def signal_handler(signum, frame):
        logger.info(f"📡 Получен сигнал {signum}")
        server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Запускаем сервер
    try:
        server.start()
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка: {e}")
        server.shutdown()
        sys.exit(1)