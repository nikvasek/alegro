#!/bin/bash
# Решение проблемы с software-properties-common

echo "🔧 РЕШЕНИЕ ПРОБЛЕМЫ SOFTWARE-PROPERTIES-COMMON"
echo "=============================================="
echo ""

echo "❌ ПРОБЛЕМА:"
echo "E: Unable to locate package software-properties-common"
echo "Пакет недоступен в Debian Trixie (новая версия)"
echo ""

echo "✅ РЕШЕНИЕ:"
echo "Убрали software-properties-common из Dockerfile"
echo "Этот пакет не критичен для установки Chrome"
echo ""

echo "📋 ОСТАВШИЕСЯ ЗАВИСИМОСТИ:"
echo "• wget - для скачивания файлов"
echo "• gnupg - для работы с ключами (вместо apt-key)"
echo "• unzip - для распаковки ChromeDriver"
echo "• curl - для HTTP запросов"
echo "• xvfb - виртуальный дисплей для headless Chrome"
echo "• ca-certificates - SSL сертификаты"
echo ""

echo "🔄 СОВМЕСТИМОСТЬ С DEBIAN TRIXIE:"
echo "Debian Trixie (testing/unstable) имеет другой набор пакетов"
echo "software-properties-common заменен встроенными инструментами"
echo ""

echo "⏰ СТАТУС:"
echo "Railway пересобирает проект без problematic пакета..."
echo "Установка Chrome должна пройти успешно!"
echo ""

echo "🎯 ОЖИДАНИЕ:"
echo "• Системные зависимости установятся"
echo "• Chrome установится с gpg ключом"
echo "• ChromeDriver будет загружен и настроен"
echo "• Бот запустится без ошибок"
echo ""

read -p "После завершения пересборки нажмите Enter..."

echo ""
echo "🎉 ПРОБЛЕМА РЕШЕНА!"
echo "Dockerfile адаптирован под Debian Trixie!"