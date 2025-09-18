#!/bin/bash
# Настройка webhook для Railway

echo "🔧 НАСТРОЙКА WEBHOOK ДЛЯ RAILWAY"
echo "================================="
echo ""

echo "📋 ПРОБЛЕМА:"
echo "Конфликт getUpdates - две копии бота работают одновременно"
echo ""

echo "✅ РЕШЕНИЕ:"
echo "Настроить webhook вместо polling для Railway версии"
echo ""

echo "🌐 ШАГИ НАСТРОЙКИ:"
echo "1. Получите публичный URL вашего Railway проекта"
echo "   • Зайдите в Railway dashboard"
echo "   • Найдите ваш проект 'alegro'"
echo "   • Скопируйте URL (например: https://alegro-production.up.railway.app)"
echo ""

echo "2. Добавьте переменные окружения в Railway:"
echo "   USE_WEBHOOK=true"
echo "   WEBHOOK_URL=https://alegro-production.up.railway.app"
echo "   WEBHOOK_PORT=8443"
echo ""

echo "3. Или создайте новый токен для Railway версии:"
echo "   • Зайдите на https://t.me/BotFather"
echo "   • Создайте нового бота командой /newbot"
echo "   • Добавьте новый BOT_TOKEN в Railway variables"
echo ""

echo "📞 ТЕСТИРОВАНИЕ:"
echo "После настройки webhook обе версии бота смогут работать одновременно"
echo ""

read -p "Введите URL вашего Railway проекта (или нажмите Enter для пропуска): " RAILWAY_URL

if [ ! -z "$RAILWAY_URL" ]; then
    echo ""
    echo "🔧 Добавьте эти переменные в Railway Variables:"
    echo "USE_WEBHOOK=true"
    echo "WEBHOOK_URL=$RAILWAY_URL"
    echo "WEBHOOK_PORT=8443"
    echo ""
    echo "📋 Полная команда для Railway:"
    echo "curl -X POST \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"USE_WEBHOOK\": \"true\", \"WEBHOOK_URL\": \"$RAILWAY_URL\", \"WEBHOOK_PORT\": \"8443\"}' \\"
    echo "  https://railway.app/api/project/YOUR_PROJECT_ID/variables"
    echo ""
fi

echo "🎯 РЕЗУЛЬТАТ:"
echo "После настройки webhook конфликт будет разрешен!"
echo ""

read -p "Нажмите Enter для выхода..."