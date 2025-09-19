from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import glob
import pandas as pd
import hashlib
from pathlib import Path
import threading
import concurrent.futures
from datetime import datetime
from selenium.webdriver.common.window import WindowTypes
import config  # Импортируем настройки конфигурации
import random
import json
import psutil
import subprocess
import signal

# Глобальная блокировка для создания драйверов
driver_creation_lock = threading.Lock()

def save_processing_checkpoint(checkpoint_data, checkpoint_file='processing_checkpoint.json'):
    """
    Сохраняет чекпоинт обработки для возможности возобновления
    
    Args:
        checkpoint_data: словарь с данными чекпоинта
        checkpoint_file: имя файла чекпоинта
    """
    try:
        checkpoint_data['timestamp'] = datetime.now().isoformat()
        checkpoint_data['version'] = '1.0'
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Чекпоинт сохранен: {checkpoint_file}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения чекпоинта: {e}")
        return False

def load_processing_checkpoint(checkpoint_file='processing_checkpoint.json'):
    """
    Загружает чекпоинт обработки
    
    Returns:
        dict: данные чекпоинта или None если файл не найден/поврежден
    """
    try:
        if not os.path.exists(checkpoint_file):
            print(f"ℹ️ Чекпоинт файл не найден: {checkpoint_file}")
            return None
            
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
        
        print(f"📂 Чекпоинт загружен: {checkpoint_file}")
        return checkpoint_data
    except Exception as e:
        print(f"❌ Ошибка загрузки чекпоинта: {e}")
        return None

def should_resume_processing(checkpoint_data, supplier_file_path):
    """
    Проверяет, нужно ли возобновлять обработку
    
    Args:
        checkpoint_data: данные чекпоинта
        supplier_file_path: путь к обрабатываемому файлу
        
    Returns:
        bool: True если нужно возобновить
    """
    if not checkpoint_data:
        return False
        
    # Проверяем, что файл тот же самый
    if checkpoint_data.get('supplier_file') != supplier_file_path:
        print("⚠️ Файл изменился, начинаем обработку заново")
        return False
        
    # Проверяем, что обработка была завершена
    if checkpoint_data.get('completed', False):
        print("✅ Обработка была завершена ранее")
        return False
        
    return True

def find_generuj_button_safely(driver, wait):
    """
    Надежно находит кнопку "Generuj" используя различные селекторы
    
    Args:
        driver: веб-драйвер
        wait: объект WebDriverWait
        
    Returns:
        WebElement: элемент кнопки "Generuj" или None если не найдена
    """
    selectors_to_try = [
        (By.ID, "j_idt702"),  # Новый ID
        (By.ID, "j_idt703"),  # Старый ID (на случай изменений)
        (By.XPATH, "//button[contains(text(), 'Generuj') and not(contains(text(), 'w tle'))]"),  # По тексту
        (By.XPATH, "//button[@title='Generuje raport od ręki (do 500 kodów EAN)']"),  # По title
        (By.CSS_SELECTOR, "button.linkButtonBr[title*='Generuje raport od ręki']"),  # По CSS классу и title
        (By.XPATH, "//button[contains(@onclick, 'waitDlg.show()')]"),  # По onclick событию
    ]
    
    for selector_type, selector_value in selectors_to_try:
        try:
            print(f"Пробуем найти кнопку 'Generuj' через {selector_type}: {selector_value}")
            button = wait.until(EC.element_to_be_clickable((selector_type, selector_value)))
            print(f"✅ Кнопка 'Generuj' найдена через {selector_type}: {selector_value}")
            return button
        except Exception as e:
            print(f"❌ Не удалось найти через {selector_type}: {selector_value} - {e}")
            continue
    
    print("🚨 КРИТИЧЕСКАЯ ОШИБКА: Кнопка 'Generuj' не найдена ни одним из селекторов!")
    return None

def check_system_resources():
    """
    Проверяет системные ресурсы перед запуском браузера
    
    Returns:
        tuple: (bool, int) - (ресурсы доступны, рекомендуемое количество браузеров)
    """
    try:
        # Проверяем память
        memory = psutil.virtual_memory()
        free_memory_mb = memory.available / 1024 / 1024
        memory_percent = memory.percent
        
        # Проверяем CPU
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Определяем рекомендуемое количество браузеров на основе ресурсов
        recommended_browsers = 1  # Минимум 1 браузер
        
        if free_memory_mb > 500 and cpu_usage < 60:
            recommended_browsers = 2  # Оптимально для большинства случаев
        elif free_memory_mb > 300 and cpu_usage < 75:
            recommended_browsers = 1  # Безопасный режим
        else:
            recommended_browsers = 1  # Экономичный режим
        
        print(f"📊 Ресурсы: Память {free_memory_mb:.0f}MB ({memory_percent:.1f}%), CPU {cpu_usage:.1f}%, Рекомендуется: {recommended_browsers} браузер(ов)")
        
        # Проверяем минимальные требования
        min_free_memory = config.RESOURCE_MANAGEMENT.get('min_free_memory_mb', 300)
        max_cpu_usage = config.RESOURCE_MANAGEMENT.get('max_cpu_usage_percent', 75)
        
        memory_ok = free_memory_mb >= min_free_memory
        cpu_ok = cpu_usage <= max_cpu_usage
        
        if not memory_ok:
            print(f"⚠️ Недостаточно памяти: {free_memory_mb:.1f}MB свободно, требуется {min_free_memory}MB")
        if not cpu_ok:
            print(f"⚠️ Высокая загрузка CPU: {cpu_usage:.1f}%, максимум {max_cpu_usage}%")
        
        resources_ok = memory_ok and cpu_ok
        
        return resources_ok, recommended_browsers
        
    except Exception as e:
        print(f"⚠️ Ошибка при проверке ресурсов: {e}")
        return True, 1  # В случае ошибки проверки разрешаем продолжение с 1 браузером

