#!/bin/bash
# Скрипт для настройки GitHub и Railway после создания репозитория

echo "🚀 Настройка GitHub и Railway для проекта Telegram Bot"
echo "=================================================="

# Запрашиваем информацию о репозитории
read -p "Введите ваш GitHub username: " GITHUB_USERNAME
read -p "Введите название репозитория: " REPO_NAME

echo ""
echo "🔧 Настройка Git remote..."
git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git

echo ""
echo "📤 Push кода на GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "✅ Код успешно загружен на GitHub!"
echo ""
echo "🌐 Теперь настройте Railway:"
echo "1. Перейдите на https://railway.app"
echo "2. Создайте новый проект"
echo "3. Выберите 'Deploy from GitHub'"
echo "4. Подключите ваш репозиторий: $GITHUB_USERNAME/$REPO_NAME"
echo "5. Добавьте переменную окружения:"
echo "   Name: BOT_TOKEN"
echo "   Value: 7258964094:AAHMvyGG7CbznDZcB34DGv7JoFPk5kA8H08"
echo "6. Railway автоматически развернет ваш бот!"
echo ""
echo "📋 URL вашего репозитория: https://github.com/$GITHUB_USERNAME/$REPO_NAME"