#!/usr/bin/env python3
"""
Автоматическая установка зависимостей для Telegram Bot
Этот скрипт автоматически устанавливает все необходимые пакеты
"""

import subprocess
import sys
import os
import platform

def install_package(package):
    """Устанавливает пакет через pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_python_version():
    """Проверяет версию Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Требуется Python 3.7 или выше")
        print(f"Текущая версия: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python версия: {version.major}.{version.minor}.{version.micro}")
    return True

def install_chrome_driver():
    """Устанавливает Chrome Driver для Selenium"""
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        ChromeDriverManager().install()
        print("✅ Chrome Driver установлен")
        return True
    except Exception as e:
        print(f"❌ Ошибка установки Chrome Driver: {e}")
        return False

def main():
    """Основная функция установки"""
    print("🚀 Установка зависимостей для Telegram Bot...")
    print("=" * 50)
    
    # Проверяем версию Python
    if not check_python_version():
        input("Нажмите Enter для выхода...")
        return
    
    # Обновляем pip
    print("\n📦 Обновляем pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Читаем requirements.txt
    requirements_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    
    if not os.path.exists(requirements_file):
        print("❌ Файл requirements.txt не найден")
        input("Нажмите Enter для выхода...")
        return
    
    with open(requirements_file, 'r') as f:
        packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Устанавливаем пакеты
    print(f"\n📋 Устанавливаем {len(packages)} пакетов...")
    failed_packages = []
    
    for package in packages:
        print(f"Устанавливаем {package}...")
        if not install_package(package):
            failed_packages.append(package)
    
    # Проверяем результаты
    if failed_packages:
        print(f"\n❌ Не удалось установить: {', '.join(failed_packages)}")
        print("Попробуйте установить их вручную:")
        for package in failed_packages:
            print(f"  pip install {package}")
    else:
        print("\n✅ Все пакеты успешно установлены!")
    
    # Устанавливаем Chrome Driver
    print("\n🌐 Устанавливаем Chrome Driver...")
    install_chrome_driver()
    
    # Проверяем токен бота
    print("\n🔑 Проверяем конфигурацию...")
    config_file = os.path.join(os.path.dirname(__file__), "config.py")
    if os.path.exists(config_file):
        print("✅ Файл config.py найден")
    else:
        print("❌ Файл config.py не найден")
    
    print("\n🎉 Установка завершена!")
    print("Для запуска бота используйте:")
    print("  python run_bot.py")
    print("или запустите start.bat (Windows) / start.sh (Mac/Linux)")
    
    input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()
