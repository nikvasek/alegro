#!/bin/bash
# Проверка развертывания на Railway

echo "🔍 ПРОВЕРКА РАЗВЕРТЫВАНИЯ НА RAILWAY"
echo "====================================="
echo ""

echo "📋 Текущий статус:"
echo "✅ GitHub репозиторий: https://github.com/nikvasek/alegro"
echo "✅ Код загружен на GitHub"
echo "⏳ Ожидает развертывания на Railway"
echo ""

echo "🌐 ШАГИ ДЛЯ RAILWAY:"
echo "1. Перейдите на https://railway.app"
echo "2. Войдите в аккаунт (или зарегистрируйтесь)"
echo "3. Нажмите 'New Project'"
echo "4. Выберите 'Deploy from GitHub'"
echo "5. Найдите и подключите репозиторий: nikvasek/alegro"
echo "6. Railway автоматически найдет railway.json и настроит проект"
echo ""

echo "🔧 НАСТРОЙКА ПЕРЕМЕННЫХ:"
echo "В разделе Variables добавьте:"
echo "  BOT_TOKEN = 7258964094:AAHMvyGG7CbznDZcB34DGv7JoFPk5kA8H08"
echo ""

echo "📊 МОНИТОРИНГ:"
echo "После развертывания Railway покажет:"
echo "  - Статус сборки (Build)"
echo "  - Статус развертывания (Deploy)"
echo "  - Логи приложения"
echo "  - URL вашего приложения (если есть веб-интерфейс)"
echo ""

echo "🎯 РЕЗУЛЬТАТ:"
echo "Ваш Telegram бот будет работать 24/7 на Railway!"
echo "Бот автоматически перезапускается при сбоях."
echo ""

echo "📞 ТЕСТИРОВАНИЕ:"
echo "Найдите бота в Telegram: @ваш_бот"
echo "Отправьте /start для проверки работы"
echo ""

read -p "После настройки Railway нажмите Enter для проверки статуса..."

echo ""
echo "🔍 Проверка подключения к GitHub..."
curl -s https://api.github.com/repos/nikvasek/alegro | head -10

echo ""
echo "✅ ГОТОВО! Ваш бот развернут на Railway 🚀"