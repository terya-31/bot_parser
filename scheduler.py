# scheduler.py
import time
import subprocess
from datetime import datetime

def run_update():
    print(f"[{datetime.now()}] Запуск обновления...")
    subprocess.run(["python", "auto_update.py"])

def main():
    print("🕐 Планировщик запущен. Будет выполняться каждый день в 5:00")
    
    while True:
        now = datetime.now()
        # Следующий запуск в 5:00
        next_run = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now.hour >= 5:
            next_run = next_run.replace(day=now.day + 1)
        
        # Ждём до следующего запуска
        wait_seconds = (next_run - now).total_seconds()
        print(f"[{now}] Следующее обновление в {next_run} (через {wait_seconds/3600:.1f} часов)")
        time.sleep(wait_seconds)
        
        run_update()
        # Небольшая пауза после обновления
        time.sleep(60)

if __name__ "__main__":
    main()