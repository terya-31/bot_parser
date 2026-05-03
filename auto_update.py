# auto_update.py - скрипт для автоматического обновления данных
import subprocess
import sys
import os
from datetime import datetime

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    sys.stdout.flush()

def run_update():
    log_message("🚀 Начинаю обновление данных...")
    
    # 1. Запускаем парсер
    log_message("📊 Запускаю парсер...")
    result = subprocess.run([sys.executable, "parser.py"], capture_output=True, text=True)
    
    if result.returncode != 0:
        log_message(f"❌ Ошибка парсера: {result.stderr}")
        return False
    
    log_message("✅ Парсер завершён")
    
    # 2. Запускаем анализ в автоматическом режиме
    log_message("📈 Запускаю анализ...")
    result = subprocess.run([sys.executable, "ind_analyze.py", "--auto"], capture_output=True, text=True)
    
    if result.returncode != 0:
        log_message(f"❌ Ошибка анализа: {result.stderr}")
        return False
    
    log_message("✅ Анализ завершён")
    log_message("🎉 Обновление данных успешно завершено!")
    return True

if __name__ == "__main__":
    success = run_update()
    sys.exit(0 if success else 1)