def create_chrome_driver_safely(headless=True, download_dir=None, max_retries=3):
    """
    Безопасно создает Chrome драйвер с блокировкой для предотвращения конфликтов
    
    Args:
        headless: запуск в headless режиме
        download_dir: папка для загрузки файлов
        max_retries: максимальное количество попыток
        
    Returns:
        webdriver.Chrome: инициализированный драйвер или None при ошибке
    """
    
    for attempt in range(max_retries):
        try:
            # Экспоненциальная задержка с jitter для избежания одновременного доступа
            base_delay = 2 ** attempt  # 1, 2, 4 секунды
            jitter = random.uniform(0.5, 1.5)
            delay = base_delay * jitter
            print(f"⏳ Задержка перед попыткой {attempt + 1}: {delay:.1f} сек")
            time.sleep(delay)
            
            with driver_creation_lock:
                print(f"🔒 Попытка {attempt + 1}/{max_retries}: Создание Chrome драйвера...")
                
                # ГЛУБОКАЯ ДИАГНОСТИКА СИСТЕМНЫХ РЕСУРСОВ
                print("🔍 ГЛУБОКАЯ ДИАГНОСТИКА СИСТЕМНЫХ РЕСУРСОВ:")
                try:
                    # Проверяем память
                    memory = psutil.virtual_memory()
                    print(f"   💾 Память: {memory.available / 1024 / 1024:.0f}MB свободно из {memory.total / 1024 / 1024:.0f}MB")
                    
                    # Проверяем CPU
                    cpu_percent = psutil.cpu_percent(interval=1)
                    print(f"   🖥️  CPU: {cpu_percent}% загрузка")
                    
                    # Проверяем диск
                    disk = psutil.disk_usage('/')
                    print(f"   💿 Диск: {disk.free / 1024 / 1024:.0f}MB свободно")
                    
                    # Проверяем процессы Chrome
                    chrome_processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                        try:
                            if 'chrome' in proc.info['name'].lower() or 'chromium' in proc.info['name'].lower():
                                chrome_processes.append(proc.info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    print(f"   🌐 Chrome процессов: {len(chrome_processes)}")
                    for proc in chrome_processes[:3]:  # Показываем первые 3
                        memory_mb = proc['memory_info'].rss / 1024 / 1024 if proc['memory_info'] else 0
                        print(f"      PID {proc['pid']}: {proc['name']} ({memory_mb:.0f}MB)")
                    
                    # ЭКСТРЕННАЯ ПРОВЕРКА КОЛИЧЕСТВА ПРОЦЕССОВ
                    if len(chrome_processes) > 50:
                        print(f"   🚨 КРИТИЧНО! {len(chrome_processes)} Chrome процессов!")
                        print("   💥 ЭКСТРЕННАЯ ОЧИСТКА ПЕРЕД ЗАПУСКОМ...")
                        try:
                            # Немедленная экстренная очистка
                            subprocess.run(["killall", "-9", "chrome"], capture_output=True, check=False)
                            subprocess.run(["killall", "-9", "chromium"], capture_output=True, check=False)
                            subprocess.run(["killall", "-9", "chromedriver"], capture_output=True, check=False)
                            time.sleep(3)
                            print("   ✅ Экстренная очистка выполнена")
                        except Exception as emergency_error:
                            print(f"   ⚠️  Ошибка экстренной очистки: {emergency_error}")
                    
                    # КРИТИЧЕСКАЯ ЗАЩИТА: ОСТАНОВКА СИСТЕМЫ ПРИ >100 ПРОЦЕССАХ
                    if len(chrome_processes) > 100:
                        print(f"   🚨 КАТАСТРОФА! {len(chrome_processes)} Chrome процессов!")
                        print("   💀 АВАРИЙНАЯ ОСТАНОВКА СИСТЕМЫ...")
                        try:
                            # Убиваем все процессы с максимальной силой
                            subprocess.run(["killall", "-9", "-f", "chrome"], capture_output=True, check=False)
                            subprocess.run(["killall", "-9", "-f", "chromium"], capture_output=True, check=False)
                            subprocess.run(["killall", "-9", "-f", "chromedriver"], capture_output=True, check=False)
                            subprocess.run(["pkill", "-9", "-f", "python"], capture_output=True, check=False)
                            print("   💀 Система принудительно остановлена из-за переполнения процессов")
                            print("   🔄 Перезапустите приложение после очистки")
                            # Выходим из функции с ошибкой
                            raise RuntimeError(f"Катастрофическое переполнение процессов: {len(chrome_processes)}")
                        except Exception as critical_error:
                            print(f"   ⚠️  Ошибка аварийной остановки: {critical_error}")
                            raise critical_error
                    
                except Exception as diag_error:
                    print(f"   ⚠️  Ошибка диагностики: {diag_error}")
                
                # ПРОВЕРКА ДОСТУПНОСТИ CHROME И CHROMEDRIVER
                print("🔍 ПРОВЕРКА ДОСТУПНОСТИ CHROME:")
                chrome_available = False
                chromedriver_available = False
                
                # Проверяем системный Chrome
                try:
                    result = subprocess.run(["/usr/bin/google-chrome", "--version"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        chrome_available = True
                        print(f"   ✅ Системный Chrome доступен: {result.stdout.strip()}")
                    else:
                        print(f"   ❌ Системный Chrome недоступен: {result.stderr}")
                except Exception as e:
                    print(f"   ❌ Ошибка проверки системного Chrome: {e}")
                
                # Проверяем ChromeDriver
                try:
                    result = subprocess.run(["/usr/bin/chromedriver", "--version"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        chromedriver_available = True
                        print(f"   ✅ ChromeDriver доступен: {result.stdout.strip()}")
                    else:
                        print(f"   ❌ ChromeDriver недоступен: {result.stderr}")
                except Exception as e:
                    print(f"   ❌ Ошибка проверки ChromeDriver: {e}")
                
                if not chrome_available or not chromedriver_available:
                    print("   🚨 Chrome или ChromeDriver недоступны! Попытка использовать ChromeDriverManager...")
                
                # СУПЕР-АГРЕССИВНАЯ ОЧИСТКА: Принудительно убиваем ВСЕ висячие процессы
                try:
                    print("🔥 СУПЕР-АГРЕССИВНАЯ ОЧИСТКА ПРОЦЕССОВ...")

                    # 1. Проверяем количество Chrome процессов ДО очистки
                    chrome_count_before = 0
                    try:
                        result = subprocess.run(["pgrep", "-f", "chrome"], capture_output=True, text=True)
                        if result.stdout.strip():
                            chrome_count_before = len(result.stdout.strip().split('\n'))
                        print(f"   📊 Chrome процессов до очистки: {chrome_count_before}")
                    except:
                        pass

                    # 2. Убиваем все Chrome процессы разными способами
                    subprocess.run(["pkill", "-9", "-f", "chrome"], capture_output=True, check=False)
                    subprocess.run(["pkill", "-9", "-f", "chromium"], capture_output=True, check=False)
                    subprocess.run(["pkill", "-9", "-f", "chromedriver"], capture_output=True, check=False)
                    subprocess.run(["pkill", "-9", "chrome"], capture_output=True, check=False)
                    subprocess.run(["pkill", "-9", "chromium"], capture_output=True, check=False)
                    subprocess.run(["pkill", "-9", "chromedriver"], capture_output=True, check=False)

                    # 3. Убиваем процессы на всех возможных портах WebDriver
                    for port in [9515, 9222, 9223, 9224, 9225]:
                        try:
                            result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True, check=False)
                            if result.stdout.strip():
                                for pid in result.stdout.strip().split('\n'):
                                    if pid:
                                        try:
                                            os.kill(int(pid), signal.SIGKILL)
                                            print(f"   💀 Убит процесс {pid} на порту {port}")
                                        except:
                                            pass
                        except:
                            pass

                    # 4. Дополнительная очистка через ps и kill
                    try:
                        # Находим все процессы chrome/chromium
                        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
                        if result.stdout:
                            for line in result.stdout.split('\n'):
                                if 'chrome' in line.lower() or 'chromium' in line.lower():
                                    try:
                                        pid = line.split()[1]
                                        os.kill(int(pid), signal.SIGKILL)
                                        print(f"   💀 Дополнительно убит процесс {pid}")
                                    except:
                                        pass
                    except:
                        pass

                    # 5. Ждем завершения процессов (увеличенное время)
                    time.sleep(3)

                    # 6. Проверяем результат очистки
                    chrome_count_after = 0
                    try:
                        result = subprocess.run(["pgrep", "-f", "chrome"], capture_output=True, text=True)
                        if result.stdout.strip():
                            chrome_count_after = len(result.stdout.strip().split('\n'))
                        print(f"   📊 Chrome процессов после очистки: {chrome_count_after}")
                        print(f"   ✅ Убито процессов: {chrome_count_before - chrome_count_after}")
                    except:
                        pass

                    # 7. Если все еще много процессов - ПАНИКА!
                    if chrome_count_after > 10:
                        print(f"   🚨 КРИТИЧНО! Все еще {chrome_count_after} Chrome процессов!")
                        print("   💥 ЭКСТРЕННАЯ ОЧИСТКА: перезапуск всех Chrome процессов...")
                        # Убиваем все процессы chrome с максимальной силой
                        subprocess.run(["killall", "-9", "chrome"], capture_output=True, check=False)
                        subprocess.run(["killall", "-9", "chromium"], capture_output=True, check=False)
                        subprocess.run(["killall", "-9", "chromedriver"], capture_output=True, check=False)
                        time.sleep(5)

                    print("🧹 Супер-агрессивная очистка процессов выполнена")

                except Exception as e:
                    print(f"⚠️ Ошибка при очистке процессов: {e}")
                
                # ПРОВЕРКА СИСТЕМНЫХ РЕСУРСОВ ПЕРЕД ЗАПУСКОМ
                print("🔍 ПРОВЕРКА СИСТЕМНЫХ РЕСУРСОВ:")
                memory_ok = False
                cpu_ok = False
                
                try:
                    # Проверяем память (минимум 400MB свободно для Chrome)
                    memory = psutil.virtual_memory()
                    min_free_memory = config.RESOURCE_MANAGEMENT.get('min_free_memory_mb', 400) * 1024 * 1024
                    memory_ok = memory.available >= min_free_memory
                    print(f"   💾 Память: {memory_ok} ({memory.available / 1024 / 1024:.0f}MB >= {min_free_memory / 1024 / 1024:.0f}MB)")
                    
                    # Проверяем CPU (не более 80% загрузки)
                    cpu_percent = psutil.cpu_percent(interval=0.5)
                    cpu_ok = cpu_percent < 80
                    print(f"   🖥️  CPU: {cpu_ok} ({cpu_percent:.1f}% < 80%)")
                    
                    if not memory_ok or not cpu_ok:
                        print("⚠️  НЕДОСТАТОЧНО РЕСУРСОВ ДЛЯ ЗАПУСКА CHROME!")
                        if not memory_ok:
                            print("   💡 Рекомендация: увеличить память или уменьшить количество браузеров")
                        if not cpu_ok:
                            print("   💡 Рекомендация: уменьшить нагрузку на CPU")
                        
                        # Для Railway - ждем освобождения ресурсов
                        print("⏳ Ждем освобождения ресурсов (10 сек)...")
                        time.sleep(10)
                        
                        # Повторная проверка
                        memory = psutil.virtual_memory()
                        cpu_percent = psutil.cpu_percent(interval=0.5)
                        memory_ok = memory.available >= min_free_memory
                        cpu_ok = cpu_percent < 80
                        
                        if not memory_ok or not cpu_ok:
                            print("❌ Ресурсы все еще недостаточны, пропускаем попытку")
                            continue  # Пропускаем эту попытку
                        else:
                            print("✅ Ресурсы освободились, продолжаем")
                    
                except Exception as resource_error:
                    print(f"⚠️  Ошибка проверки ресурсов: {resource_error}")
                    print("   Продолжаем без проверки ресурсов...")
                
                # Создаем опции Chrome с Railway-специфичными настройками
                options = webdriver.ChromeOptions()
                
                if headless:
                    options.add_argument("--headless")
                    options.add_argument("--disable-gpu")
                
                # ОСНОВНЫЕ ОПЦИИ ДЛЯ RAILWAY КОНТЕЙНЕРА
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-web-security")
                options.add_argument("--disable-features=VizDisplayCompositor")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-logging")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-crash-reporter")
                options.add_argument("--disable-in-process-stack-traces")
                options.add_argument("--silent")
                options.add_argument("--log-level=3")  # Минимальный уровень логирования
                options.add_argument("--disable-background-timer-throttling")
                options.add_argument("--disable-backgrounding-occluded-windows")
                options.add_argument("--disable-renderer-backgrounding")
                
                # ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ДЛЯ RAILWAY
                options.add_argument("--disable-software-rasterizer")
                options.add_argument("--disable-background-networking")
                options.add_argument("--disable-default-apps")
                options.add_argument("--disable-sync")
                options.add_argument("--disable-translate")
                options.add_argument("--hide-scrollbars")
                options.add_argument("--metrics-recording-only")
                options.add_argument("--mute-audio")
                options.add_argument("--no-first-run")
                options.add_argument("--safebrowsing-disable-auto-update")
                options.add_argument("--single-process")  # Важно для контейнеров
                
                # ОГРАНИЧЕНИЯ РЕСУРСОВ ДЛЯ КОНТЕЙНЕРА
                options.add_argument("--max_old_space_size=512")  # Ограничение памяти JavaScript
                options.add_argument("--memory-pressure-off")  # Отключение мониторинга памяти
                
                # СЕТЕВЫЕ НАСТРОЙКИ ДЛЯ КОНТЕЙНЕРА
                options.add_argument("--disable-ipc-flooding-protection")
                options.add_argument("--disable-hang-monitor")
                options.add_argument("--disable-prompt-on-repost")
                options.add_argument("--force-color-profile=srgb")
                options.add_argument("--disable-component-extensions-with-background-pages")
                
                print(f"🔧 Настройки Chrome: headless={headless}, Railway-оптимизированные")
                
                # Настройка загрузки файлов
                if download_dir:
                    prefs = {
                        "download.default_directory": download_dir,
                        "download.prompt_for_download": False,
                        "download.directory_upgrade": True,
                        "safebrowsing.enabled": True
                    }
                    options.add_experimental_option("prefs", prefs)
                
                # ПРОВЕРКА ДОСТУПНОСТИ ПОРТА WEBDRIVER
                print("🔍 ПРОВЕРКА ПОРТА WEBDRIVER:")
                port_available = False
                
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('127.0.0.1', 9515))
                    sock.close()
                    
                    if result == 0:
                        print("   ❌ Порт 9515 занят! Попытка освободить...")
                        # Пытаемся убить процесс на порту
                        try:
                            result = subprocess.run(["lsof", "-ti:9515"], capture_output=True, text=True, check=False)
                            if result.stdout.strip():
                                for pid in result.stdout.strip().split('\n'):
                                    if pid:
                                        os.kill(int(pid), signal.SIGKILL)
                                        print(f"   💀 Убит процесс {pid} на порту 9515")
                                time.sleep(2)  # Ждем завершения
                                
                                # Повторная проверка
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(1)
                                result = sock.connect_ex(('127.0.0.1', 9515))
                                sock.close()
                                
                                if result != 0:
                                    port_available = True
                                    print("   ✅ Порт 9515 освобожден")
                                else:
                                    print("   ❌ Порт 9515 все еще занят")
                            else:
                                print("   ⚠️  lsof не нашел процессов на порту 9515")
                        except Exception as port_kill_error:
                            print(f"   ⚠️  Ошибка освобождения порта: {port_kill_error}")
                    else:
                        port_available = True
                        print("   ✅ Порт 9515 свободен")
                        
                except Exception as port_check_error:
                    print(f"   ⚠️  Ошибка проверки порта: {port_check_error}")
                    port_available = True  # Предполагаем, что порт доступен
                
                # Пытаемся использовать системный Chrome
                try:
                    options.binary_location = "/usr/bin/google-chrome"
                    service = Service(executable_path="/usr/bin/chromedriver")
                    print("🚀 Запуск Chrome с системными бинарными файлами...")
                    driver = webdriver.Chrome(service=service, options=options)
                    print("✅ Используем системный Chrome с предустановленным ChromeDriver")
                    return driver
                except Exception as e:
                    error_msg = str(e)
                    print(f"⚠️  Системный Chrome не найден или версия не совпадает: {error_msg}")
                    
                    # ДЕТАЛЬНЫЙ АНАЛИЗ ОШИБКИ ПОДКЛЮЧЕНИЯ
                    if "connection refused" in error_msg.lower():
                        print("🔍 АНАЛИЗ ОШИБКИ ПОДКЛЮЧЕНИЯ:")
                        print("   - ChromeDriver не может подключиться к Chrome")
                        print("   - Возможные причины: порт занят, Chrome не запустился, ресурсы исчерпаны")
                        
                        # Проверяем, не остался ли Chrome процесс
                        try:
                            result = subprocess.run(["pgrep", "-f", "chrome"], capture_output=True, text=True)
                            if result.stdout.strip():
                                print(f"   - Найдены висячие Chrome процессы: {result.stdout.strip()}")
                                subprocess.run(["pkill", "-9", "-f", "chrome"], capture_output=True)
                                print("   - Висячие процессы убиты")
                            else:
                                print("   - Висячих Chrome процессов не найдено")
                        except Exception as pgrep_error:
                            print(f"   - Ошибка проверки процессов: {pgrep_error}")
                            
                    elif "version" in error_msg.lower():
                        print("🔍 АНАЛИЗ ВЕРСИОННОЙ ОШИБКИ:")
                        print("   - Несовпадение версий Chrome и ChromeDriver")
                        print("   - Попытка использовать ChromeDriverManager...")
                        
                    elif "session not created" in error_msg.lower():
                        print("🔍 АНАЛИЗ ОШИБКИ СЕАНСА:")
                        print("   - Chrome не может создать сессию")
                        print("   - Возможные причины: недостаточно памяти, поврежденные настройки")
                    
                    # Используем ChromeDriverManager как fallback с улучшенной обработкой
                    try:
                        print("🔄 Попытка с ChromeDriverManager...")
                        service = Service(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=options)
                        print("✅ Используем ChromeDriverManager (автоматическое совпадение версий)")
                        return driver
                    except Exception as wdm_error:
                        wdm_error_msg = str(wdm_error)
                        print(f"❌ ChromeDriverManager тоже не сработал: {wdm_error_msg}")
                        
                        # ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ ПО ОШИБКАМ
                        if "connection refused" in wdm_error_msg.lower():
                            print("💡 РЕКОМЕНДАЦИИ:")
                            print("   - Проверьте доступность порта 9515")
                            print("   - Убедитесь, что Chrome может запускаться в контейнере")
                            print("   - Попробуйте увеличить задержки между запусками")
                        elif "memory" in wdm_error_msg.lower():
                            print("💡 РЕКОМЕНДАЦИИ:")
                            print("   - Недостаточно памяти для запуска Chrome")
                            print("   - Рассмотрите уменьшение количества одновременных браузеров")
                        
                        raise wdm_error
                        
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Попытка {attempt + 1} неудачна: {error_msg}")
            
            # Дополнительная очистка при версионных конфликтах
            if "version" in error_msg.lower() or "session not created" in error_msg.lower():
                print("🚨 Обнаружен версионный конфликт Chrome/ChromeDriver! Принудительная очистка...")
                try:
                    subprocess.run(["pkill", "-9", "-f", "chrome"], capture_output=True, check=False)
                    subprocess.run(["pkill", "-9", "-f", "chromedriver"], capture_output=True, check=False)
                    time.sleep(2)
                except:
                    pass
            
            if attempt < max_retries - 1:
                delay = (attempt + 1) * 3 + random.uniform(0, 2)  # Увеличенная задержка для версионных конфликтов
                print(f"⏳ Ждем {delay:.1f} секунд перед следующей попыткой...")
                time.sleep(delay)
            else:
                print(f"💥 Все {max_retries} попыток исчерпаны!")
                raise e
    
    return None

def safe_get_downloaded_file(downloaded_files, context=""):
    """
    Безопасно получает первый файл из списка с проверкой на пустоту
    
    Args:
        downloaded_files: список файлов
        context: контекст для сообщения об ошибке
        
    Returns:
        str: путь к файлу или None если список пуст
    """
    if downloaded_files and len(downloaded_files) > 0:
        return downloaded_files[0]
    else:
        print(f"⚠️  {context}: Список загруженных файлов пуст, файл не найден")
        return None

def clear_ean_field_thoroughly(driver, ean_field, batch_number):
    """
    КРИТИЧЕСКИ ВАЖНО: Тщательно очищает поле EAN кодов несколькими способами
    
    Args:
        driver: веб-драйвер
        ean_field: элемент поля EAN кодов
        batch_number: номер группы для логирования
    """
    print(f"НАЧИНАЕМ АГРЕССИВНУЮ ОЧИСТКУ поля EAN кодов для группы {batch_number}...")
    
    # Проверяем изначальное состояние
    initial_value = ean_field.get_attribute("value")
    print(f"Изначальное содержимое поля: '{initial_value}'")
    
    # Сначала убеждаемся, что поле в фокусе
    try:
        ean_field.click()
        time.sleep(0.3)
    except:
        pass
    
    # СПОСОБ 1: Стандартная очистка (может не работать)
    ean_field.clear()
    time.sleep(0.2)
    
    # СПОСОБ 2: Выделяем все и удаляем (может не работать)
    try:
        ean_field.send_keys(Keys.CONTROL + "a")
        time.sleep(0.1)
        ean_field.send_keys(Keys.DELETE)
        time.sleep(0.2)
    except:
        pass
    
    # СПОСОБ 3: Альтернативная очистка клавишами
    try:
        ean_field.send_keys(Keys.CONTROL + "a")
        time.sleep(0.1)
        ean_field.send_keys(Keys.BACKSPACE)
        time.sleep(0.2)
    except:
        pass
    
    # СПОСОБ 4: JavaScript очистка (основной метод)
    driver.execute_script("arguments[0].value = '';", ean_field)
    time.sleep(0.2)
    
    # СПОСОБ 5: Более агрессивная JavaScript очистка
    driver.execute_script("""
        var element = arguments[0];
        element.value = '';
        element.innerHTML = '';
        element.textContent = '';
        element.innerText = '';
        if (element.defaultValue) element.defaultValue = '';
    """, ean_field)
    time.sleep(0.2)
    
    # СПОСОБ 6: Эмуляция очистки через JavaScript события
    driver.execute_script("""
        var element = arguments[0];
        element.focus();
        element.value = '';
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.dispatchEvent(new Event('blur', { bubbles: true }));
        element.dispatchEvent(new Event('keydown', { bubbles: true }));
        element.dispatchEvent(new Event('keyup', { bubbles: true }));
    """, ean_field)
    time.sleep(0.3)
    
    # СПОСОБ 7: Удаление через execCommand
    driver.execute_script("""
        var element = arguments[0];
        element.focus();
        element.select();
        document.execCommand('selectAll');
        document.execCommand('delete');
        document.execCommand('removeFormat');
    """, ean_field)
    time.sleep(0.2)
    
    # СПОСОБ 8: Принудительная замена содержимого
    driver.execute_script("""
        var element = arguments[0];
        element.setAttribute('value', '');
        element.removeAttribute('defaultValue');
        if (element.value) element.value = '';
    """, ean_field)
    time.sleep(0.3)
    
    # КРИТИЧЕСКАЯ ПРОВЕРКА: Проверяем, что поле действительно очищено
    for attempt in range(3):
        current_value = ean_field.get_attribute("value")
        print(f"Попытка {attempt + 1}: Содержимое поля после очистки: '{current_value}'")
        
        if not current_value or len(current_value.strip()) == 0:
            print(f"✅ Поле успешно очищено для группы {batch_number}")
            break
        else:
            print(f"❌ Поле не очищено! Осталось: '{current_value}'. Дополнительная агрессивная очистка...")
            
            # Дополнительная агрессивная очистка
            driver.execute_script("""
                var element = arguments[0];
                
                // Удаляем все возможные свойства
                element.value = '';
                element.defaultValue = '';
                element.textContent = '';
                element.innerHTML = '';
                element.innerText = '';
                
                // Принудительно удаляем атрибуты
                element.removeAttribute('value');
                element.removeAttribute('defaultValue');
                
                // Эмуляция пользовательских действий
                element.focus();
                element.select();
                
                // Очистка через range API
                if (window.getSelection) {
                    var selection = window.getSelection();
                    selection.removeAllRanges();
                    var range = document.createRange();
                    range.selectNodeContents(element);
                    selection.addRange(range);
                    selection.deleteFromDocument();
                }
                
                // Финальная установка пустого значения
                element.value = '';
                
                // Генерация событий
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
            """, ean_field)
            time.sleep(0.5)
            
            # Если все еще не очищено, принудительно заменяем элемент
            if attempt == 2:
                final_value = ean_field.get_attribute("value")
                if final_value and final_value.strip():
                    print(f"🔥 КРИТИЧЕСКАЯ ОШИБКА: Поле не удается очистить! Содержимое: '{final_value}'")
                    print("Выполняем принудительную перезагрузку страницы...")
                    driver.refresh()
                    time.sleep(3)
                    return False
    
    print(f"✅ Агрессивная очистка завершена для группы {batch_number}")
    return True


def insert_ean_codes_safely(driver, ean_field, ean_codes_string, batch_number):
    """
    Безопасно вставляет EAN коды с проверкой результата
    
    Args:
        driver: веб-драйвер
        ean_field: элемент поля EAN кодов
        ean_codes_string: строка с EAN кодами
        batch_number: номер группы для логирования
    """
    # Убеждаемся, что поле в фокусе
    try:
        ean_field.click()
        time.sleep(0.2)
    except:
        pass
    
    # Вставляем коды
    ean_field.send_keys(ean_codes_string)
    
    # Даем время на обработку
    time.sleep(0.5)
    
    # Проверяем, что коды вставились корректно
    inserted_value = ean_field.get_attribute("value")
    if not inserted_value or len(inserted_value.strip()) == 0:
        print(f"Коды не вставились! Попытка повторной вставки через JavaScript...")
        
        # Попытка через JavaScript
        driver.execute_script("""
            var element = arguments[0];
            var text = arguments[1];
            element.focus();
            element.value = text;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        """, ean_field, ean_codes_string)
        
        time.sleep(1)
        
        # Повторная проверка
        inserted_value = ean_field.get_attribute("value")
        if not inserted_value or len(inserted_value.strip()) == 0:
            print(f"Ошибка: коды так и не вставились даже через JavaScript!")
            
            # Последняя попытка - прямая вставка
            try:
                ean_field.clear()
                ean_field.send_keys(ean_codes_string)
                time.sleep(1)
                inserted_value = ean_field.get_attribute("value")
            except:
                pass
            
            if not inserted_value or len(inserted_value.strip()) == 0:
                return False
    
    # Проверяем соответствие количества кодов
    inserted_codes = inserted_value.strip().split()
    expected_codes = ean_codes_string.strip().split()
    
    if len(inserted_codes) != len(expected_codes):
        print(f"Предупреждение: количество вставленных кодов ({len(inserted_codes)}) не совпадает с ожидаемым ({len(expected_codes)})")
        print(f"Ожидались: {expected_codes[:5]}...")
        print(f"Вставлены: {inserted_codes[:5]}...")
        
        # Проверяем, что хотя бы половина кодов вставилась
        if len(inserted_codes) < len(expected_codes) * 0.5:
            print(f"Критическая ошибка: вставлено менее половины кодов!")
            return False
    else:
        print(f"✅ Вставлено {len(inserted_codes)} EAN кодов для группы {batch_number}")
    
    return True


def verify_batch_uniqueness(downloaded_files):
    """
    Проверяет уникальность содержимого загруженных файлов
    
    Args:
        downloaded_files: список путей к загруженным файлам
        
    Returns:
        bool: True если все файлы уникальны, False если есть дублирования
    """
    print("\n🔍 ПРОВЕРКА УНИКАЛЬНОСТИ содержимого файлов...")
    
    file_hashes = {}
    duplicates_found = False
    
    for file_path in downloaded_files:
        if not os.path.exists(file_path):
            print(f"❌ Файл не найден: {file_path}")
            continue
            
        try:
            # Читаем файл и создаем хеш содержимого
            df = pd.read_excel(file_path)
            
            # Создаем строку из содержимого для хеширования
            content_string = df.to_string()
            content_hash = hashlib.md5(content_string.encode()).hexdigest()
            
            filename = os.path.basename(file_path)
            
            if content_hash in file_hashes:
                print(f"🚨 ОБНАРУЖЕНО ДУБЛИРОВАНИЕ: {filename} идентичен {file_hashes[content_hash]}")
                duplicates_found = True
            else:
                file_hashes[content_hash] = filename
                print(f"✅ Файл уникален: {filename}")
                
        except Exception as e:
            print(f"❌ Ошибка при проверке файла {file_path}: {e}")
    
    if duplicates_found:
        print("\n🚨 НАЙДЕНЫ ДУБЛИРОВАННЫЕ ФАЙЛЫ! Требуется исправление.")
        return False
    else:
        print("\n✅ Все файлы уникальны.")
        return True


def format_ean_to_13_digits(ean_code):
    """
    Форматирует EAN код в стандартный 13-цифровой формат
    
    Args:
        ean_code: EAN код (строка или число)
        
    Returns:
        str: EAN код в 13-цифровом формате с ведущими нулями
        
    Пример:
        format_ean_to_13_digits("123456789") -> "0000123456789"
        format_ean_to_13_digits("1234567890123") -> "1234567890123"
    """
    try:
        # Конвертируем в строку и удаляем пробелы
        ean_str = str(ean_code).strip()
        
        # Если получилось пустое значение, возвращаем None
        if not ean_str:
            return None
        
        # Особая обработка для научной нотации
        if 'E' in ean_str.upper() or 'e' in ean_str:
            try:
                # Конвертируем через float для обработки научной нотации
                ean_float = float(ean_str)
                ean_str = str(int(ean_float))
            except:
                pass
        
        # Удаляем все нечисловые символы
        ean_digits = ''.join(char for char in ean_str if char.isdigit())
        
        # Если получилось пустое значение, возвращаем None
        if not ean_digits:
            return None
            
        # Обрезаем до 13 цифр если больше
        if len(ean_digits) > 13:
            ean_digits = ean_digits[:13]
            
        # Дополняем ведущими нулями до 13 цифр
        ean_formatted = ean_digits.zfill(13)
        
        return ean_formatted
        
    except Exception as e:
        print(f"Ошибка при форматировании EAN кода '{ean_code}': {e}")
        return None

def process_ean_codes_batch(ean_codes_batch, download_dir, batch_number=1, headless=None):
    """
    [УСТАРЕЛО] Обрабатывает группу EAN кодов в TradeWatch и скачивает файл
    Используйте process_supplier_file_with_tradewatch() для более эффективной обработки
    
    Args:
        ean_codes_batch: список EAN кодов для обработки
        download_dir: папка для скачивания файлов
        batch_number: номер группы для идентификации файла
        headless: запуск в headless режиме или None (использовать config)
    
    Returns:
        str: путь к скачанному файлу или None если ошибка
    """
    print("⚠️  ВНИМАНИЕ: Эта функция устарела. Используйте process_supplier_file_with_tradewatch() для более эффективной обработки с единой сессией браузера.")
    
    # Используем конфигурацию если headless не указан
    if headless is None:
        headless = config.HEADLESS_MODE
    
    if not ean_codes_batch:
        print("Пустая группа EAN кодов")
        return None
        
    # Создаем папку для скачивания если её нет
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)
    
    # Удаляем только файлы с оригинальным именем (не переименованные)
    old_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji.xlsx"))
    for old_file in old_files:
        try:
            os.remove(old_file)
            print(f"Удален старый файл: {old_file}")
        except Exception as e:
            print(f"Не удалось удалить файл {old_file}: {e}")
            pass
    
    # Соединяем EAN коды в одну строку через пробел
    ean_codes_string = ' '.join(str(code) for code in ean_codes_batch)
    
    # Настройка драйвера Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # if headless:
        # options.add_argument("--headless")  # Запуск в headless режиме
    
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    
    # Настройка для автоматической загрузки файлов
    prefs = {
        "download.default_directory": str(download_path.absolute()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    # Инициализация драйвера
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"Обработка группы {batch_number} с {len(ean_codes_batch)} EAN кодами...")
        
        # Переход на страницу входа
        driver.get("https://tradewatch.pl/login.jsf")
        
        # Ждем загрузки страницы
        wait = WebDriverWait(driver, 10)
        
        # Ищем поле для email
        email_field = wait.until(EC.presence_of_element_located((By.NAME, "j_username")))
        
        # Вводим email
        email_field.clear()
        email_field.send_keys("emvertrends@gmail.com")
        
        # Ищем поле для пароля
        password_field = driver.find_element(By.NAME, "j_password")
        
        # Вводим пароль
        password_field.clear()
        password_field.send_keys("Trade-watch12")
        
        # Ищем кнопку входа
        login_button = driver.find_element(By.NAME, "btnLogin")
        
        # Нажимаем кнопку входа
        login_button.click()
        
        # Ждем немного после входа
        time.sleep(3)
        
        # Проверяем успешность входа
        current_url = driver.current_url
        
        if "login.jsf" not in current_url:
            print("Успешный вход в систему!")
            
            # Переходим на страницу EAN Price Report
            driver.get("https://tradewatch.pl/report/ean-price-report.jsf")
            time.sleep(3)
            
            try:
                # Ищем поле для ввода EAN кодов
                ean_field = wait.until(EC.presence_of_element_located((By.ID, "eansPhrase")))
                
                # Тщательно очищаем поле
                clear_ean_field_thoroughly(driver, ean_field, batch_number)
                
                # Безопасно вставляем EAN коды
                if not insert_ean_codes_safely(driver, ean_field, ean_codes_string, batch_number):
                    print(f"Ошибка: не удалось вставить EAN коды для группы {batch_number}")
                    return None
                
                # Ждем немного
                time.sleep(1)
                
                # Ищем кнопку "Generuj" надежным способом
                generate_button = find_generuj_button_safely(driver, wait)
                if not generate_button:
                    print(f"❌ Ошибка: не удалось найти кнопку 'Generuj' для группы {batch_number}")
                    return None
                
                # Нажимаем кнопку
                generate_button.click()
                
                # Ждем обработки
                print("Ждем обработки запроса...")
                time.sleep(5)
                
                # Ждем появления результатов
                print("Ждем появления результатов...")
                time.sleep(5)  # Увеличиваем время ожидания результатов
                
                # Ищем кнопку "Eksport do XLS"
                try:
                    export_button = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Eksport do XLS")))
                    
                    # Нажимаем кнопку экспорта
                    export_button.click()
                    
                    # Ждем начала загрузки файла
                    print("Ждем загрузки файла...")
                    
                    # Ждем появления файла с проверкой каждые 2 секунды
                    max_wait_time = 60  # Максимальное время ожидания 60 секунд
                    wait_interval = 2   # Проверяем каждые 2 секунды
                    waited_time = 0
                    
                    downloaded_file_found = False
                    
                    while waited_time < max_wait_time:
                        time.sleep(wait_interval)
                        waited_time += wait_interval
                        
                        # Ищем скачанный файл (только оригинальное имя)
                        downloaded_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji.xlsx"))
                        if downloaded_files:
                            # Проверяем, что файл полностью скачался (не изменяется в размере)
                            latest_file = safe_get_downloaded_file(downloaded_files, f"Группа {batch_number} - основная проверка")
                            if not latest_file:
                                return None
                            
                            # Ждем немного и проверяем, что размер файла не изменился
                            initial_size = os.path.getsize(latest_file)
                            time.sleep(3)  # Ждем 3 секунды
                            
                            try:
                                final_size = os.path.getsize(latest_file)
                                if initial_size == final_size and final_size > 0:
                                    # Файл стабильного размера, значит скачивание завершено
                                    print(f"Файл для группы {batch_number} загружен: {latest_file} (размер: {final_size} байт)")
                                    downloaded_file_found = True
                                    break
                                else:
                                    print(f"Файл еще скачивается... (размер: {final_size} байт)")
                            except:
                                # Файл может быть заблокирован, продолжаем ждать
                                print(f"Файл заблокирован, продолжаем ждать...")
                                continue
                        else:
                            print(f"Ожидание файла... ({waited_time}/{max_wait_time} сек)")
                    
                    if downloaded_file_found:
                        # Переименовываем файл для идентификации
                        new_filename = f"TradeWatch_batch_{batch_number}.xlsx"
                        new_filepath = os.path.join(download_dir, new_filename)
                        
                        if os.path.exists(new_filepath):
                            os.remove(new_filepath)
                        
                        os.rename(latest_file, new_filepath)
                        return new_filepath
                    else:
                        print(f"Файл для группы {batch_number} не найден после {max_wait_time} секунд ожидания")
                        return None
                        
                except Exception as export_error:
                    print(f"Ошибка при экспорте группы {batch_number}: {export_error}")
                    # Попробуем альтернативный способ
                    try:
                        export_button = driver.find_element(By.CSS_SELECTOR, "a.icon-excel")
                        export_button.click()
                        
                        # Ждем с проверкой завершения скачивания
                        max_wait_time = 60
                        wait_interval = 2
                        waited_time = 0
                        
                        while waited_time < max_wait_time:
                            time.sleep(wait_interval)
                            waited_time += wait_interval
                            
                            downloaded_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji.xlsx"))
                            if downloaded_files:
                                latest_file = safe_get_downloaded_file(downloaded_files, f"Группа {batch_number} - альтернативная проверка")
                                if not latest_file:
                                    continue
                                
                                # Проверяем стабильность размера файла
                                initial_size = os.path.getsize(latest_file)
                                time.sleep(3)
                                
                                try:
                                    final_size = os.path.getsize(latest_file)
                                    if initial_size == final_size and final_size > 0:
                                        new_filename = f"TradeWatch_batch_{batch_number}.xlsx"
                                        new_filepath = os.path.join(download_dir, new_filename)
                                        
                                        if os.path.exists(new_filepath):
                                            os.remove(new_filepath)
                                        
                                        os.rename(latest_file, new_filepath)
                                        return new_filepath
                                except:
                                    continue
                            else:
                                print(f"Альтернативный способ: ожидание файла... ({waited_time}/{max_wait_time} сек)")
                        
                        return None
                    except Exception as alt_error:
                        print(f"Альтернативный метод тоже не сработал для группы {batch_number}: {alt_error}")
                        return None
                
            except Exception as e:
                print(f"Ошибка при работе с EAN кодами группы {batch_number}: {e}")
                return None
        else:
            print("Ошибка при входе в систему")
            return None
            
    except Exception as e:
        print(f"Произошла ошибка при обработке группы {batch_number}: {e}")
        return None
    
    finally:
        # Закрываем браузер
        driver.quit()


def process_batch_in_session(driver, ean_codes_batch, download_dir, batch_number):
    """
    Обрабатывает группу EAN кодов в уже открытой сессии браузера
    
    Args:
        driver: активный веб-драйвер
        ean_codes_batch: список EAN кодов для обработки
        download_dir: папка для скачивания файлов
        batch_number: номер группы для идентификации файла
    
    Returns:
        str: путь к скачанному файлу или None если ошибка
    """
    if not ean_codes_batch:
        print("Пустая группа EAN кодов")
        return None
    
    try:
        # Форматируем EAN коды в 13-цифровой формат
        formatted_ean_codes = []
        for code in ean_codes_batch:
            formatted_code = format_ean_to_13_digits(code)
            if formatted_code:
                formatted_ean_codes.append(formatted_code)
        
        if not formatted_ean_codes:
            print("Нет валидных EAN кодов после форматирования")
            return None
        
        print(f"Отформатировано {len(formatted_ean_codes)} EAN кодов в 13-цифровой формат")
        
        # Соединяем отформатированные EAN коды в одну строку через пробел
        ean_codes_string = ' '.join(formatted_ean_codes)
        
        print(f"DEBUG: Обрабатываем группу {batch_number} с EAN кодами: {ean_codes_string[:100]}...")
        
        # КРИТИЧЕСКИ ВАЖНО: Полный сброс страницы между группами
        print(f"Выполняем полный сброс страницы для группы {batch_number}...")
        
        # Сначала очищаем куки и локальное хранилище
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        
        # Переходим на пустую страницу для полного сброса
        driver.get("about:blank")
        time.sleep(1)
        
        # Переходим на страницу EAN Price Report заново
        driver.get("https://tradewatch.pl/report/ean-price-report.jsf")
        time.sleep(3)  # Увеличиваем время ожидания после полного сброса
        
        wait = WebDriverWait(driver, 15)  # Увеличиваем время ожидания
        
        # Ищем поле для ввода EAN кодов
        ean_field = wait.until(EC.presence_of_element_located((By.ID, "eansPhrase")))
        
        # Дополнительная проверка - убеждаемся, что поле пустое
        initial_value = ean_field.get_attribute("value")
        if initial_value and initial_value.strip():
            print(f"КРИТИЧЕСКАЯ ОШИБКА: Поле не пустое перед очисткой! Содержимое: '{initial_value}'")
            
            # Принудительная очистка всей страницы
            driver.refresh()
            time.sleep(3)
            ean_field = wait.until(EC.presence_of_element_located((By.ID, "eansPhrase")))
        
        # Тщательно очищаем поле
        if not clear_ean_field_thoroughly(driver, ean_field, batch_number):
            print(f"Критическая ошибка: не удалось очистить поле для группы {batch_number}")
            return None
        
        # Безопасно вставляем EAN коды
        if not insert_ean_codes_safely(driver, ean_field, ean_codes_string, batch_number):
            print(f"Ошибка: не удалось вставить EAN коды для группы {batch_number}")
            return None
        
        # КРИТИЧЕСКИ ВАЖНО: Проверяем, что в поле только наши коды
        final_value = ean_field.get_attribute("value")
        final_codes = final_value.strip().split() if final_value else []
        expected_codes = ean_codes_string.strip().split()
        
        # Проверяем на наличие посторонних кодов
        extra_codes = [code for code in final_codes if code not in expected_codes]
        if extra_codes:
            print(f"КРИТИЧЕСКАЯ ОШИБКА: Обнаружены посторонние коды в поле: {extra_codes}")
            print(f"Ожидались только: {expected_codes}")
            print(f"Найдено в поле: {final_codes}")
            
            # Принудительная перезагрузка и повторная попытка
            driver.refresh()
            time.sleep(3)
            ean_field = wait.until(EC.presence_of_element_located((By.ID, "eansPhrase")))
            clear_ean_field_thoroughly(driver, ean_field, batch_number)
            
        if not insert_ean_codes_safely(driver, ean_field, ean_codes_string, batch_number):
            print(f"Повторная попытка также не удалась для группы {batch_number}")
            return None
        
        # Ждем немного
        time.sleep(1)
        
        # Ищем кнопку "Generuj" надежным способом
        generate_button = find_generuj_button_safely(driver, wait)
        if not generate_button:
            print("❌ Ошибка: не удалось найти кнопку 'Generuj'")
            return None
        
        # Нажимаем кнопку
        generate_button.click()
        
        # Ждем обработки
        print("Ждем обработки запроса...")
        time.sleep(5)        # Ждем появления результатов
        print("Ждем появления результатов...")
        time.sleep(3)
        
        # Ищем кнопку "Eksport do XLS"
        try:
            export_button = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Eksport do XLS")))
            
            # Пытаемся кликнуть разными способами
            click_success = False
            
            # Способ 1: Обычный клик
            try:
                export_button.click()
                click_success = True
                print("Клик по кнопке экспорта выполнен (обычный клик)")
            except Exception as e:
                print(f"Обычный клик не сработал: {e}")
                
                # Способ 2: JavaScript клик
                try:
                    driver.execute_script("arguments[0].click();", export_button)
                    click_success = True
                    print("Клик по кнопке экспорта выполнен (JavaScript клик)")
                except Exception as js_e:
                    print(f"JavaScript клик не сработал: {js_e}")
                    
                    # Способ 3: Закрываем возможные оверлеи и пытаемся снова
                    try:
                        # Закрываем оверлеи
                        overlays = driver.find_elements(By.CLASS_NAME, "ui-widget-overlay")
                        for overlay in overlays:
                            driver.execute_script("arguments[0].style.display = 'none';", overlay)
                        
                        # Пытаемся кликнуть снова
                        time.sleep(1)
                        export_button.click()
                        click_success = True
                        print("Клик по кнопке экспорта выполнен (после закрытия оверлеев)")
                    except Exception as overlay_e:
                        print(f"Клик после закрытия оверлеев не сработал: {overlay_e}")
                        
                        # Способ 4: Scroll to element и клик
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", export_button)
                            click_success = True
                            print("Клик по кнопке экспорта выполнен (с прокруткой)")
                        except Exception as scroll_e:
                            print(f"Клик с прокруткой не сработал: {scroll_e}")
            
            if not click_success:
                print("Все методы клика не сработали, пробуем альтернативный способ...")
                raise Exception("Не удалось кликнуть по кнопке экспорта")
            
            # Если клик успешен, ждем скачивания
            # Ждем появления файла с проверкой каждые 2 секунды
            print("Ждем загрузки файла...")
            max_wait_time = 60
            wait_interval = 2
            waited_time = 0
            
            downloaded_file_found = False
            
            while waited_time < max_wait_time:
                time.sleep(wait_interval)
                waited_time += wait_interval
                
                # Ищем скачанный файл (только оригинальное имя)
                downloaded_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji.xlsx"))
                if downloaded_files:
                    # Проверяем, что файл полностью скачался
                    latest_file = safe_get_downloaded_file(downloaded_files, f"Группа {batch_number} - основная загрузка")
                    if not latest_file:
                        continue
                    
                    # Ждем немного и проверяем, что размер файла не изменился
                    initial_size = os.path.getsize(latest_file)
                    time.sleep(3)
                    
                    try:
                        final_size = os.path.getsize(latest_file)
                        if initial_size == final_size and final_size > 0:
                            print(f"Файл для группы {batch_number} загружен: {latest_file} (размер: {final_size} байт)")
                            downloaded_file_found = True
                            break
                        else:
                            print(f"Файл еще скачивается... (размер: {final_size} байт)")
                    except:
                        print(f"Файл заблокирован, продолжаем ждать...")
                        continue
                else:
                    print(f"Ожидание файла... ({waited_time}/{max_wait_time} сек)")
            
            if downloaded_file_found:
                # Переименовываем файл для идентификации
                new_filename = f"TradeWatch_batch_{batch_number}.xlsx"
                new_filepath = os.path.join(download_dir, new_filename)
                
                # Проверяем, что новый файл действительно отличается от существующего
                if os.path.exists(new_filepath):
                    try:
                        existing_size = os.path.getsize(new_filepath)
                        new_size = os.path.getsize(latest_file)
                        
                        if existing_size == new_size:
                            print(f"Файл {new_filepath} уже существует с таким же размером ({existing_size} байт), пропускаем...")
                            # Удаляем загруженный файл, так как он дублирует существующий
                            os.remove(latest_file)
                            return new_filepath
                        else:
                            print(f"Существующий файл {new_filepath} имеет другой размер ({existing_size} vs {new_size} байт), заменяем...")
                            os.remove(new_filepath)
                    except Exception as rm_e:
                        print(f"Не удалось удалить существующий файл {new_filepath}: {rm_e}")
                
                # Переименовываем файл
                try:
                    os.rename(latest_file, new_filepath)
                    print(f"Файл переименован: {latest_file} -> {new_filepath}")
                    return new_filepath
                except Exception as rename_e:
                    print(f"Ошибка при переименовании файла: {rename_e}")
                    return None
            else:
                print(f"Файл для группы {batch_number} не найден после {max_wait_time} секунд ожидания")
                return None
                
        except Exception as export_error:
            print(f"Ошибка при экспорте группы {batch_number}: {export_error}")
            
            # Дополнительная попытка с альтернативными методами
            try:
                # Попытка найти кнопку по другим селекторам
                alternative_buttons = [
                    (By.CSS_SELECTOR, "a.icon-excel"),
                    (By.CSS_SELECTOR, "a[onclick*='j_idt133']"),
                    (By.XPATH, "//a[contains(@class, 'icon-excel')]"),
                    (By.XPATH, "//a[contains(@onclick, 'j_idt133')]")
                ]
                
                button_found = False
                for selector_type, selector in alternative_buttons:
                    try:
                        alt_button = driver.find_element(selector_type, selector)
                        
                        # Удаляем оверлеи
                        driver.execute_script("""
                            var overlays = document.querySelectorAll('.ui-widget-overlay');
                            for (var i = 0; i < overlays.length; i++) {
                                overlays[i].style.display = 'none';
                            }
                        """)
                        
                        # Прокручиваем к элементу
                        driver.execute_script("arguments[0].scrollIntoView(true);", alt_button)
                        time.sleep(1)
                        
                        # Используем JavaScript для клика
                        driver.execute_script("arguments[0].click();", alt_button)
                        
                        print(f"Альтернативный метод клика сработал для группы {batch_number}")
                        button_found = True
                        break
                        
                    except Exception as alt_e:
                        continue
                
                if not button_found:
                    print(f"Все альтернативные методы не сработали для группы {batch_number}")
                    return None
                    
                # Если альтернативный метод сработал, ждем файл
                print("Ждем загрузки файла...")
                max_wait_time = 60
                wait_interval = 2
                waited_time = 0
                
                downloaded_file_found = False
                
                while waited_time < max_wait_time:
                    time.sleep(wait_interval)
                    waited_time += wait_interval
                    
                    # Ищем скачанный файл
                    downloaded_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji.xlsx"))
                    if downloaded_files:
                        latest_file = safe_get_downloaded_file(downloaded_files, f"Группа {batch_number} - альтернативная кнопка")
                        if not latest_file:
                            continue
                        
                        initial_size = os.path.getsize(latest_file)
                        time.sleep(3)
                        
                        try:
                            final_size = os.path.getsize(latest_file)
                            if initial_size == final_size and final_size > 0:
                                print(f"Файл для группы {batch_number} загружен: {latest_file} (размер: {final_size} байт)")
                                downloaded_file_found = True
                                break
                        except:
                            continue
                    else:
                        print(f"Ожидание файла... ({waited_time}/{max_wait_time} сек)")
                
                if downloaded_file_found:
                    new_filename = f"TradeWatch_batch_{batch_number}.xlsx"
                    new_filepath = os.path.join(download_dir, new_filename)
                    
                    # Проверяем, что новый файл действительно отличается от существующего
                    if os.path.exists(new_filepath):
                        try:
                            existing_size = os.path.getsize(new_filepath)
                            new_size = os.path.getsize(latest_file)
                            
                            if existing_size == new_size:
                                print(f"Файл {new_filepath} уже существует с таким же размером ({existing_size} байт), пропускаем...")
                                # Удаляем загруженный файл, так как он дублирует существующий
                                os.remove(latest_file)
                                return new_filepath
                            else:
                                print(f"Существующий файл {new_filepath} имеет другой размер ({existing_size} vs {new_size} байт), заменяем...")
                                os.remove(new_filepath)
                        except Exception as rm_e:
                            print(f"Не удалось удалить существующий файл {new_filepath}: {rm_e}")
                    
                    # Переименовываем файл
                    try:
                        os.rename(latest_file, new_filepath)
                        print(f"Файл переименован: {latest_file} -> {new_filepath}")
                        return new_filepath
                    except Exception as rename_e:
                        print(f"Ошибка при переименовании файла: {rename_e}")
                        return None
                else:
                    return None
                    
            except Exception as alt_error:
                print(f"Альтернативный метод тоже не сработал для группы {batch_number}: {alt_error}")
                return None
        
    except Exception as e:
        print(f"Ошибка при обработке группы {batch_number}: {e}")
        return None


def process_supplier_file_with_tradewatch(supplier_file_path, download_dir, headless=None, progress_callback=None):
    """
    🔥 НОВАЯ ВЕРСИЯ: Обрабатывает файл поставщика в ОДНОМ БРАУЗЕРЕ с ВКЛАДКАМИ
    Одна сессия браузера, каждая группа в новой вкладке, агрессивная очистка поля
    
    Args:
        supplier_file_path: путь к файлу поставщика
        download_dir: папка для скачивания файлов TradeWatch
        headless: запуск в headless режиме (False для наблюдения)
        progress_callback: функция для отслеживания прогресса
    
    Returns:
        list: список путей к скачанным файлам TradeWatch
    """
    # 🔥 ПЕРЕНАПРАВЛЯЕМ НА НОВУЮ ФУНКЦИЮ С ОДНИМ БРАУЗЕРОМ
    print("🔄 ПЕРЕНАПРАВЛЕНИЕ НА НОВУЮ ВЕРСИЮ С ОДНИМ БРАУЗЕРОМ И ВКЛАДКАМИ...")
    return process_supplier_file_with_tradewatch_single_browser(
        supplier_file_path, 
        download_dir, 
        headless, 
        progress_callback
    )


def process_batch_with_new_browser(ean_codes_batch, download_dir, batch_number, headless=None):
    """
    🔥 НОВАЯ ФУНКЦИЯ: Обрабатывает группу EAN кодов в НОВОЙ сессии браузера
    Это гарантированно исключает любое кеширование между группами
    
    Args:
        ean_codes_batch: список EAN кодов для обработки
        download_dir: папка для скачивания файлов
        batch_number: номер группы для идентификации файла
        headless: запуск в headless режиме или None (использовать config)
    
    Returns:
        str: путь к скачанному файлу или None если ошибка
    """
    print(f"🔥 Запускаем НОВЫЙ браузер для группы {batch_number} с {len(ean_codes_batch)} кодами")
    
    # Используем конфигурацию если headless не указан
    if headless is None:
        headless = config.HEADLESS_MODE
    
    if not ean_codes_batch:
        print("Пустая группа EAN кодов")
        return None
    
    # Настройка драйвера Chrome для НОВОЙ сессии
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    if headless:
        options.add_argument("--headless")
    
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    
    # 🔥 КРИТИЧЕСКИ ВАЖНО: Отключаем ВСЕ виды кеширования
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--no-first-run")
    options.add_argument("--safebrowsing-disable-auto-update")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--disable-preconnect")
    
    # Настройка для автоматической загрузки файлов
    download_path = Path(download_dir)
    prefs = {
        "download.default_directory": str(download_path.absolute()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    # 🆕 СОЗДАЕМ НОВЫЙ ДРАЙВЕР для каждой группы
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"🔥 НОВАЯ СЕССИЯ: Обрабатываем группу {batch_number} с {len(ean_codes_batch)} EAN кодами")
        
        # Форматируем EAN коды в 13-цифровой формат
        formatted_ean_codes = []
        for code in ean_codes_batch:
            formatted_code = format_ean_to_13_digits(code)
            if formatted_code:
                formatted_ean_codes.append(formatted_code)
        
        if not formatted_ean_codes:
            print("Нет валидных EAN кодов после форматирования")
            return None
        
        print(f"Отформатировано {len(formatted_ean_codes)} EAN кодов в 13-цифровой формат")
        
        # Соединяем отформатированные EAN коды в одну строку через пробел
        ean_codes_string = ' '.join(formatted_ean_codes)
        print(f"🔍 DEBUG: EAN коды для группы {batch_number}: {ean_codes_string[:100]}...")
        
        # Переход на страницу входа
        driver.get("https://tradewatch.pl/login.jsf")
        
        # Ждем загрузки страницы
        wait = WebDriverWait(driver, 15)
        
        # Ищем поле для email
        email_field = wait.until(EC.presence_of_element_located((By.NAME, "j_username")))
        
        # Вводим email
        email_field.clear()
        email_field.send_keys("emvertrends@gmail.com")
        
        # Ищем поле для пароля
        password_field = driver.find_element(By.NAME, "j_password")
        
        # Вводим пароль
        password_field.clear()
        password_field.send_keys("Trade-watch1")
        
        # Ищем кнопку входа
        login_button = driver.find_element(By.NAME, "btnLogin")
        
        # Нажимаем кнопку входа
        login_button.click()
        
        # Ждем немного после входа
        time.sleep(3)
        
        # Проверяем успешность входа
        current_url = driver.current_url
        
        if "login.jsf" in current_url:
            print(f"❌ Ошибка при входе в систему для группы {batch_number}")
            return None
        
        print(f"✅ Успешный вход в систему для группы {batch_number}!")
        
        # Переходим на страницу EAN Price Report
        driver.get("https://tradewatch.pl/report/ean-price-report.jsf")
        time.sleep(3)
        
        # Ищем поле для ввода EAN кодов
        ean_field = wait.until(EC.presence_of_element_located((By.ID, "eansPhrase")))
        
        # Проверяем, что поле изначально пустое (должно быть в новой сессии)
        initial_value = ean_field.get_attribute("value")
        if initial_value and initial_value.strip():
            print(f"🚨 КРИТИЧЕСКАЯ ОШИБКА: Поле не пустое в новой сессии! Содержимое: '{initial_value}'")
            return None
        else:
            print(f"✅ Поле изначально пустое в новой сессии для группы {batch_number}")
        
        # Вставляем EAN коды (поле уже должно быть пустым)
        ean_field.send_keys(ean_codes_string)
        
        # Проверяем, что вставились именно наши коды
        inserted_value = ean_field.get_attribute("value")
        inserted_codes = inserted_value.strip().split() if inserted_value else []
        expected_codes = ean_codes_string.strip().split()
        
        if len(inserted_codes) != len(expected_codes):
            print(f"⚠️ Количество вставленных кодов ({len(inserted_codes)}) не совпадает с ожидаемым ({len(expected_codes)})")
            return None
        
        print(f"✅ Вставлено {len(inserted_codes)} EAN кодов для группы {batch_number}")
        
        # Ждем немного
        time.sleep(1)
        
        # Ищем кнопку "Generuj" надежным способом
        generate_button = find_generuj_button_safely(driver, wait)
        if not generate_button:
            print(f"❌ Ошибка: не удалось найти кнопку 'Generuj' для группы {batch_number}")
            return None
        
        # Нажимаем кнопку
        generate_button.click()
        
        # Ждем обработки
        print(f"⏳ Ждем обработки запроса для группы {batch_number}...")
        time.sleep(5)
        
        # Ждем появления результатов
        print(f"⏳ Ждем появления результатов для группы {batch_number}...")
        time.sleep(3)
        
        # Очищаем старые файлы перед скачиванием
        old_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji.xlsx"))
        for old_file in old_files:
            try:
                os.remove(old_file)
            except:
                pass
        
        # Ищем кнопку "Eksport do XLS"
        export_button = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Eksport do XLS")))
        
        # Нажимаем кнопку экспорта
        export_button.click()
        
        # Ждем загрузки файла
        print(f"⏳ Ждем загрузки файла для группы {batch_number}...")
        max_wait_time = 60
        wait_interval = 2
        waited_time = 0
        
        downloaded_file_found = False
        
        while waited_time < max_wait_time:
            time.sleep(wait_interval)
            waited_time += wait_interval
            
            # Ищем скачанный файл
            downloaded_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji.xlsx"))
            if downloaded_files:
                latest_file = safe_get_downloaded_file(downloaded_files, f"Группа {batch_number} - финальная проверка")
                if not latest_file:
                    continue
                
                # Проверяем стабильность размера файла
                initial_size = os.path.getsize(latest_file)
                time.sleep(3)
                
                try:
                    final_size = os.path.getsize(latest_file)
                    if initial_size == final_size and final_size > 0:
                        print(f"✅ Файл для группы {batch_number} загружен: {latest_file} (размер: {final_size} байт)")
                        downloaded_file_found = True
                        break
                    else:
                        print(f"⏳ Файл еще скачивается... (размер: {final_size} байт)")
                except:
                    print(f"⏳ Файл заблокирован, продолжаем ждать...")
                    continue
            else:
                print(f"⏳ Ожидание файла... ({waited_time}/{max_wait_time} сек)")
        
        if downloaded_file_found:
            # Переименовываем файл с оригинальным названием и датой/временем
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"TradeWatch_raport_konkurencji_{timestamp}.xlsx"
            new_filepath = os.path.join(download_dir, new_filename)
            
            # Убеждаемся, что целевой файл не существует
            if os.path.exists(new_filepath):
                try:
                    os.remove(new_filepath)
                    print(f"🗑️ Удален существующий файл: {new_filepath}")
                except Exception as rm_e:
                    print(f"❌ Не удалось удалить существующий файл {new_filepath}: {rm_e}")
            
            # Переименовываем файл
            try:
                os.rename(latest_file, new_filepath)
                print(f"✅ Файл переименован: {latest_file} -> {new_filepath}")
                return new_filepath
            except Exception as rename_e:
                print(f"❌ Ошибка при переименовании файла: {rename_e}")
                return None
        else:
            print(f"❌ Файл для группы {batch_number} не найден после {max_wait_time} секунд ожидания")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при обработке группы {batch_number} в новой сессии: {e}")
        return None
    
    finally:
        # 🔥 КРИТИЧЕСКИ ВАЖНО: Закрываем браузер после каждой группы
        print(f"🔒 Закрываем браузер для группы {batch_number}")
        driver.quit()


def process_supplier_file_with_tradewatch_old_version(supplier_file_path, download_dir, headless=None):
    """
    Обрабатывает файл поставщика: извлекает EAN коды, 
    разбивает на группы и получает данные из TradeWatch
    Использует одну сессию браузера для всех групп
    
    Args:
        supplier_file_path: путь к файлу поставщика
        download_dir: папка для скачивания файлов TradeWatch
        headless: запуск в headless режиме или None (использовать config)
    
    Returns:
        list: список путей к скачанным файлам TradeWatch
    """
    # Используем конфигурацию если headless не указан
    if headless is None:
        headless = config.HEADLESS_MODE
        
    try:
        # Читаем файл поставщика
        print(f"Читаем файл поставщика: {supplier_file_path}")
        df = pd.read_excel(supplier_file_path)
        
        # Проверяем наличие необходимых колонок
        if 'GTIN' not in df.columns:
            print("Ошибка: В файле поставщика нет колонки GTIN")
            return []
        
        if 'Price' not in df.columns:
            print("Ошибка: В файле поставщика нет колонки Price")
            return []
        
        # Извлекаем EAN коды
        ean_codes = df['GTIN'].dropna().astype(str).tolist()
        # Удаляем пустые и некорректные коды
        ean_codes = [code.strip() for code in ean_codes if code.strip() and code.strip() != 'nan']
        
        print(f"Найдено {len(ean_codes)} EAN кодов в файле поставщика")
        
        if not ean_codes:
            print("Нет EAN кодов для обработки")
            return []
        
        # Разбиваем на группы по размеру из конфигурации
        batch_size = config.BATCH_SIZE
        batches = [ean_codes[i:i + batch_size] for i in range(0, len(ean_codes), batch_size)]
        
        print(f"Разбиваем на {len(batches)} групп по {batch_size} кодов")
        
        # Создаем папку для скачивания если её нет
        download_path = Path(download_dir)
        download_path.mkdir(parents=True, exist_ok=True)
        
        # Очищаем все старые файлы TradeWatch перед началом обработки
        print("Очищаем старые файлы TradeWatch...")
        old_files_patterns = [
            "TradeWatch - raport konkurencji*.xlsx",
            "TradeWatch_raport_konkurencji_*.xlsx"
        ]
        
        for pattern in old_files_patterns:
            old_files = glob.glob(os.path.join(download_dir, pattern))
            for old_file in old_files:
                try:
                    os.remove(old_file)
                    print(f"Удален старый файл: {old_file}")
                except Exception as e:
                    print(f"Не удалось удалить файл {old_file}: {e}")
                    pass
        
        # Настройка драйвера Chrome один раз
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        if headless:
            options.add_argument("--headless")
        
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-logging")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        
        # Настройка для автоматической загрузки файлов
        prefs = {
            "download.default_directory": str(download_path.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        # Инициализация драйвера один раз
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        try:
            print("Запускаем браузер и выполняем вход в систему...")
            
            # Переход на страницу входа
            driver.get("https://tradewatch.pl/login.jsf")
            
            # Ждем загрузки страницы
            wait = WebDriverWait(driver, 10)
            
            # Ищем поле для email
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "j_username")))
            
            # Вводим email
            email_field.clear()
            email_field.send_keys("emvertrends@gmail.com")
            
            # Ищем поле для пароля
            password_field = driver.find_element(By.NAME, "j_password")
            
            # Вводим пароль
            password_field.clear()
            password_field.send_keys("Trade-watch1")
            
            # Ищем кнопку входа
            login_button = driver.find_element(By.NAME, "btnLogin")
            
            # Нажимаем кнопку входа
            login_button.click()
            
            # Ждем немного после входа
            time.sleep(3)
            
            # Проверяем успешность входа
            current_url = driver.current_url
            
            if "login.jsf" in current_url:
                print("Ошибка при входе в систему")
                return []
            
            print("✅ Успешный вход в систему! Начинаем обработку групп...")
            
            # Обрабатываем группы последовательно в одной сессии (стабильный подход)
            print(f"Обрабатываем {len(batches)} групп последовательно в одной сессии")
            downloaded_files = []
            
            for i, batch in enumerate(batches, 1):
                print(f"\nОбрабатываем группу {i}/{len(batches)} ({len(batch)} EAN кодов)")
                
                # Проверяем, что файл группы уже не существует
                target_filename = f"TradeWatch_batch_{i}.xlsx"
                target_filepath = os.path.join(download_dir, target_filename)
                
                if os.path.exists(target_filepath):
                    existing_size = os.path.getsize(target_filepath)
                    if existing_size > 0:
                        print(f"Файл группы {i} уже существует ({existing_size} байт), пропускаем обработку...")
                        downloaded_files.append(target_filepath)
                        continue
                
                # Очищаем старые файлы перед обработкой группы
                # Удаляем файлы с оригинальным именем
                old_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji.xlsx"))
                for old_file in old_files:
                    try:
                        os.remove(old_file)
                        print(f"Удален старый файл: {old_file}")
                    except:
                        pass
                
                # Также удаляем файл с целевым именем, если он существует
                if os.path.exists(target_filepath):
                    try:
                        os.remove(target_filepath)
                        print(f"Удален существующий файл: {target_filepath}")
                    except:
                        pass
                
                # Обрабатываем группу в той же сессии
                result = process_batch_in_session(driver, batch, download_dir, i)
                
                if result:
                    downloaded_files.append(result)
                    print(f"✅ Группа {i} обработана успешно")
                else:
                    print(f"❌ Ошибка при обработке группы {i}")
                
                # КРИТИЧЕСКИ ВАЖНАЯ пауза между группами для полного сброса
                if i < len(batches):
                    print(f"🔄 ВАЖНАЯ ПАУЗА между группами {i} и {i+1} для предотвращения дублирования...")
                    time.sleep(5)  # Увеличиваем до 5 секунд для полного сброса
                    
                    # Дополнительная очистка кеша браузера между группами
                    driver.execute_script("localStorage.clear(); sessionStorage.clear();")
                    print(f"🧹 Очищен кеш браузера между группами {i} и {i+1}")
            
            print(f"\nОбработка завершена. Загружено {len(downloaded_files)} файлов из {len(batches)} групп")
            
            # Проверяем, что все файлы существуют
            print("Проверка существования файлов:")
            existing_files = []
            for i, file_path in enumerate(downloaded_files):
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    print(f"  ✅ {file_path} (размер: {size} байт)")
                    existing_files.append(file_path)
                else:
                    print(f"  ❌ {file_path} - НЕ НАЙДЕН!")
            
            # КРИТИЧЕСКИ ВАЖНО: Проверяем уникальность содержимого
            if existing_files:
                verify_batch_uniqueness(existing_files)
            
            return downloaded_files
            
        finally:
            # Закрываем браузер в конце
            print("🔒 Закрываем браузер...")
            try:
                driver.quit()
            except Exception as e:
                print(f"⚠️ Ошибка при закрытии браузера: {e}")
            
            # Очистка памяти после закрытия браузера
            try:
                import gc
                gc.collect()  # Принудительная сборка мусора
                print("🧹 Память очищена после закрытия браузера")
            except Exception as e:
                print(f"⚠️ Ошибка при очистке памяти: {e}")
        
    except Exception as e:
        print(f"Ошибка при обработке файла поставщика: {e}")
        return []


def login_to_tradewatch():
    """
    Оригинальная функция для совместимости (устарела)
    """
    print("Эта функция устарела. Используйте process_supplier_file_with_tradewatch()")
    pass


def process_multiple_batches_parallel(main_driver, ean_groups, download_dir, max_parallel=None):
    """
    Обрабатывает несколько групп EAN кодов параллельно в отдельных браузерах
    
    Args:
        main_driver: основной веб-драйвер (не используется, но нужен для совместимости)
        ean_groups: список групп EAN кодов
        download_dir: папка для скачивания файлов
        max_parallel: максимальное количество параллельных браузеров или None (использовать config)
    
    Returns:
        list: список путей к скачанным файлам
    """
    # Используем конфигурацию если max_parallel не указан
    if max_parallel is None:
        max_parallel = config.MAX_PARALLEL_BROWSERS
    
    results = []
    
    # Обрабатываем группы по max_parallel штук
    for i in range(0, len(ean_groups), max_parallel):
        batch_to_process = ean_groups[i:i + max_parallel]
        
        print(f"Обрабатываем параллельно группы {i+1}-{min(i+max_parallel, len(ean_groups))}")
        
        # Используем потоки для параллельной обработки с отдельными браузерами
        with concurrent.futures.ThreadPoolExecutor(max_workers=current_max_parallel) as executor:
            futures = []
            
            for j, group in enumerate(batch_to_process):
                batch_number = i + j + 1
                
                # Проверяем ресурсы перед запуском браузера
                resources_ok, recommended = check_system_resources()
                if not resources_ok:
                    print(f"⏳ Ждем освобождения ресурсов перед запуском браузера {batch_number}...")
                    time.sleep(5)
                    # Повторная проверка
                    resources_ok, recommended = check_system_resources()
                    if not resources_ok:
                        print(f"⚠️ Ресурсы все еще недоступны, пропускаем браузер {batch_number}")
                        continue
                
                # Добавляем задержку между запусками браузеров для предотвращения перегрузки
                if j > 0:
                    delay = config.RESOURCE_MANAGEMENT.get('browser_start_delay', 2)
                    time.sleep(delay)
                
                future = executor.submit(
                    process_batch_in_separate_browser, 
                    group, 
                    download_dir, 
                    batch_number
                )
                futures.append(future)
            
            # Собираем результаты
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    error_message = str(e).lower()
                    
                    # Определяем тип ошибки
                    if any(keyword in error_message for keyword in ['connection', 'timeout', 'network', 'unreachable']):
                        print(f"🌐 Сетевая ошибка при обработке группы (браузер не перезапускается): {e}")
                        # Не перезапускаем браузер при сетевых ошибках
                    elif any(keyword in error_message for keyword in ['webdriver', 'chrome', 'browser', 'driver']):
                        print(f"🔧 Ошибка браузера при обработке группы: {e}")
                        # При ошибках браузера тоже не перезапускаем
                    else:
                        print(f"❌ Неизвестная ошибка при обработке группы: {e}")
                        # Для других ошибок логируем для анализа
        
        if i + max_parallel < len(ean_groups):
            print("Пауза между пакетами групп...")
            time.sleep(3)
    
    return results


def process_batch_in_separate_browser(ean_codes_batch, download_dir, batch_number):
    """
    Обрабатывает группу EAN кодов в отдельном браузере
    
    Args:
        ean_codes_batch: список EAN кодов для обработки
        download_dir: папка для скачивания файлов
        batch_number: номер группы
    
    Returns:
        str: путь к скачанному файлу или None
    """
    driver = None
    try:
        # Создаем отдельный браузер для этой группы
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        # Настройки Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Настройки загрузки
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Создаем драйвер
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print(f"Создан браузер для группы {batch_number}")
        
        # Вход в систему
        driver.get("https://tradewatch.pl/login.jsf")
        
        # Ждем загрузки страницы
        wait = WebDriverWait(driver, 20)
        
        # Вводим логин
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        username_field.clear()
        username_field.send_keys("emvertrends@gmail.com")
        
        # Вводим пароль
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys("Trade-watch1")
        
        # Нажимаем кнопку входа
        login_button = driver.find_element(By.NAME, "btnLogin")
        login_button.click()
        
        time.sleep(3)
        
        # Проверяем успешность входа
        current_url = driver.current_url
        if "login.jsf" in current_url:
            print(f"Ошибка при входе в систему для группы {batch_number}")
            return None
            
        print(f"Успешный вход для группы {batch_number}")
        
        # Переходим на страницу EAN Price Report
        driver.get("https://tradewatch.pl/report/ean-price-report.jsf")
        
        # Соединяем EAN коды в одну строку
        ean_codes_string = ' '.join(str(code) for code in ean_codes_batch)
        
        # Ищем текстовое поле для ввода EAN кодов
        ean_input = wait.until(EC.presence_of_element_located((By.ID, "report_form:ean_codes")))
        ean_input.clear()
        ean_input.send_keys(ean_codes_string)
        
        print(f"Вставлены EAN коды для группы {batch_number}: {len(ean_codes_batch)} кодов")
        
        # Нажимаем кнопку "Szukaj"
        search_button = wait.until(EC.element_to_be_clickable((By.ID, "report_form:search_button")))
        search_button.click()
        
        print(f"Ждем обработки запроса для группы {batch_number}...")
        time.sleep(5)
        
        # Ждем появления результатов
        wait.until(EC.presence_of_element_located((By.ID, "report_form:results")))
        print(f"Ждем появления результатов для группы {batch_number}...")
        time.sleep(3)
        
        # Экспортируем результаты
        return export_results_for_separate_browser(driver, download_dir, batch_number, wait)
        
    except Exception as e:
        print(f"Ошибка при обработке группы {batch_number}: {e}")
        return None
    finally:
        # Обязательно закрываем браузер
        if driver:
            try:
                driver.quit()
                print(f"Браузер для группы {batch_number} закрыт")
            except:
                pass


def export_results_for_separate_browser(driver, download_dir, batch_number, wait):
    """
    Экспортирует результаты для отдельного браузера
    """
    try:
        # Очищаем старые файлы
        old_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji*.xlsx"))
        for old_file in old_files:
            try:
                os.remove(old_file)
            except:
                pass
        
        export_button = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Eksport do XLS")))
        
        # Пытаемся кликнуть разными способами
        click_success = False
        
        # Способ 1: Обычный клик
        try:
            export_button.click()
            click_success = True
            print(f"Клик по кнопке экспорта выполнен для группы {batch_number} (обычный клик)")
        except Exception as e:
            print(f"Обычный клик не сработал для группы {batch_number}: {e}")
            
            # Способ 2: JavaScript клик
            try:
                driver.execute_script("arguments[0].click();", export_button)
                click_success = True
                print(f"Клик по кнопке экспорта выполнен для группы {batch_number} (JavaScript клик)")
            except Exception as js_e:
                print(f"JavaScript клик не сработал для группы {batch_number}: {js_e}")
                
                # Способ 3: Закрываем оверлеи
                try:
                    overlays = driver.find_elements(By.CLASS_NAME, "ui-widget-overlay")
                    for overlay in overlays:
                        driver.execute_script("arguments[0].style.display = 'none';", overlay)
                    
                    time.sleep(1)
                    export_button.click()
                    click_success = True
                    print(f"Клик по кнопке экспорта выполнен для группы {batch_number} (после закрытия оверлеев)")
                except Exception as overlay_e:
                    print(f"Клик после закрытия оверлеев не сработал для группы {batch_number}: {overlay_e}")
        
        if not click_success:
            print(f"Все методы клика не сработали для группы {batch_number}")
            return None
        
        # Ждем загрузки файла
        print(f"Ждем загрузки файла для группы {batch_number}...")
        return wait_for_download_separate_browser(download_dir, batch_number)
        
    except Exception as e:
        print(f"Ошибка при экспорте группы {batch_number}: {e}")
        return None


def wait_for_download_separate_browser(download_dir, batch_number):
    """
    Ждет загрузки файла для отдельного браузера
    """
    max_wait_time = 60
    wait_interval = 2
    waited_time = 0
    
    while waited_time < max_wait_time:
        time.sleep(wait_interval)
        waited_time += wait_interval
        
        # Ищем скачанный файл
        downloaded_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji*.xlsx"))
        if downloaded_files:
            # Берем самый новый файл
            latest_file = max(downloaded_files, key=os.path.getctime)
            
            # Проверяем стабильность размера
            initial_size = os.path.getsize(latest_file)
            time.sleep(3)
            
            try:
                final_size = os.path.getsize(latest_file)
                if initial_size == final_size and final_size > 0:
                    print(f"Файл для группы {batch_number} загружен: {latest_file} (размер: {final_size} байт)")
                    
                    # Переименовываем файл
                    new_filename = f"TradeWatch_batch_{batch_number}.xlsx"
                    new_filepath = os.path.join(download_dir, new_filename)
                    
                    if os.path.exists(new_filepath):
                        os.remove(new_filepath)
                    
                    os.rename(latest_file, new_filepath)
                    return new_filepath
                else:
                    print(f"Файл для группы {batch_number} еще скачивается... (размер: {final_size} байт)")
            except:
                print(f"Файл для группы {batch_number} заблокирован, продолжаем ждать...")
                continue
        else:
            print(f"Ожидание файла для группы {batch_number}... ({waited_time}/{max_wait_time} сек)")
    
    print(f"Файл для группы {batch_number} не найден после {max_wait_time} секунд ожидания")
    return None


def process_supplier_file_with_tradewatch_interruptible(supplier_file_path, download_dir, stop_flag_callback=None, progress_callback=None, headless=None):
    """
    Обрабатывает файл поставщика с возможностью остановки процесса
    
    Args:
        supplier_file_path: путь к файлу поставщика
        download_dir: папка для скачивания файлов TradeWatch
        stop_flag_callback: функция для проверки флага остановки
        progress_callback: функция для обновления прогресса
        headless: запуск в headless режиме или None (использовать config)
    
    Returns:
        list: список путей к скачанным файлам TradeWatch
    """
    # Используем конфигурацию если headless не указан
    if headless is None:
        headless = config.HEADLESS_MODE
        
    try:
        # Читаем файл поставщика
        print(f"Читаем файл поставщика: {supplier_file_path}")
        df = pd.read_excel(supplier_file_path)
        
        # Проверяем наличие необходимых колонок
        if 'GTIN' not in df.columns:
            print("Ошибка: В файле поставщика нет колонки GTIN")
            return []
        
        if 'Price' not in df.columns:
            print("Ошибка: В файле поставщика нет колонки Price")
            return []
        
        # Извлекаем EAN коды
        ean_codes = df['GTIN'].dropna().astype(str).tolist()
        # Удаляем пустые и некорректные коды
        ean_codes = [code.strip() for code in ean_codes if code.strip() and code.strip() != 'nan']
        
        print(f"Найдено {len(ean_codes)} EAN кодов в файле поставщика")
        
        if not ean_codes:
            print("Нет EAN кодов для обработки")
            return []
        
        # Разбиваем на группы по размеру из конфигурации
        batch_size = config.BATCH_SIZE
        batches = [ean_codes[i:i + batch_size] for i in range(0, len(ean_codes), batch_size)]
        
        print(f"Разбиваем на {len(batches)} групп по {batch_size} кодов")
        
        # Создаем папку для скачивания если её нет
        download_path = Path(download_dir)
        download_path.mkdir(parents=True, exist_ok=True)
        
        # Очищаем все старые файлы TradeWatch перед началом обработки
        print("Очищаем старые файлы TradeWatch...")
        old_files_patterns = [
            "TradeWatch - raport konkurencji*.xlsx",
            "TradeWatch_raport_konkurencji_*.xlsx"
        ]
        
        for pattern in old_files_patterns:
            old_files = glob.glob(os.path.join(download_dir, pattern))
            for old_file in old_files:
                try:
                    os.remove(old_file)
                    print(f"Удален старый файл: {old_file}")
                except Exception as e:
                    print(f"Не удалось удалить файл {old_file}: {e}")
                    pass
        
        # Обрабатываем каждую группу в отдельной сессии браузера
        print(f"🔥 НОВАЯ ЛОГИКА: Каждая группа обрабатывается в отдельной сессии браузера")
        downloaded_files = []
        
        for i, batch in enumerate(batches, 1):
            # Проверяем флаг остановки
            if stop_flag_callback and stop_flag_callback():
                print(f"🛑 Получен сигнал остановки. Прерываем обработку на группе {i}/{len(batches)}")
                break
            
            # Обновляем прогресс
            if progress_callback:
                progress_callback(f"🔄 Обрабатываю группу {i}/{len(batches)} ({len(batch)} EAN кодов)...")
            
            print(f"\n🆕 СОЗДАЕМ НОВУЮ СЕССИЮ БРАУЗЕРА для группы {i}/{len(batches)}")
            
            # Обрабатываем группу в новой сессии браузера
            result = process_batch_with_new_browser(batch, download_dir, i, headless)
            
            if result:
                downloaded_files.append(result)
                print(f"✅ Группа {i} обработана успешно в новой сессии")
            else:
                print(f"❌ Ошибка при обработке группы {i} в новой сессии")
        
        if stop_flag_callback and stop_flag_callback():
            print(f"\n🛑 Процесс остановлен пользователем. Обработано {len(downloaded_files)} из {len(batches)} групп")
        else:
            print(f"\n🏁 Обработка завершена. Загружено {len(downloaded_files)} файлов из {len(batches)} групп")
        
        # Проверяем, что все файлы существуют
        print("Проверка существования файлов:")
        existing_files = []
        for i, file_path in enumerate(downloaded_files):
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {file_path} (размер: {size} байт)")
                existing_files.append(file_path)
            else:
                print(f"  ❌ {file_path} - НЕ НАЙДЕН!")
        
        # Проверяем уникальность содержимого
        if existing_files:
            verify_batch_uniqueness(existing_files)
        
        return downloaded_files
        
    except Exception as e:
        print(f"Ошибка при обработке файла поставщика: {e}")
        return []


def initialize_browser_and_login(headless=None, download_dir=None):
    """
    Инициализирует браузер один раз, логинится в TradeWatch и сохраняет сессию

    Args:
        headless: запуск в headless режиме или None (использовать config)
        download_dir: папка для скачивания файлов (если не указана, используется текущая)

    Returns:
        webdriver.Chrome: инициализированный драйвер с активной сессией
    """
    # Используем конфигурацию если headless не указан
    if headless is None:
        headless = config.HEADLESS_MODE
        
    print("🚀 ИНИЦИАЛИЗАЦИЯ БРАУЗЕРА: Создаем один браузер для всех групп")
    print(f"🔧 Используем headless режим: {headless}")

    # Настройка драйвера Chrome для Railway/Linux
    options = webdriver.ChromeOptions()

    # Основные аргументы для работы в контейнере
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--no-first-run")
    options.add_argument("--safebrowsing-disable-auto-update")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--disable-preconnect")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-application-cache")
    options.add_argument("--window-size=1920,1080")

    # 🔥 ОТКЛЮЧАЕМ HEADLESS РЕЖИМ для наблюдения
    if headless:
        options.add_argument("--headless")
    else:
        print("👁️  HEADLESS РЕЖИМ ОТКЛЮЧЕН - можно наблюдать за процессом")

    # 🔥 КРИТИЧЕСКИ ВАЖНО: Настраиваем папку для скачивания файлов
    if download_dir:
        download_path = Path(download_dir)
        download_path.mkdir(parents=True, exist_ok=True)

        prefs = {
            "download.default_directory": str(download_path.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        print(f"📁 Папка для скачивания: {download_path.absolute()}")
    else:
        print("⚠️  ВНИМАНИЕ: Папка для скачивания не указана - файлы будут скачиваться в папку по умолчанию")

    # Создаем драйвер для Railway/Linux
    try:
        # Пытаемся использовать системный Chrome
        options.binary_location = "/usr/bin/google-chrome"  # Путь к Chrome в Railway
        service = Service(executable_path="/usr/bin/chromedriver")  # Путь к chromedriver
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ Используем системный Chrome")
    except Exception as e:
        print(f"⚠️  Системный Chrome не найден, пробуем ChromeDriverManager: {e}")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            print("✅ Используем ChromeDriverManager")
        except Exception as e2:
            print(f"❌ Ошибка создания драйвера: {e2}")
            raise e2

    try:
        print("🔐 ЛОГИНИМСЯ В TRADEWATCH...")

        # Переход на страницу входа
        driver.get("https://tradewatch.pl/login.jsf")

        # Ждем загрузки страницы
        wait = WebDriverWait(driver, 15)

        # Ищем поле для email
        email_field = wait.until(EC.presence_of_element_located((By.NAME, "j_username")))

        # Вводим email
        email_field.clear()
        email_field.send_keys("emvertrends@gmail.com")

        # Ищем поле для пароля
        password_field = driver.find_element(By.NAME, "j_password")

        # Вводим пароль
        password_field.clear()
        password_field.send_keys("Trade-watch1")

        # Ищем кнопку входа
        login_button = driver.find_element(By.NAME, "btnLogin")

        # Нажимаем кнопку входа
        login_button.click()

        # Ждем немного после входа
        time.sleep(3)

        # Проверяем успешность входа
        current_url = driver.current_url

        if "login.jsf" in current_url:
            print("❌ ОШИБКА: Не удалось войти в систему!")
            driver.quit()
            return None

        print("✅ УСПЕШНЫЙ ВХОД В TRADEWATCH!")
        print("🔄 ГОТОВ К ОБРАБОТКЕ ГРУПП EAN В ВКЛАДКАХ")

        return driver

    except Exception as e:
        print(f"❌ ОШИБКА при инициализации браузера: {e}")
        driver.quit()
        return None


def process_batch_in_tab(driver, ean_codes_batch, download_dir, batch_number):
    """
    Обрабатывает группу EAN кодов в НОВОЙ ВКЛАДКЕ с агрессивной очисткой поля

    Args:
        driver: инициализированный драйвер с активной сессией
        ean_codes_batch: список EAN кодов для обработки
        download_dir: папка для скачивания файлов
        batch_number: номер группы для идентификации

    Returns:
        str: путь к скачанному файлу или None если ошибка
    """
    if not ean_codes_batch:
        print(f"❌ Группа {batch_number} пустая")
        return None

    # Проверяем, что папка для скачивания существует и доступна
    if not os.path.exists(download_dir):
        print(f"❌ Папка для скачивания не существует: {download_dir}")
        return None

    if not os.access(download_dir, os.W_OK):
        print(f"❌ Нет прав на запись в папку: {download_dir}")
        return None

    print(f"📁 Папка для скачивания проверена: {download_dir}")

    original_window = driver.current_window_handle
    new_tab = None

    try:
        print(f"📑 ОТКРЫВАЕМ НОВУЮ ВКЛАДКУ для группы {batch_number} с {len(ean_codes_batch)} EAN кодами")

        # Открываем новую вкладку
        driver.execute_script("window.open('https://tradewatch.pl/report/ean-price-report.jsf', '_blank');")
        time.sleep(2)

        # Переключаемся на новую вкладку
        windows = driver.window_handles
        new_tab = [w for w in windows if w != original_window][0]
        driver.switch_to.window(new_tab)

        print(f"✅ Переключились на новую вкладку для группы {batch_number}")

        # Ждем загрузки страницы
        wait = WebDriverWait(driver, 15)

        # Ищем поле для ввода EAN кодов
        ean_field = wait.until(EC.presence_of_element_located((By.ID, "eansPhrase")))

        # 🔥 АГРЕССИВНАЯ ОЧИСТКА ПОЛЯ ПЕРЕД ВВОДОМ
        print(f"🧹 АГРЕССИВНАЯ ОЧИСТКА поля EAN для группы {batch_number}...")
        clear_ean_field_thoroughly(driver, ean_field, batch_number)

        # Проверяем, что поле пустое после очистки
        final_value = ean_field.get_attribute("value")
        if final_value and final_value.strip():
            print(f"⚠️  ВНИМАНИЕ: Поле не полностью очищено: '{final_value}'")
        else:
            print(f"✅ Поле успешно очищено для группы {batch_number}")

        # Форматируем EAN коды в 13-цифровой формат
        formatted_ean_codes = []
        for code in ean_codes_batch:
            formatted_code = format_ean_to_13_digits(code)
            if formatted_code:
                formatted_ean_codes.append(formatted_code)

        if not formatted_ean_codes:
            print(f"❌ Нет валидных EAN кодов после форматирования для группы {batch_number}")
            return None

        print(f"📝 Отформатировано {len(formatted_ean_codes)} EAN кодов для группы {batch_number}")

        # Соединяем отформатированные EAN коды в одну строку через пробел
        ean_codes_string = ' '.join(formatted_ean_codes)
        print(f"🔍 EAN коды для группы {batch_number}: {ean_codes_string[:100]}...")

        # Вставляем EAN коды
        ean_field.send_keys(ean_codes_string)

        # Проверяем, что вставились наши коды
        inserted_value = ean_field.get_attribute("value")
        inserted_codes = inserted_value.strip().split() if inserted_value else []
        expected_codes = ean_codes_string.strip().split()

        if len(inserted_codes) != len(expected_codes):
            print(f"⚠️  Количество вставленных кодов ({len(inserted_codes)}) не совпадает с ожидаемым ({len(expected_codes)})")
            return None

        print(f"✅ Вставлено {len(inserted_codes)} EAN кодов для группы {batch_number}")

        # Ждем немного
        time.sleep(1)

        # Ищем кнопку "Generuj" надежным способом
        generate_button = find_generuj_button_safely(driver, wait)
        if not generate_button:
            print(f"❌ Не удалось найти кнопку 'Generuj' для группы {batch_number}")
            return None

        # Нажимаем кнопку
        generate_button.click()

        # Ждем обработки
        print(f"⏳ Ждем обработки запроса для группы {batch_number}...")
        time.sleep(5)

        # Ждем появления результатов
        print(f"⏳ Ждем появления результатов для группы {batch_number}...")
        time.sleep(3)

        # 🔥 ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА ЗАГРУЗКИ СТРАНИЦЫ
        try:
            # Ждем, пока страница полностью загрузится
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            print(f"✅ Страница полностью загружена для группы {batch_number}")
            
            # Ждем исчезновения любых loading индикаторов
            time.sleep(2)
            
        except Exception as e:
            print(f"⚠️ Ошибка при проверке загрузки страницы: {e}")

        # 🔥 ЖДЕМ ИСЧЕЗНОВЕНИЯ OVERLAY ПЕРЕД ЭКСПОРТОМ
        print(f"🛡️ Ждем исчезновения overlay для группы {batch_number}...")
        try:
            # Ждем исчезновения overlay элементов
            overlay_selectors = [
                ".ui-widget-overlay",
                ".ui-overlay", 
                "[class*='overlay']",
                ".modal-backdrop",
                ".loading-overlay",
                ".ui-blockui",  # Дополнительный селектор для блокирующих overlay
                ".blockUI"
            ]
            
            for selector in overlay_selectors:
                try:
                    # Ждем, пока overlay исчезнет или станет невидимым
                    wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, selector)) == 0 or 
                              (len(driver.find_elements(By.CSS_SELECTOR, selector)) > 0 and 
                               not driver.find_element(By.CSS_SELECTOR, selector).is_displayed()))
                    print(f"✅ Overlay {selector} исчез")
                except:
                    print(f"⚠️ Overlay {selector} не найден или уже исчез")
                    pass
            
            # Дополнительное ожидание для стабильности
            time.sleep(2)
            
        except Exception as e:
            print(f"⚠️ Ошибка при ожидании overlay: {e}")

        # 🔥 ГЕНЕРИРУЕМ УНИКАЛЬНОЕ ИМЯ ФАЙЛА ЗАРАНЕЕ
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"TradeWatch_raport_konkurencji_{timestamp}.xlsx"
        expected_filepath = os.path.join(download_dir, unique_filename)
        print(f"📄 Ожидаемое имя файла для группы {batch_number}: {unique_filename}")

        # 🔥 ЖДЕМ ИСЧЕЗНОВЕНИЯ OVERLAY ПЕРЕД ЭКСПОРТОМ
        print(f"🛡️ Ждем исчезновения overlay для группы {batch_number}...")
        try:
            # Ждем исчезновения overlay элементов
            overlay_selectors = [
                ".ui-widget-overlay",
                ".ui-overlay", 
                "[class*='overlay']",
                ".modal-backdrop",
                ".loading-overlay",
                ".ui-blockui",  # Дополнительный селектор для блокирующих overlay
                ".blockUI"
            ]
            
            for selector in overlay_selectors:
                try:
                    # Ждем, пока overlay исчезнет или станет невидимым
                    wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, selector)) == 0 or 
                              (len(driver.find_elements(By.CSS_SELECTOR, selector)) > 0 and 
                               not driver.find_element(By.CSS_SELECTOR, selector).is_displayed()))
                    print(f"✅ Overlay {selector} исчез")
                except:
                    print(f"⚠️ Overlay {selector} не найден или уже исчез")
                    pass
            
            # Дополнительное ожидание для стабильности
            time.sleep(2)
            
        except Exception as e:
            print(f"⚠️ Ошибка при ожидании overlay: {e}")

        # 🔥 ИСПОЛЬЗУЕМ JAVASCRIPT ДЛЯ ИЗМЕНЕНИЯ ИМЕНИ ФАЙЛА ПЕРЕД СКАЧИВАНИЕМ
        print(f"🔍 Поиск кнопки экспорта для группы {batch_number}...")
        
        # Ищем кнопку "Eksport do XLS" с повторными попытками
        export_button = None
        max_attempts = 5  # Увеличиваем количество попыток
        
        for attempt in range(max_attempts):
            try:
                print(f"🔍 Поиск кнопки экспорта (попытка {attempt + 1}/{max_attempts})")
                
                # Проверяем, что кнопка существует и кликабельна
                export_button = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Eksport do XLS")))
                
                # Дополнительная проверка на кликабельность
                if export_button.is_displayed() and export_button.is_enabled():
                    print(f"✅ Кнопка экспорта найдена и готова к клику")
                    
                    # 🔥 ИЗМЕНЯЕМ АТРИБУТ DOWNLOAD С ПОМОЩЬЮ JAVASCRIPT
                    driver.execute_script(f"arguments[0].setAttribute('download', '{unique_filename}');", export_button)
                    print(f"✅ Установлено уникальное имя файла: {unique_filename}")
                    break
                else:
                    print(f"⚠️ Кнопка найдена, но не кликабельна (попытка {attempt + 1})")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"⚠️ Не удалось найти кнопку экспорта (попытка {attempt + 1}): {e}")
                time.sleep(2)
        
        if not export_button:
            print(f"❌ Не удалось найти кнопку экспорта после {max_attempts} попыток")
            return None

        # 🔥 КЛИКАЕМ ПО КНОПКЕ ЭКСПОРТА
        print(f"🖱️ Кликаем по кнопке экспорта для группы {batch_number}")
        try:
            # Сначала пробуем обычный клик
            export_button.click()
            print(f"✅ Обычный клик по кнопке экспорта успешен")
        except Exception as e:
            print(f"⚠️ Обычный клик не удался: {e}")
            print(f"🔄 Пробуем JavaScript клик...")
            try:
                # JavaScript клик как запасной вариант
                driver.execute_script("arguments[0].click();", export_button)
                print(f"✅ JavaScript клик по кнопке экспорта успешен")
            except Exception as js_e:
                print(f"❌ JavaScript клик тоже не удался: {js_e}")
                return None        # 🔥 АЛЬТЕРНАТИВНЫЙ ПОДХОД: ПЕРЕИМЕНОВАНИЕ ПОСЛЕ СКАЧИВАНИЯ
        print(f"🔄 Используем альтернативный подход: скачивание с последующим переименованием")

        # Ждем загрузки файла с оригинальным именем
        print(f"⏳ Ждем загрузки файла для группы {batch_number}...")
        max_wait_time = 60
        wait_interval = 2
        waited_time = 0

        while waited_time < max_wait_time:
            time.sleep(wait_interval)
            waited_time += wait_interval

            # Ищем файл с оригинальным именем
            original_files = glob.glob(os.path.join(download_dir, "TradeWatch - raport konkurencji.xlsx"))

            if original_files:
                original_file = original_files[0]

                # Проверяем стабильность размера файла
                initial_size = os.path.getsize(original_file)
                time.sleep(3)

                try:
                    final_size = os.path.getsize(original_file)
                    if initial_size == final_size and final_size > 0:
                        print(f"✅ Файл загружен: {original_file} (размер: {final_size} байт)")

                        # Переименовываем файл в уникальное имя
                        try:
                            # Ждем дополнительно, чтобы файл был полностью освобожден
                            time.sleep(2)

                            # Проверяем, что файл все еще существует и доступен
                            if os.path.exists(original_file):
                                os.rename(original_file, expected_filepath)
                                print(f"✅ Файл переименован: {os.path.basename(original_file)} -> {os.path.basename(expected_filepath)}")
                                return expected_filepath
                            else:
                                print(f"⚠️  Файл исчез после скачивания: {original_file}")
                                return None
                        except Exception as rename_e:
                            print(f"❌ Ошибка при переименовании файла: {rename_e}")
                            # Пробуем еще раз через некоторое время
                            try:
                                time.sleep(5)
                                if os.path.exists(original_file):
                                    os.rename(original_file, expected_filepath)
                                    print(f"✅ Файл переименован (повторная попытка): {os.path.basename(original_file)} -> {os.path.basename(expected_filepath)}")
                                    return expected_filepath
                            except Exception as retry_e:
                                print(f"❌ Повторная попытка переименования тоже неудачна: {retry_e}")
                            return None
                    else:
                        print(f"⏳ Файл еще скачивается... (размер: {final_size} байт)")
                except:
                    print(f"⏳ Файл заблокирован, продолжаем ждать...")
                    continue
            else:
                # Дополнительная диагностика
                all_files_in_dir = os.listdir(download_dir) if os.path.exists(download_dir) else []
                tradewatch_files = [f for f in all_files_in_dir if 'tradewatch' in f.lower() or 'raport' in f.lower()]
                if tradewatch_files:
                    print(f"🔍 Найдены файлы TradeWatch в папке: {tradewatch_files}")
                else:
                    print(f"⏳ Ожидание файла... ({waited_time}/{max_wait_time} сек) | Файлов в папке: {len(all_files_in_dir)}")

        print(f"❌ Файл для группы {batch_number} не найден после {max_wait_time} секунд ожидания")
        return None

    except Exception as e:
        print(f"❌ Ошибка при обработке группы {batch_number} во вкладке: {e}")
        return None

    finally:
        # Закрываем вкладку после обработки
        if new_tab:
            try:
                print(f"🔒 Закрываем вкладку для группы {batch_number}")
                driver.switch_to.window(new_tab)
                driver.close()

                # Возвращаемся к основной вкладке
                driver.switch_to.window(original_window)
                print(f"✅ Вернулись к основной вкладке после группы {batch_number}")
            except Exception as e:
                print(f"⚠️  Ошибка при закрытии вкладки: {e}")


