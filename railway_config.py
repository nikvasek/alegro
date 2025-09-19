#!/usr/bin/env python3
"""
Railway-специфичная конфигурация для предотвращения зависаний
"""

import os
import psutil
import signal
import time
import threading
from pathlib import Path

class RailwayResourceManager:
    """Менеджер ресурсов для Railway deployment"""
    
    def __init__(self):
        self.max_memory_percent = 85
        self.max_chrome_processes = 5
        self.max_temp_files = 500
        self.cleanup_interval = 300  # 5 минут
        self.running = True
        
    def monitor_resources(self):
        """Мониторинг ресурсов и принудительная очистка"""
        while self.running:
            try:
                # Проверка памяти
                memory = psutil.virtual_memory()
                if memory.percent > self.max_memory_percent:
                    print(f"🚨 Критическое использование памяти: {memory.percent}%")
                    self.emergency_cleanup()
                
                # Проверка Chrome процессов
                chrome_count = len([p for p in psutil.process_iter() if 'chrome' in p.name().lower()])
                if chrome_count > self.max_chrome_processes:
                    print(f"🚨 Слишком много Chrome процессов: {chrome_count}")
                    self.kill_old_chrome_processes()
                
                # Проверка временных файлов
                temp_count = len(list(Path('temp_files').rglob('*'))) if Path('temp_files').exists() else 0
                if temp_count > self.max_temp_files:
                    print(f"🚨 Слишком много временных файлов: {temp_count}")
                    self.cleanup_temp_files()
                    
                time.sleep(60)  # Проверка каждую минуту
                
            except Exception as e:
                print(f"❌ Ошибка мониторинга: {e}")
                time.sleep(60)
    
    def emergency_cleanup(self):
        """Экстренная очистка ресурсов"""
        print("🧹 Экстренная очистка ресурсов...")
        
        # Принудительная сборка мусора
        import gc
        gc.collect()
        
        # Убиваем старые Chrome процессы
        self.kill_old_chrome_processes()
        
        # Очищаем временные файлы
        self.cleanup_temp_files()
        
        print("✅ Экстренная очистка завершена")
    
    def kill_old_chrome_processes(self):
        """Убивает старые Chrome процессы"""
        killed = 0
        current_time = time.time()
        
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    # Убиваем процессы старше 20 минут
                    if current_time - proc.info['create_time'] > 1200:
                        proc.kill()
                        killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if killed > 0:
            print(f"🔪 Убито {killed} старых Chrome процессов")
    
    def cleanup_temp_files(self):
        """Очистка старых временных файлов"""
        temp_dir = Path('temp_files')
        if not temp_dir.exists():
            return
            
        cleaned = 0
        current_time = time.time()
        
        for file_path in temp_dir.rglob('*'):
            try:
                if file_path.is_file():
                    # Удаляем файлы старше 30 минут
                    if current_time - file_path.stat().st_mtime > 1800:
                        file_path.unlink()
                        cleaned += 1
            except:
                pass
        
        if cleaned > 0:
            print(f"🗑️ Очищено {cleaned} временных файлов")
    
    def start_monitoring(self):
        """Запуск мониторинга в отдельном потоке"""
        monitor_thread = threading.Thread(target=self.monitor_resources, daemon=True)
        monitor_thread.start()
        print("🔍 Запущен мониторинг ресурсов для Railway")
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.running = False

# Глобальный экземпляр менеджера
railway_manager = None

def setup_railway_limits():
    """Настройка ограничений для Railway"""
    global railway_manager
    
    if os.getenv('RAILWAY_ENVIRONMENT'):
        print("🚂 Обнаружена Railway среда - настройка ограничений ресурсов")
        railway_manager = RailwayResourceManager()
        railway_manager.start_monitoring()
        
        # Настройка сигналов для корректного завершения
        def signal_handler(signum, frame):
            print("📡 Получен сигнал завершения")
            if railway_manager:
                railway_manager.stop_monitoring()
                railway_manager.emergency_cleanup()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        return True
    return False

if __name__ == "__main__":
    setup_railway_limits()