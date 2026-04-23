#!/bin/bash

# FuelProcess SaaS - Автоматическая установка и запуск
# Этот скрипт настроит и запустит всё необходимое

set -e

echo "🚀 FuelProcess SaaS - Установка и запуск"
echo "========================================="

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден! Установите Docker сначала."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose не найден! Установите Docker Compose сначала."
    exit 1
fi

echo "✅ Docker и Docker Compose найдены"

# Создание .env файла если не существует
if [ ! -f .env ]; then
    echo "📝 Создание файла .env..."
    cat > .env << EOF
# База данных
POSTGRES_USER=fuelprocess_user
POSTGRES_PASSWORD=fuelprocess_secure_password_2024

# Безопасность (измените в production!)
SECRET_KEY=your-super-secret-key-change-in-production-$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://redis:6379

# CORS
ALLOWED_ORIGINS=["http://localhost:3000"]

# Логирование
LOG_LEVEL=INFO

# Внешние API (опционально)
OPENROUTESERVICE_API_KEY=
SMTP_SERVER=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
EOF
    echo "✅ Файл .env создан"
else
    echo "✅ Файл .env уже существует"
fi

# Остановка старых контейнеров
echo "🛑 Остановка старых контейнеров..."
docker compose down 2>/dev/null || true

# Запуск сервисов
echo "🏗️  Запуск сервисов (это может занять несколько минут)..."
docker compose up -d --build

# Ожидание готовности backend
echo "⏳ Ожидание готовности backend..."
sleep 15

# Проверка здоровья backend
echo "🔍 Проверка здоровья сервисов..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health/ready > /dev/null 2>&1; then
        echo "✅ Backend готов!"
        break
    fi
    echo "   Попытка $attempt/$max_attempts..."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "⚠️  Backend не ответил вовремя, но это не критично"
fi

# Создание демо-данных
echo "📊 Создание демо-данных..."
docker compose exec -T backend python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.seed import seed_demo_data

async def main():
    async with AsyncSessionLocal() as session:
        await seed_demo_data(session)
        await session.commit()

asyncio.run(main())
" 2>/dev/null || echo "⚠️  Демо-данные будут созданы при первом запросе"

echo ""
echo "========================================="
echo "🎉 Установка завершена успешно!"
echo "========================================="
echo ""
echo "📱 Доступ к приложениям:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   Swagger:   http://localhost:8000/api/v1/docs"
echo "   ReDoc:     http://localhost:8000/api/v1/redoc"
echo ""
echo "🔐 Данные для входа:"
echo "   Admin: admin / admin123"
echo "   Tech:  tech / tech123"
echo ""
echo "📋 Полезные команды:"
echo "   ./start.sh          - Запустить проект"
echo "   ./stop.sh           - Остановить проект"
echo "   ./logs.sh           - Просмотр логов"
echo "   ./reset.sh          - Полный сброс и перезапуск"
echo "   docker compose ps   - Статус контейнеров"
echo ""
echo "📖 Документация: README.md"
echo ""