def process_batch_in_separate_browser_with_unique_name(ean_codes_batch, download_dir, batch_number, headless=None):
    """
    🚀 НОВАЯ ФУНКЦИЯ: Обрабатывает группу EAN кодов в ОТДЕЛЬНОМ БРАУЗЕРЕ с уникальным именем файла
    
    Args:
        ean_codes_batch: список EAN кодов для обработки
        download_dir: папка для скачивания файлов
        batch_number: номер группы для идентификации
        headless: запуск в headless режиме или None (использовать config)
        
    Returns:
        str: путь к скачанному файлу или None если ошибка
    """
    # Используем конфигурацию если headless не указан
    if headless is None:
        headless = config.HEADLESS_MODE
        
    if not ean_codes_batch:
        print(f"❌ Группа {batch_number} пустая")
        return None

    # Генерируем уникальное имя файла заранее
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # миллисекунды для уникальности
    unique_filename = f"TradeWatch_raport_konkurencji_batch_{batch_number}_{timestamp}.xlsx"
    expected_filepath = os.path.join(download_dir, unique_filename)
    
    print(f"🔥 БРАУЗЕР {batch_number}: Запуск отдельного браузера для группы {batch_number}")
    print(f"📄 Ожидаемое имя файла: {unique_filename}")

    # Настройка драйвера Chrome для ОТДЕЛЬНОГО браузера
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    if headless:
        options.add_argument("--headless")
    else:
        print(f"👁️  Браузер {batch_number}: HEADLESS РЕЖИМ ОТКЛЮЧЕН")

    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")

    # Отключаем кеширование
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI")

    # 🔥 КРИТИЧЕСКИ ВАЖНО: Создаем УНИКАЛЬНУЮ подпапку для каждого браузера
    browser_subfolder = f"browser_{batch_number}_{timestamp}"
    unique_download_path = Path(download_dir) / browser_subfolder
    unique_download_path.mkdir(parents=True, exist_ok=True)

    prefs = {
        "download.default_directory": str(unique_download_path.absolute()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    print(f"📁 Браузер {batch_number}: Уникальная папка для скачивания: {unique_download_path.absolute()}")

    # Создаем драйвер с помощью безопасной функции
    driver = create_chrome_driver_safely(headless=headless, download_dir=str(unique_download_path.absolute()))
    if not driver:
        print(f"❌ Браузер {batch_number}: Не удалось создать драйвер")
        return None

    try:
        print(f"🔐 Браузер {batch_number}: ЛОГИНИМСЯ В TRADEWATCH...")

        # Переход на страницу входа
        driver.get("https://tradewatch.pl/login.jsf")

        # Ждем загрузки страницы
        wait = WebDriverWait(driver, 15)

        # Ищем поле для email
        email_field = wait.until(EC.presence_of_element_located((By.NAME, "j_username")))

        # Вводим email
        email_field.clear()
        email_field.send_keys("emvertrends@gmail.com")

        # Ищем поле для пароля
        password_field = driver.find_element(By.NAME, "j_password")

        # Вводим пароль
        password_field.clear()
        password_field.send_keys("Trade-watch1")

        # Ищем кнопку входа
        login_button = driver.find_element(By.NAME, "btnLogin")

        # Нажимаем кнопку входа
        login_button.click()

        # Ждем немного после входа
        time.sleep(3)

        # Проверяем успешность входа
        current_url = driver.current_url

        if "login.jsf" in current_url:
            print(f"❌ Браузер {batch_number}: ОШИБКА входа в систему!")
            return None

        print(f"✅ Браузер {batch_number}: УСПЕШНЫЙ ВХОД В TRADEWATCH!")

        # Переходим на страницу EAN Price Report
        driver.get("https://tradewatch.pl/report/ean-price-report.jsf")
        time.sleep(3)

        # Ищем поле для ввода EAN кодов
        ean_field = wait.until(EC.presence_of_element_located((By.ID, "eansPhrase")))

        # 🔥 АГРЕССИВНАЯ ОЧИСТКА ПОЛЯ
        print(f"🧹 Браузер {batch_number}: АГРЕССИВНАЯ ОЧИСТКА поля EAN...")
        if not clear_ean_field_thoroughly(driver, ean_field, batch_number):
            print(f"❌ Браузер {batch_number}: Не удалось очистить поле EAN")
            return None

        # Форматируем EAN коды в 13-цифровой формат
        formatted_ean_codes = []
        for code in ean_codes_batch:
            formatted_code = format_ean_to_13_digits(code)
            if formatted_code:
                formatted_ean_codes.append(formatted_code)

        if not formatted_ean_codes:
            print(f"❌ Браузер {batch_number}: Нет валидных EAN кодов после форматирования")
            return None

        print(f"📝 Браузер {batch_number}: Отформатировано {len(formatted_ean_codes)} EAN кодов")

        # Соединяем отформатированные EAN коды в одну строку через пробел
        ean_codes_string = ' '.join(formatted_ean_codes)
        print(f"🔍 Браузер {batch_number}: EAN коды: {ean_codes_string[:100]}...")

        # Вставляем EAN коды
        ean_field.send_keys(ean_codes_string)

        # Проверяем, что вставились наши коды
        inserted_value = ean_field.get_attribute("value")
        inserted_codes = inserted_value.strip().split() if inserted_value else []
        expected_codes = ean_codes_string.strip().split()

        if len(inserted_codes) != len(expected_codes):
            print(f"⚠️ Браузер {batch_number}: Количество вставленных кодов ({len(inserted_codes)}) не совпадает с ожидаемым ({len(expected_codes)})")
            return None

        print(f"✅ Браузер {batch_number}: Вставлено {len(inserted_codes)} EAN кодов")

        # Ждем немного
        time.sleep(1)

        # Ищем кнопку "Generuj" надежным способом
        generate_button = find_generuj_button_safely(driver, wait)
        if not generate_button:
            print(f"❌ Браузер {batch_number}: Не удалось найти кнопку 'Generuj'")
            return None

        # Нажимаем кнопку
        generate_button.click()

        # Ждем обработки
        print(f"⏳ Браузер {batch_number}: Ждем обработки запроса...")
        time.sleep(5)

        # Ждем появления результатов
        print(f"⏳ Браузер {batch_number}: Ждем появления результатов...")
        time.sleep(3)

        # 🔥 ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА ЗАГРУЗКИ СТРАНИЦЫ
        try:
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            print(f"✅ Браузер {batch_number}: Страница полностью загружена")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Браузер {batch_number}: Ошибка при проверке загрузки страницы: {e}")

        # 🔥 ЖДЕМ ИСЧЕЗНОВЕНИЯ OVERLAY ПЕРЕД ЭКСПОРТОМ
        print(f"🛡️ Браузер {batch_number}: Ждем исчезновения overlay...")
        try:
            overlay_selectors = [
                ".ui-widget-overlay",
                ".ui-overlay", 
                "[class*='overlay']",
                ".modal-backdrop",
                ".loading-overlay",
                ".ui-blockui",
                ".blockUI"
            ]
            
            for selector in overlay_selectors:
                try:
                    wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, selector)) == 0 or 
                              (len(driver.find_elements(By.CSS_SELECTOR, selector)) > 0 and 
                               not driver.find_element(By.CSS_SELECTOR, selector).is_displayed()))
                    print(f"✅ Браузер {batch_number}: Overlay {selector} исчез")
                except:
                    pass
            
            time.sleep(2)
            
        except Exception as e:
            print(f"⚠️ Браузер {batch_number}: Ошибка при ожидании overlay: {e}")

        # Ищем кнопку "Eksport do XLS" с повторными попытками
        export_button = None
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                print(f"🔍 Браузер {batch_number}: Поиск кнопки экспорта (попытка {attempt + 1}/{max_attempts})")
                
                export_button = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Eksport do XLS")))
                
                if export_button.is_displayed() and export_button.is_enabled():
                    print(f"✅ Браузер {batch_number}: Кнопка экспорта найдена и готова к клику")
                    break
                else:
                    print(f"⚠️ Браузер {batch_number}: Кнопка найдена, но не кликабельна (попытка {attempt + 1})")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"⚠️ Браузер {batch_number}: Не удалось найти кнопку экспорта (попытка {attempt + 1}): {e}")
                time.sleep(2)
        
        if not export_button:
            print(f"❌ Браузер {batch_number}: Не удалось найти кнопку экспорта после {max_attempts} попыток")
            return None

        # 🔥 КЛИКАЕМ ПО КНОПКЕ ЭКСПОРТА
        print(f"🖱️ Браузер {batch_number}: Кликаем по кнопке экспорта")
        try:
            export_button.click()
            print(f"✅ Браузер {batch_number}: Обычный клик по кнопке экспорта успешен")
        except Exception as e:
            print(f"⚠️ Браузер {batch_number}: Обычный клик не удался: {e}")
            try:
                driver.execute_script("arguments[0].click();", export_button)
                print(f"✅ Браузер {batch_number}: JavaScript клик по кнопке экспорта успешен")
            except Exception as js_e:
                print(f"❌ Браузер {batch_number}: JavaScript клик тоже не удался: {js_e}")
                return None

        # 🔥 ЖДЕМ ЗАГРУЗКИ ФАЙЛА С ПЕРЕИМЕНОВАНИЕМ
        print(f"⏳ Браузер {batch_number}: Ждем загрузки файла...")
        max_wait_time = 60
        wait_interval = 2
        waited_time = 0

        while waited_time < max_wait_time:
            time.sleep(wait_interval)
            waited_time += wait_interval

            # Ищем файл с оригинальным именем в УНИКАЛЬНОЙ папке браузера
            original_files = glob.glob(os.path.join(unique_download_path, "TradeWatch - raport konkurencji.xlsx"))

            if original_files:
                original_file = original_files[0]

                # Проверяем стабильность размера файла
                initial_size = os.path.getsize(original_file)
                time.sleep(3)

                try:
                    final_size = os.path.getsize(original_file)
                    if initial_size == final_size and final_size > 0:
                        print(f"✅ Браузер {batch_number}: Файл загружен: {original_file} (размер: {final_size} байт)")

                        # Перемещаем файл из уникальной папки в основную папку с уникальным именем
                        try:
                            time.sleep(2)  # Ждем дополнительно
                            if os.path.exists(original_file):
                                # Создаем путь к итоговому файлу в основной папке
                                final_filepath = os.path.join(download_dir, unique_filename)
                                os.rename(original_file, final_filepath)
                                print(f"✅ Браузер {batch_number}: Файл перемещен: {os.path.basename(original_file)} -> {unique_filename}")
                                
                                # Удаляем временную папку браузера
                                try:
                                    unique_download_path.rmdir()
                                    print(f"🧹 Браузер {batch_number}: Временная папка удалена")
                                except:
                                    pass
                                
                                return final_filepath
                            else:
                                print(f"⚠️ Браузер {batch_number}: Файл исчез после скачивания")
                                return None
                        except Exception as rename_e:
                            print(f"❌ Браузер {batch_number}: Ошибка при перемещении файла: {rename_e}")
                            try:
                                time.sleep(5)
                                if os.path.exists(original_file):
                                    final_filepath = os.path.join(download_dir, unique_filename)
                                    os.rename(original_file, final_filepath)
                                    print(f"✅ Браузер {batch_number}: Файл перемещен (повторная попытка)")
                                    return final_filepath
                            except Exception as retry_e:
                                print(f"❌ Браузер {batch_number}: Повторная попытка перемещения неудачна: {retry_e}")
                            return None
                    else:
                        print(f"⏳ Браузер {batch_number}: Файл еще скачивается... (размер: {final_size} байт)")
                except:
                    print(f"⏳ Браузер {batch_number}: Файл заблокирован, продолжаем ждать...")
                    continue
            else:
                all_files_in_dir = os.listdir(unique_download_path) if os.path.exists(unique_download_path) else []
                print(f"⏳ Браузер {batch_number}: Ожидание файла... ({waited_time}/{max_wait_time} сек) | Файлов в уникальной папке: {len(all_files_in_dir)}")

        print(f"❌ Браузер {batch_number}: Файл не найден после {max_wait_time} секунд ожидания")
        return None

    except Exception as e:
        print(f"❌ Браузер {batch_number}: Ошибка при обработке: {e}")
        return None

    finally:
        # Закрываем браузер
        try:
            print(f"🔒 Закрываем браузер {batch_number}")
            driver.quit()
        except Exception as e:
            print(f"⚠️ Ошибка при закрытии браузера {batch_number}: {e}")
        
        # Очистка памяти после закрытия браузера
        try:
            import gc
            gc.collect()  # Принудительная сборка мусора
            print(f"🧹 Память очищена после закрытия браузера {batch_number}")
        except Exception as e:
            print(f"⚠️ Ошибка при очистке памяти для браузера {batch_number}: {e}")


