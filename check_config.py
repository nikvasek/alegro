#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка конфигурации браузеров
"""

import config

def check_config():
    """Проверяет текущие настройки конфигурации"""
    print("🔧 ПРОВЕРКА НАСТРОЕК КОНФИГУРАЦИИ")
    print("=" * 50)
    print(f"📊 Максимальное количество браузеров: {config.MAX_PARALLEL_BROWSERS}")
    print(f"🔧 Режим headless: {config.HEADLESS_MODE}")
    print(f"📦 Размер группы EAN: {config.BATCH_SIZE}")
    print("=" * 50)
    
    # Проверим настройки таймаутов
    print("⏱️  ТАЙМАУТЫ:")
    for key, value in config.BROWSER_TIMEOUTS.items():
        print(f"  ├─ {key}: {value} сек")
    
    print("\n🔄 ПОВТОРНЫЕ ПОПЫТКИ:")
    for key, value in config.RETRY_SETTINGS.items():
        print(f"  ├─ {key}: {value}")

if __name__ == "__main__":
    check_config()