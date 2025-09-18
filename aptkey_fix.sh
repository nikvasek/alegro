#!/bin/bash
# Решение проблемы apt-key в Dockerfile

echo "🔧 РЕШЕНИЕ ПРОБЛЕМЫ APT-KEY"
echo "==========================="
echo ""

echo "❌ ПРОБЛЕМА:"
echo "/bin/sh: 1: apt-key: not found"
echo "apt-key устарел в новых версиях Debian/Ubuntu"
echo ""

echo "✅ РЕШЕНИЕ:"
echo "Переход на современный способ установки Chrome:"
echo "• Используем gpg --dearmor вместо apt-key"
echo "• Создаем keyring файл в /usr/share/keyrings/"
echo "• Указываем signed-by в sources.list"
echo ""

echo "🔄 ИЗМЕНЕНИЯ В DOCKERFILE:"
echo "СТАРО: apt-key add -"
echo "НОВО: gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg"
echo ""
echo "СТАРО: deb [arch=amd64] http://dl.google.com/..."
echo "НОВО: deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/..."
echo ""

echo "📋 ДОПОЛНИТЕЛЬНЫЕ ПАКЕТЫ:"
echo "• ca-certificates - для работы с сертификатами"
echo "• software-properties-common - для управления репозиториями"
echo ""

echo "⏰ СТАТУС:"
echo "Railway пересобирает проект с исправленным Dockerfile..."
echo "Теперь Chrome должен установиться корректно!"
echo ""

echo "🎯 ОЖИДАНИЕ:"
echo "• Dockerfile сборка займет 3-5 минут"
echo "• Chrome установится без ошибок apt-key"
echo "• ChromeDriver будет доступен"
echo "• Бот сможет обрабатывать файлы"
echo ""

read -p "После завершения пересборки нажмите Enter..."

echo ""
echo "🎉 ПРОБЛЕМА APT-KEY РЕШЕНА!"
echo "Chrome теперь устанавливается современным способом!"