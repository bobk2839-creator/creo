# FuelProcess SaaS - Шпаргалка по запуску

## 🚀 Самый быстрый способ (1 команда)

```bash
./setup.sh
```

Всё! Скрипт сам:
- Проверит Docker
- Создаст настройки
- Запустит сервисы
- Создаст тестовые данные
- Покажет куда заходить

---

## 📋 Другие полезные команды

### Запуск/Остановка
```bash
./start.sh          # Быстрый запуск
./stop.sh           # Остановка
./reset.sh          # Полный сброс (удалит данные!)
```

### Логи
```bash
./logs.sh                   # Все логи
./logs.sh backend           # Только backend
./logs.sh frontend          # Только frontend
./logs.sh postgres          # Только база данных
```

### Через Docker Compose напрямую
```bash
docker compose up -d        # Запуск
docker compose down         # Остановка
docker compose ps           # Статус
docker compose logs -f      # Логи
docker compose restart      # Перезапуск
```

---

## 🔐 Данные для входа

| Роль | Логин | Пароль |
|------|-------|--------|
| Admin | `admin` | `admin123` |
| Tech | `tech` | `tech123` |

---

## 🌐 URL доступа

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Swagger (API Docs)**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

---

## ✅ Проверка что всё работает

```bash
# Проверка backend
curl http://localhost:8000/health/ready

# Должно вернуть: {"status":"ok"}
```

---

## 🐛 Если что-то не работает

### 1. Проверьте Docker
```bash
docker --version
docker compose version
```

### 2. Посмотрите логи
```bash
./logs.sh backend
```

### 3. Перезапустите
```bash
./stop.sh
./start.sh
```

### 4. Полный сброс (если совсем плохо)
```bash
./reset.sh
```

---

## 📚 Подробнее

Полная документация: [README.md](README.md)