def process_batches_independent(batches, download_dir, headless=None, max_parallel=None, progress_callback=None):
    """
    🚀 НЕЗАВИСИМАЯ ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА: Каждый браузер работает полностью автономно
    
    Все браузеры запускаются одновременно и работают независимо друг от друга.
    Никто не ждет завершения "напарника" - каждый браузер обрабатывает свою группу
    и завершается сразу после завершения своей задачи.
    
    Args:
        batches: список групп EAN кодов
        download_dir: папка для скачивания файлов
        headless: запуск в headless режиме
        max_parallel: максимальное количество одновременных браузеров
        progress_callback: функция для отслеживания прогресса
        
    Returns:
        list: список путей к скачанным файлам
    """
    # Используем значения из конфигурации, если параметры не переданы
    if headless is None:
        headless = config.HEADLESS_MODE
    if max_parallel is None:
        max_parallel = config.MAX_PARALLEL_BROWSERS
    
    print(f"🚀 ЗАПУСК НЕЗАВИСИМОЙ ПАРАЛЛЕЛЬНОЙ ОБРАБОТКИ: {len(batches)} групп, макс. {max_parallel} браузеров одновременно")
    print(f"⚡ Каждый браузер работает ПОЛНОСТЬЮ НЕЗАВИСИМО - никто не ждет других!")
    print(f"🔧 Настройки: headless={headless}, max_parallel={max_parallel}")
    
    downloaded_files = []
    processed_count = 0
    
    # Используем Semaphore для ограничения количества одновременных браузеров
    # но каждый браузер работает независимо
    semaphore = threading.Semaphore(max_parallel)
    
    def process_single_batch_independent(batch, batch_number):
        """Обрабатывает одну группу в независимом браузере"""
        nonlocal processed_count
        
        # Получаем разрешение на запуск браузера
        semaphore.acquire()
        try:
            print(f"🔥 НЕЗАВИСИМЫЙ БРАУЗЕР {batch_number}: Запуск автономной обработки группы {batch_number}")
            
            result = process_batch_in_separate_browser_with_unique_name(
                batch, download_dir, batch_number, headless
            )
            
            if result:
                downloaded_files.append(result)
                processed_count += len(batch)
                print(f"✅ НЕЗАВИСИМЫЙ БРАУЗЕР {batch_number}: Группа {batch_number} завершена автономно")
                
                # 💾 ЧЕКПОИНТ: Сохраняем прогресс каждые N групп
                if config.CHECKPOINT_SETTINGS['enabled'] and batch_number % config.CHECKPOINT_SETTINGS['save_interval'] == 0:
                    checkpoint_data = {
                        'supplier_file': getattr(config, 'current_supplier_file', 'unknown'),
                        'total_batches': len(batches),
                        'completed_batches': batch_number,
                        'processed_ean_count': processed_count,
                        'downloaded_files': downloaded_files,
                        'completed': False
                    }
                    save_processing_checkpoint(checkpoint_data, config.CHECKPOINT_SETTINGS['checkpoint_file'])
                
                # 🧹 ОЧИСТКА ПАМЯТИ для больших файлов
                if hasattr(config, 'LARGE_FILE_OPTIMIZATIONS') and batch_number % config.LARGE_FILE_OPTIMIZATIONS['memory_cleanup_interval'] == 0:
                    print(f"🧹 Очистка памяти после группы {batch_number}")
                    # Принудительная сборка мусора
                    import gc
                    gc.collect()
                
                # Обновляем прогресс
                if progress_callback:
                    try:
                        progress_callback(processed_count)
                    except Exception as e:
                        print(f"⚠️ Ошибка в progress_callback для группы {batch_number}: {e}")
                        
                return result
            else:
                print(f"❌ НЕЗАВИСИМЫЙ БРАУЗЕР {batch_number}: Ошибка при обработке группы {batch_number}")
                return None
                
        except Exception as e:
            print(f"❌ НЕЗАВИСИМЫЙ БРАУЗЕР {batch_number}: Исключение при обработке группы {batch_number}: {e}")
            return None
        finally:
            # Освобождаем разрешение для следующего браузера
            semaphore.release()
            print(f"🏁 НЕЗАВИСИМЫЙ БРАУЗЕР {batch_number}: Освободил слот для следующего браузера")
    
    # Запускаем все браузеры независимо с ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(batches)) as executor:
        # Создаем задачи для ВСЕХ групп сразу
        future_to_batch = {
            executor.submit(process_single_batch_independent, batch, i + 1): (i + 1, batch) 
            for i, batch in enumerate(batches)
        }
        
        print(f"🚀 ЗАПУЩЕНО {len(batches)} НЕЗАВИСИМЫХ БРАУЗЕРОВ")
        print(f"⏳ Браузеры будут завершаться по мере готовности (макс. {max_parallel} одновременно)")
        
        # Ожидаем завершения всех независимых браузеров
        for future in concurrent.futures.as_completed(future_to_batch):
            batch_number, batch = future_to_batch[future]
            try:
                result = future.result()
                if result:
                    print(f"🎉 БРАУЗЕР {batch_number} ЗАВЕРШЕН: Группа {batch_number} обработана независимо")
                else:
                    print(f"💥 БРАУЗЕР {batch_number} НЕУДАЧА: Группа {batch_number} не обработана")
                    
            except Exception as e:
                print(f"💥 БРАУЗЕР {batch_number} ИСКЛЮЧЕНИЕ: {e}")
    
    print(f"\n🏁 ВСЕ НЕЗАВИСИМЫЕ БРАУЗЕРЫ ЗАВЕРШЕНЫ")
    print(f"📊 Успешно обработано групп: {len([f for f in downloaded_files if f])} из {len(batches)}")
    
    # 💾 ФИНАЛЬНЫЙ ЧЕКПОИНТ: Сохраняем завершение обработки
    if config.CHECKPOINT_SETTINGS['enabled']:
        checkpoint_data = {
            'supplier_file': getattr(config, 'current_supplier_file', 'unknown'),
            'total_batches': len(batches),
            'completed_batches': len(batches),
            'processed_ean_count': processed_count,
            'downloaded_files': downloaded_files,
            'completed': True,
            'completion_time': datetime.now().isoformat()
        }
        save_processing_checkpoint(checkpoint_data, config.CHECKPOINT_SETTINGS['checkpoint_file'])
        print("🎉 ОБРАБОТКА ЗАВЕРШЕНА! Финальный чекпоинт сохранен.")
    
    return downloaded_files


