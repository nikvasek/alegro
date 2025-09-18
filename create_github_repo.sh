#!/bin/bash
# Скрипт для создания GitHub репозитория через API

echo "🔧 Создание GitHub репозитория через API"
echo "=========================================="

# Запрашиваем GitHub токен
echo "Для создания репозитория нужен GitHub Personal Access Token:"
echo "1. Перейдите на https://github.com/settings/tokens"
echo "2. Создайте новый токен с правами 'repo'"
echo "3. Скопируйте токен"
echo ""

read -p "Введите ваш GitHub Personal Access Token: " GITHUB_TOKEN
read -p "Введите ваш GitHub username: " GITHUB_USERNAME
read -p "Введите название репозитория (alegro-telegram-bot): " REPO_NAME

if [ -z "$REPO_NAME" ]; then
    REPO_NAME="alegro-telegram-bot"
fi

echo ""
echo "📡 Создание репозитория..."

# Создаем репозиторий через GitHub API
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO_NAME\", \"public\":true, \"description\":\"Telegram bot for Excel processing with TradeWatch integration\"}"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Репозиторий создан успешно!"
    echo "🔗 URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
    echo ""
    echo "🔧 Настройка Git remote..."
    git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git

    echo "📤 Push кода..."
    git branch -M main
    git push -u origin main

    echo ""
    echo "🎉 Готово! Теперь настройте Railway:"
    echo "1. Перейдите на https://railway.app"
    echo "2. Создайте проект → Deploy from GitHub"
    echo "3. Подключите репозиторий: $GITHUB_USERNAME/$REPO_NAME"
    echo "4. Добавьте BOT_TOKEN: 7258964094:AAHMvyGG7CbznDZcB34DGv7JoFPk5kA8H08"
else
    echo ""
    echo "❌ Ошибка создания репозитория"
    echo "Проверьте токен и попробуйте снова"
fi