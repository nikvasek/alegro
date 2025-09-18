#!/bin/bash
# Тестирование healthcheck локально

echo "🧪 ТЕСТИРОВАНИЕ HEALTHCHECK"
echo "============================"
echo ""

echo "🔧 Запуск локального сервера для тестирования..."
echo "Это проверит, что Flask healthcheck работает"
echo ""

# Запускаем простой Flask сервер для тестирования
cat > test_health.py << 'EOF'
from flask import Flask
import os
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "telegram_bot"
    }

@app.route('/health')
def health():
    return {"status": "ok", "bot": "running"}

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
EOF

echo "🌐 Запуск тестового сервера..."
python3 test_health.py &
SERVER_PID=$!

echo ""
echo "⏳ Ожидание запуска сервера..."
sleep 3

echo ""
echo "🔍 Тестирование healthcheck endpoints:"
echo ""

# Тестируем /health endpoint
echo "📡 Тестирование /health:"
curl -s http://localhost:8080/health | python3 -m json.tool

echo ""
echo "📡 Тестирование /:"
curl -s http://localhost:8080/ | python3 -m json.tool

echo ""
echo "🛑 Остановка тестового сервера..."
kill $SERVER_PID 2>/dev/null

echo ""
echo "✅ Тестирование завершено!"
echo "Если оба endpoint вернули JSON с status, значит healthcheck работает!"

# Очистка
rm test_health.py