def process_batches_parallel(batches, download_dir, headless=None, max_parallel=None, progress_callback=None):
    """
    🚀 ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА ПАЧКАМИ: Обрабатывает группы EAN кодов параллельно в отдельных браузерах
    
    Args:
        batches: список групп EAN кодов
        download_dir: папка для скачивания файлов
        headless: запуск в headless режиме
        max_parallel: максимальное количество параллельных браузеров (по умолчанию 2)
        progress_callback: функция для отслеживания прогресса
        
    Returns:
        list: список путей к скачанным файлам
    """
    # Используем значения из конфигурации, если параметры не переданы
    if headless is None:
        headless = config.HEADLESS_MODE
    if max_parallel is None:
        max_parallel = config.MAX_PARALLEL_BROWSERS
    
    print(f"🚀 ЗАПУСК ПАРАЛЛЕЛЬНОЙ ОБРАБОТКИ ПАЧКАМИ: {len(batches)} групп, макс. {max_parallel} браузеров")
    print(f"🔧 Настройки: headless={headless}, max_parallel={max_parallel}")
    
    downloaded_files = []
    processed_count = 0
    consecutive_failures = 0  # Счетчик последовательных неудач
    current_max_parallel = max_parallel  # Текущее максимальное количество браузеров
    
    # Обрабатываем группы пачками по max_parallel
    for i in range(0, len(batches), current_max_parallel):
        current_batch_group = batches[i:i + current_max_parallel]
        
        print(f"\n🔄 ОБРАБАТЫВАЕМ ПАЧКУ {i//current_max_parallel + 1}: группы {i+1}-{i+len(current_batch_group)} из {len(batches)} (макс. {current_max_parallel} браузеров)")
        
        # Запускаем параллельную обработку для текущей пачки
        with concurrent.futures.ThreadPoolExecutor(max_workers=current_max_parallel) as executor:
            # Создаем задачи для каждой группы в пачке
            future_to_batch = {}
            batch_failures = 0  # Неудачи в текущей пачке
            
            for j, batch in enumerate(current_batch_group):
                batch_number = i + j + 1
                
                # Проверяем ресурсы перед запуском браузера
                resources_ok, recommended = check_system_resources()
                if not resources_ok:
                    print(f"⏳ Ждем освобождения ресурсов перед запуском браузера {batch_number}...")
                    time.sleep(5)
                    # Повторная проверка
                    resources_ok, recommended = check_system_resources()
                    if not resources_ok:
                        print(f"⚠️ Ресурсы все еще недоступны, пропускаем браузер {batch_number}")
                        continue
                
                # Добавляем задержку между запусками браузеров для предотвращения перегрузки
                if j > 0:
                    delay = config.RESOURCE_MANAGEMENT.get('browser_start_delay', 2)
                    time.sleep(delay)
                
                future = executor.submit(
                    process_batch_in_separate_browser_with_unique_name,
                    batch,
                    download_dir,
                    batch_number,  # номер группы
                    headless
                )
                future_to_batch[future] = (batch_number, batch)
            
            # Ожидаем завершения всех задач в пачке
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_number, batch = future_to_batch[future]
                try:
                    result = future.result()
                    if result:
                        downloaded_files.append(result)
                        processed_count += len(batch)
                        print(f"✅ Группа {batch_number} обработана успешно в отдельном браузере")
                        
                        # Обновляем прогресс
                        if progress_callback:
                            try:
                                progress_callback(processed_count)
                            except Exception as e:
                                print(f"⚠️ Ошибка в progress_callback: {e}")
                    else:
                        print(f"❌ Ошибка при обработке группы {batch_number} в отдельном браузере")
                        
                except Exception as e:
                    error_message = str(e).lower()
                    
                    # Определяем тип ошибки для улучшения обработки
                    if any(keyword in error_message for keyword in ['connection', 'timeout', 'network', 'unreachable', 'refused', 'disconnected']):
                        print(f"🌐 Сетевая ошибка при обработке группы {batch_number} (браузер не перезапускается): {e}")
                        # При сетевых ошибках ждем дольше перед следующей попыткой
                        time.sleep(10)
                    elif any(keyword in error_message for keyword in ['webdriver', 'chrome', 'browser', 'driver']):
                        print(f"🔧 Ошибка браузера при обработке группы {batch_number}: {e}")
                        # При ошибках браузера тоже ждем
                        time.sleep(5)
                    else:
                        print(f"❌ Неизвестная ошибка при обработке группы {batch_number}: {e}")
                        # Для других ошибок тоже ждем
                        time.sleep(3)
        
        print(f"🏁 Пачка {i//current_max_parallel + 1} завершена. Обработано групп: {len([f for f in downloaded_files if f])}")
    
    return downloaded_files


