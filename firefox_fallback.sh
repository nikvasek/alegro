#!/bin/bash
# Альтернативная настройка с Firefox для Railway

echo "🦊 АЛЬТЕРНАТИВНАЯ НАСТРОЙКА С FIREFOX"
echo "====================================="
echo ""

echo "📋 СИТУАЦИЯ:"
echo "Если Chrome не работает в Railway, можно использовать Firefox"
echo ""

echo "🔧 НАСТРОЙКА FIREFOX:"
echo "1. Обновить nixpacks.toml для Firefox"
echo "2. Изменить tradewatch_login.py для использования Firefox"
echo "3. Добавить переменные окружения"
echo ""

echo "📝 ИЗМЕНЕНИЯ В nixpacks.toml:"
echo '[phases.setup]'
echo 'nixPkgs = ["firefox", "geckodriver", ...]'
echo ""

echo "📝 ИЗМЕНЕНИЯ В tradewatch_login.py:"
echo 'from selenium.webdriver.firefox.options import Options'
echo 'from selenium.webdriver.firefox.service import Service'
echo 'from webdriver_manager.firefox import GeckoDriverManager'
echo ""

echo "❓ ХОТИТЕ НАСТРОИТЬ FIREFOX?"
echo "Если Chrome не заработает после пересборки,"
echo "мы можем быстро переключиться на Firefox"
echo ""

read -p "Настроить Firefox сейчас? (y/n): " choice

if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    echo ""
    echo "🔧 Настраиваем Firefox..."

    # Обновляем nixpacks.toml для Firefox
    cat > nixpacks.toml << 'EOF'
[phases.setup]
nixPkgs = ["firefox", "nss", "nss_latest", "nspr", "atk", "gtk3", "gtk2", "gdk-pixbuf", "glib", "pango", "cairo", "freetype", "fontconfig", "libX11", "libXext", "libXrender", "libXtst", "libXi", "libXdamage", "libXcomposite", "libXfixes", "libXrandr", "libxcb", "libxkbcommon", "libdrm", "mesa", "libGL", "alsa-lib", "dbus", "cups", "expat", "zlib", "libpng", "libjpeg", "libtiff", "libwebp", "wget", "gnupg", "apt"]

[phases.install]
cmds = [
  "apt-get update && apt-get install -y firefox-esr",
  "wget -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz",
  "tar -xzf /tmp/geckodriver.tar.gz -C /usr/bin/",
  "chmod +x /usr/bin/geckodriver",
  "firefox --version",
  "geckodriver --version"
]

[phases.build]
cmds = [
  "python -m pip install --upgrade pip",
  "pip install -r requirements.txt"
]

[start]
cmd = "python run_bot.py"
EOF

    echo "✅ nixpacks.toml обновлен для Firefox"
    echo "🔄 Railway пересоберет проект..."
else
    echo ""
    echo "⏳ Ждем результатов с Chrome..."
    echo "Если Chrome не заработает, запустите этот скрипт снова"
fi

echo ""
echo "🎯 РЕЗУЛЬТАТ:"
echo "Firefox может быть более стабильным в Railway окружении!"