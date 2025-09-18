#!/bin/bash
# Проверка всех скриптов для Railway

echo "📋 ОБЗОР ВСЕХ СКРИПТОВ ДЛЯ RAILWAY"
echo "=================================="
echo ""

echo "🚀 СКРИПТЫ РАЗВЕРТЫВАНИЯ:"
echo "• deploy.sh - быстрое развертывание"
echo "• create_github_repo.sh - создание репозитория через API"
echo "• setup_github_railway.sh - пошаговая настройка"
echo ""

echo "🔧 СКРИПТЫ ДИАГНОСТИКИ:"
echo "• chrome_diagnostic.sh - диагностика Chrome проблем"
echo "• dockerfile_fix.sh - объяснение перехода на Dockerfile"
echo "• firefox_fallback.sh - альтернатива с Firefox"
echo ""

echo "✅ СКРИПТЫ ПРОВЕРКИ:"
echo "• final_check.sh - финальная проверка готовности"
echo "• status_check.sh - проверка статуса развертывания"
echo "• check_railway.sh - общая информация о Railway"
echo "• test_healthcheck.sh - тестирование healthcheck"
echo ""

echo "🤖 СКРИПТЫ БОТОВ:"
echo "• create_new_bot.sh - создание нового токена"
echo "• setup_webhook.sh - настройка webhook"
echo ""

echo "📊 ТЕКУЩИЙ СТАТУС:"
echo "✅ GitHub репозиторий: https://github.com/nikvasek/alegro"
echo "✅ Код загружен и обновлен"
echo "✅ Переключились на Dockerfile"
echo "⏳ Railway пересобирает проект..."
echo ""

echo "🎯 СЛЕДУЮЩИЕ ШАГИ:"
echo "1. Подождите завершения пересборки (3-5 мин)"
echo "2. Запустите: ./final_check.sh"
echo "3. Попробуйте загрузить файл в бота"
echo "4. При проблемах: ./chrome_diagnostic.sh"
echo ""

echo "🔍 МОНИТОРИНГ:"
echo "• Railway dashboard покажет статус сборки"
echo "• Логи покажут установку Chrome"
echo "• Healthcheck проверит готовность"
echo ""

read -p "Нажмите Enter для выхода..."

echo ""
echo "🎉 ВСЕ ГОТОВО ДЛЯ ТЕСТИРОВАНИЯ!"