def process_supplier_file_with_tradewatch_single_browser(supplier_file_path, download_dir, headless=None, progress_callback=None):
    """
    🔥 НОВАЯ ВЕРСИЯ: Обрабатывает файл поставщика в ОДНОМ БРАУЗЕРЕ с ВКЛАДКАМИ
    Одна сессия браузера, каждая группа в новой вкладке, агрессивная очистка поля

    Args:
        supplier_file_path: путь к файлу поставщика
        download_dir: папка для скачивания файлов TradeWatch
        headless: запуск в headless режиме (False для наблюдения)
        progress_callback: функция для отслеживания прогресса

    Returns:
        list: список путей к скачанным файлам TradeWatch
    """
    # Используем значения из конфигурации, если параметры не переданы
    if headless is None:
        headless = config.HEADLESS_MODE
    
    print(f"🔧 Настройки: headless={headless}")
    
    driver = None

    try:
        # Читаем файл поставщика
        print(f"📖 Читаем файл поставщика: {supplier_file_path}")
        df = pd.read_excel(supplier_file_path)

        # Проверяем наличие необходимых колонок
        if 'GTIN' not in df.columns:
            print("❌ Ошибка: В файле поставщика нет колонки GTIN")
            return []

        if 'Price' not in df.columns:
            print("❌ Ошибка: В файле поставщика нет колонки Price")
            return []

        # Извлекаем EAN коды
        ean_codes = df['GTIN'].dropna().astype(str).tolist()
        # Удаляем пустые и некорректные коды
        ean_codes = [code.strip() for code in ean_codes if code.strip() and code.strip() != 'nan']

        print(f"🔢 Найдено {len(ean_codes)} EAN кодов в файле поставщика")

        if not ean_codes:
            print("❌ Нет EAN кодов для обработки")
            return []

        # Разбиваем на группы по размеру из конфигурации
        batch_size = config.BATCH_SIZE
        batches = [ean_codes[i:i + batch_size] for i in range(0, len(ean_codes), batch_size)]

        print(f"📦 Разбиваем на {len(batches)} групп по {batch_size} кодов")

        # Создаем папку для скачивания если её нет
        download_path = Path(download_dir)
        download_path.mkdir(parents=True, exist_ok=True)

        # Очищаем все старые файлы TradeWatch перед началом обработки
        print("🧹 Очищаем старые файлы TradeWatch...")
        old_files_patterns = [
            "TradeWatch - raport konkurencji*.xlsx",
            "TradeWatch_raport_konkurencji_*.xlsx"
        ]

        for pattern in old_files_patterns:
            old_files = glob.glob(os.path.join(download_dir, pattern))
            for old_file in old_files:
                try:
                    os.remove(old_file)
                    print(f"🗑️ Удален старый файл: {old_file}")
                except Exception as e:
                    print(f"⚠️  Не удалось удалить файл {old_file}: {e}")
                    pass

        # 🔥 ВЫБИРАЕМ РЕЖИМ ОБРАБОТКИ: НЕЗАВИСИМЫЕ БРАУЗЕРЫ, ПАРАЛЛЕЛЬНЫЕ ПАЧКИ ИЛИ ПОСЛЕДОВАТЕЛЬНЫЙ
        if len(batches) >= 2:
            # 🚀 НОВЫЙ РЕЖИМ: ПОЛНОСТЬЮ НЕЗАВИСИМЫЕ БРАУЗЕРЫ
            print("🚀 ИСПОЛЬЗУЕМ НЕЗАВИСИМУЮ ПАРАЛЛЕЛЬНУЮ ОБРАБОТКУ (каждый браузер автономен)")
            downloaded_files = process_batches_independent(
                batches, 
                download_dir, 
                headless, 
                max_parallel=config.MAX_PARALLEL_BROWSERS, 
                progress_callback=progress_callback
            )
            
            # 📊 АЛЬТЕРНАТИВНЫЙ РЕЖИМ: ПАРАЛЛЕЛЬНЫЕ ПАЧКИ (закомментирован)
            # print("🚀 ИСПОЛЬЗУЕМ ПАРАЛЛЕЛЬНУЮ ОБРАБОТКУ ПАЧКАМИ (config.MAX_PARALLEL_BROWSERS браузеров одновременно)")
            # downloaded_files = process_batches_parallel(
            #     batches, 
            #     download_dir, 
            #     headless, 
            #     max_parallel=config.MAX_PARALLEL_BROWSERS, 
            #     progress_callback=progress_callback
            # )
        else:
            print("🔄 ИСПОЛЬЗУЕМ ПОСЛЕДОВАТЕЛЬНУЮ ОБРАБОТКУ (1 группа)")
            # Для одной группы используем старый метод с одним браузером
            driver = initialize_browser_and_login(headless, download_dir)

            if not driver:
                print("❌ Не удалось инициализировать браузер")
                return []

            downloaded_files = []
            processed_count = 0

            for i, batch in enumerate(batches, 1):
                print(f"\n📑 ОБРАБАТЫВАЕМ ГРУППУ {i}/{len(batches)} В НОВОЙ ВКЛАДКЕ")

                # Обрабатываем группу в новой вкладке
                result = process_batch_in_tab(driver, batch, download_dir, i)

                if result:
                    downloaded_files.append(result)
                    processed_count += len(batch)
                    print(f"✅ Группа {i} обработана успешно во вкладке")

                    # Обновляем прогресс через callback
                    if progress_callback:
                        try:
                            progress_callback(processed_count)
                        except Exception as e:
                            print(f"⚠️  Ошибка в progress_callback: {e}")
                else:
                    print(f"❌ Ошибка при обработке группы {i} во вкладке")
                    
            # Закрываем браузер после всех групп
            if driver:
                print("🔒 ЗАКРЫВАЕМ БРАУЗЕР ПОСЛЕ ВСЕХ ГРУПП")
                driver.quit()
                
                # 🔥 ПРИНУДИТЕЛЬНАЯ ОЧИСТКА ПРОЦЕССОВ ПОСЛЕ ЗАКРЫТИЯ БРАУЗЕРА
                print("🧹 ПРИНУДИТЕЛЬНАЯ ОЧИСТКА ПРОЦЕССОВ ПОСЛЕ ЗАКРЫТИЯ БРАУЗЕРА...")
                try:
                    # Убиваем все висячие процессы этого браузера
                    subprocess.run(["pkill", "-9", "-f", "chrome"], capture_output=True, check=False)
                    subprocess.run(["pkill", "-9", "-f", "chromedriver"], capture_output=True, check=False)
                    
                    # Ждем завершения процессов
                    time.sleep(1)
                    
                    print("✅ Очистка процессов после закрытия браузера выполнена")
                except Exception as cleanup_error:
                    print(f"⚠️  Ошибка очистки после закрытия браузера: {cleanup_error}")

        print(f"\n🏁 Обработка завершена. Загружено {len(downloaded_files)} файлов из {len(batches)} групп")

        # Проверяем, что все файлы существуют
        print("🔍 Проверка существования файлов:")
        existing_files = []
        for i, file_path in enumerate(downloaded_files):
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {file_path} (размер: {size} байт)")
                existing_files.append(file_path)
            else:
                print(f"  ❌ {file_path} - НЕ НАЙДЕН!")

        # Проверяем уникальность содержимого
        if existing_files:
            verify_batch_uniqueness(existing_files)

        return downloaded_files

    except Exception as e:
        print(f"❌ Ошибка при обработке файла поставщика: {e}")
        return []

    finally:
        # Очистка выполняется в соответствующих режимах обработки
        pass
