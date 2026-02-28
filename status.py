#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
status.py - Скрипт для проверки статуса сервера
Запуск: python status.py
"""

import os
import sys
import json
import requests
from datetime import datetime

def check_server():
    """Проверка статуса сервера"""
    
    # Проверяем наличие bot.py
    if not os.path.exists('bot.py'):
        print("❌ bot.py не найден")
        return False
    
    # Проверяем наличие web/index.html
    if not os.path.exists('web/index.html'):
        print("❌ web/index.html не найден")
        return False
    
    # Проверяем наличие баз данных
    dbs = ['users.json', 'stats.json', 'subs.json', 'attacks.json']
    for db in dbs:
        if os.path.exists(db):
            size = os.path.getsize(db)
            print(f"✅ {db} - {size} байт")
        else:
            print(f"⚠️ {db} не найден (будет создан при запуске)")
    
    # Пытаемся подключиться к веб-серверу
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        if response.status_code == 200:
            print("✅ Веб-сервер отвечает на порту 5000")
        else:
            print(f"⚠️ Веб-сервер вернул код {response.status_code}")
    except:
        print("❌ Веб-сервер не доступен на порту 5000")
    
    print("\n📊 Информация:")
    if os.path.exists('stats.json'):
        with open('stats.json', 'r') as f:
            stats = json.load(f)
            print(f"  👥 Пользователей: {stats.get('total_users', 0)}")
            print(f"  🔥 Атак: {stats.get('total_attacks', 0)}")
            print(f"  📨 Запросов: {stats.get('total_requests', 0)}")
    
    return True

def check_logs():
    """Проверка логов"""
    log_file = 'logs/server.log'
    if os.path.exists(log_file):
        size = os.path.getsize(log_file)
        print(f"✅ Лог файл: {log_file} - {size} байт")
        
        # Показываем последние 10 строк
        print("\n📋 Последние 10 строк лога:")
        with open(log_file, 'r') as f:
            lines = f.readlines()[-10:]
            for line in lines:
                print(f"  {line.strip()}")
    else:
        print("❌ Лог файл не найден")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 ПРОВЕРКА СТАТУСА СЕРВЕРА")
    print("=" * 60)
    
    check_server()
    print("-" * 60)
    check_logs()
    print("=" * 60)