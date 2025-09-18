#!/bin/bash
# Быстрое развертывание Telegram бота на Railway

echo "🚀 БЫСТРОЕ РАЗВЕРТЫВАНИЕ TELEGRAM БОТА"
echo "======================================"
echo ""

# Проверяем наличие Git
if ! command -v git &> /dev/null; then
    echo "❌ Git не установлен. Установите Git и попробуйте снова."
    exit 1
fi

echo "✅ Git найден"

# Проверяем статус Git
if [ ! -d ".git" ]; then
    echo "❌ Это не Git репозиторий. Инициализируйте Git сначала."
    exit 1
fi

echo "✅ Git репозиторий найден"

# Проверяем наличие необходимых файлов
required_files=("requirements.txt" "run_bot.py" "railway.json")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Файл $file не найден"
        exit 1
    fi
done

echo "✅ Все необходимые файлы найдены"

# Проверяем, есть ли незакоммиченные изменения
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "⚠️  Есть незакоммиченные изменения. Коммитим..."
    git add .
    git commit -m "Auto-commit before deployment"
    echo "✅ Изменения закоммичены"
fi

echo ""
echo "📋 ДАЛЕЕ:"
echo "1. Создайте репозиторий на GitHub (github.com/new)"
echo "2. Назовите его 'alegro-telegram-bot'"
echo "3. Сделайте публичным"
echo "4. НЕ добавляйте README/gitignore"
echo ""
read -p "После создания репозитория нажмите Enter..."

echo ""
echo "🔧 Запуск скрипта настройки..."
./setup_github_railway.sh

echo ""
echo "🎉 ГОТОВО!"
echo "Теперь перейдите на railway.app и подключите ваш репозиторий!"