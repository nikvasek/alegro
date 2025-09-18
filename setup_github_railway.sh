#!/bin/bash
# Скрипт для настройки GitHub и Railway после создания репозитория

echo "🚀 Настройка GitHub и Railway для проекта Telegram Bot"
echo "=================================================="
echo ""
echo "📋 ШАГ 1: Создайте репозиторий на GitHub"
echo "------------------------------------------"
echo "1. Перейдите на https://github.com/new"
echo "2. Название репозитория: alegro-telegram-bot"
echo "3. Сделайте репозиторий публичным"
echo "4. НЕ добавляйте README, .gitignore или лицензию"
echo "5. Нажмите 'Create repository'"
echo ""
echo "После создания репозитория нажмите Enter для продолжения..."
read -p ""

# Запрашиваем информацию о репозитории
read -p "Введите ваш GitHub username: " GITHUB_USERNAME
read -p "Введите название репозитория (alegro-telegram-bot): " REPO_NAME

if [ -z "$REPO_NAME" ]; then
    REPO_NAME="alegro-telegram-bot"
fi

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
echo "🌐 ШАГ 2: Настройка Railway"
echo "---------------------------"
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
echo "🔗 URL Railway проекта: https://railway.app (после создания)"
echo ""
echo "🎉 Готово! Ваш бот будет работать 24/7!"