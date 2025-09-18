#!/bin/bash
# Создание нового токена бота для Railway

echo "🤖 СОЗДАНИЕ НОВОГО ТОКЕНА БОТА"
echo "=============================="
echo ""

echo "📋 СИТУАЦИЯ:"
echo "Конфликт getUpdates - две копии бота с одним токеном"
echo ""

echo "✅ РЕШЕНИЕ:"
echo "Создать нового бота для Railway версии"
echo ""

echo "🔧 ШАГИ:"
echo "1. Откройте Telegram"
echo "2. Найдите @BotFather"
echo "3. Отправьте команду: /newbot"
echo "4. Придумайте имя для нового бота"
echo "5. Придумайте username для нового бота (должен заканчиваться на 'bot')"
echo "6. BotFather пришлет вам новый токен"
echo ""

echo "📝 ПРИМЕР ДИАЛОГА С BOTFATHER:"
echo "Вы: /newbot"
echo "BotFather: Alright, a new bot. How are we going to call it?"
echo "Вы: Alegro Railway Bot"
echo "BotFather: Good. Now let's choose a username for your bot."
echo "Вы: alegro_railway_bot"
echo "BotFather: Done! Congratulations on your new bot."
echo "BotFather: You will find it at t.me/alegro_railway_bot"
echo "BotFather: Use this token to access the HTTP API:"
echo "BotFather: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
echo ""

echo "🌐 НАСТРОЙКА RAILWAY:"
echo "1. Скопируйте новый токен от BotFather"
echo "2. Зайдите в Railway dashboard"
echo "3. Найдите проект 'alegro'"
echo "4. Перейдите в Variables"
echo "5. Измените BOT_TOKEN на новый токен"
echo "6. Railway автоматически пересоберет проект"
echo ""

echo "🎯 РЕЗУЛЬТАТ:"
echo "• Локальная версия бота продолжит работать со старым токеном"
echo "• Railway версия будет работать с новым токеном"
echo "• Конфликт разрешен!"
echo ""

echo "⚠️  ВАЖНО:"
echo "• Не делитесь токеном с другими"
echo "• Токен дает полный доступ к боту"
echo "• При компрометации токена создайте нового бота"
echo ""

read -p "После создания нового бота нажмите Enter..."

echo ""
echo "✅ ГОТОВО!"
echo "Теперь добавьте новый токен в Railway Variables"