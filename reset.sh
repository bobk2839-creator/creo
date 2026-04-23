#!/bin/bash
# Полный сброс и перезапуск
echo "⚠️  Внимание! Это удалит все данные базы данных!"
read -p "Продолжить? (y/n): " confirm
if [ "$confirm" = "y" ]; then
    echo "🔄 Сброс и перезапуск..."
    docker compose down -v
    docker compose up -d --build
    echo "✅ Готово!"
else
    echo "❌ Отменено"
fi
