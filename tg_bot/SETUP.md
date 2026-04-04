# Инструкция по запуску OmniVoice Telegram Bot

## Быстрый старт

### 1. Подготовка окружения

#### Вариант A: Локальная установка (рекомендуется для разработки)

```bash
# Создание виртуального окружения
python -m venv venv

# Активация (Linux/Mac)
source venv/bin/activate

# Активация (Windows)
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Копирование .env.example в .env
cp .env.example .env

# Редактирование .env - добавьте ваш BOT_TOKEN
nano .env  # или используйте любой редактор
```

#### Вариант B: Docker (рекомендуется для production)

```bash
# Копирование .env.example в .env
cp .env.example .env

# Редактирование .env

# Запуск через docker-compose
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot
```

### 2. Получение токена бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Введите имя бота (например, "OmniVoice Bot")
   - Введите username бота (должен заканчиваться на `bot`, например `omnivoice_tts_bot`)
4. Скопируйте полученный токен
5. Добавьте токен в файл `.env`:
   ```
   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

### 3. Запуск бота

#### Локально:
```bash
python main.py
```

#### В Docker:
```bash
docker-compose up -d
```

### 4. Проверка работы

1. Найдите вашего бота в Telegram по username
2. Нажмите `/start`
3. Попробуйте сгенерировать речь!

---

## Конфигурация

### Основные переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `BOT_TOKEN` | Токен от @BotFather | `1234567890:ABCdef...` |
| `DATABASE_URL` | URL базы данных | `sqlite:///bot.db` |
| `OMNIVOICE_MODEL` | Модель для генерации | `k2-fsa/OmniVoice` |
| `INFERENCE_DEVICE` | Устройство для inference | `cuda`, `cpu`, `mps` |
| `FREE_DAILY_LIMIT` | Бесплатный лимит (мин/день) | `5` |
| `PRICE_PER_MINUTE` | Цена за минуту (центы) | `10` |
| `ADMIN_IDS` | ID админов (через запятую) | `123456789,987654321` |

### Платежи

Для подключения платежей:

1. **Telegram Stars** (рекомендуется):
   - Не требует дополнительной настройки
   - Работает во всех странах

2. **Stripe**:
   - Зарегистрируйтесь на [stripe.com](https://stripe.com)
   - Получите API ключи
   - Добавьте `PAYMENT_PROVIDER_TOKEN` в `.env`

3. **Другие провайдеры**:
   - ЮKassa (для РФ)
   - CryptoCloud (криптовалюты)
   - И другие через Bot API

---

## Монетизация

### Настройка тарифов

В файле `.env`:

```env
# Цена за минуту для pay-per-use (в центах)
PRICE_PER_MINUTE=10

# Подписки (месячная цена в центах)
SUBSCRIPTION_BASIC=999      # $9.99
SUBSCRIPTION_PRO=2999       # $29.99
SUBSCRIPTION_PREMIUM=9999   # $99.99

# Бесплатный лимит
FREE_DAILY_LIMIT=5
```

### Рекомендуемая стратегия монетизации

1. **Free tier**: 5 минут/день для привлечения пользователей
2. **Basic ($9.99)**: Для обычных пользователей (60 мин/день)
3. **Pro ($29.99)**: Для контент-мейкеров (300 мин/день)
4. **Premium ($99.99)**: Для бизнеса (безлимит)

### Дополнительные источники дохода

- Продажа уникальных голосовых пресетов
- Кастомные голоса на заказ
- API доступ для разработчиков
- Белая этикетка для бизнеса

---

## Production развертывание

### Требования к серверу

**Минимальные (CPU):**
- 4 CPU cores
- 8 GB RAM
- 20 GB SSD

**Рекомендуемые (GPU):**
- NVIDIA GPU с 8+ GB VRAM
- 8 CPU cores
- 16 GB RAM
- 50 GB SSD

### Развертывание на VPS

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Клонирование проекта
git clone <your-repo> omnivoice-bot
cd omnivoice-bot/tg_bot

# Настройка
cp .env.example .env
nano .env  # Добавьте BOT_TOKEN

# Запуск
docker-compose up -d
```

### Настройка HTTPS webhook (опционально)

Для production рекомендуется использовать webhook вместо polling:

1. Получите SSL сертификат (Let's Encrypt бесплатно)
2. Настройте nginx как reverse proxy
3. Установите webhook:
```python
await bot.set_webhook("https://your-domain.com/webhook")
```

---

## Администрирование

### Добавление админа

Добавьте ваш Telegram ID в `ADMIN_IDS` в `.env`:

1. Узнайте свой ID через [@userinfobot](https://t.me/userinfobot)
2. Добавьте в `.env`: `ADMIN_IDS=123456789`

### Админ-команды

- `/stats` - Общая статистика бота
- `/users` - Список пользователей
- `/broadcast` - Рассылка сообщений

---

## Troubleshooting

### Бот не запускается

1. Проверьте токен: `echo $BOT_TOKEN`
2. Проверьте логи: `docker-compose logs bot`
3. Убедитесь что все зависимости установлены

### Ошибки при генерации аудио

1. **TTS сервис недоступен**: Установите torch и torchaudio:
   ```bash
   pip install torch torchaudio omnivoice
   ```
   
2. Проверьте наличие GPU: `nvidia-smi`
3. Для CPU увеличьте память в docker-compose.yml
4. Проверьте место на диске: `df -h`

### Бот работает но не генерирует аудио

Бот запустится даже без установленных ML-библиотек (torch, torchaudio, omnivoice).
В этом случае он будет работать в демо-режиме - все кнопки работают, но при попытке 
генерации аудио появится сообщение с инструкцией по установке зависимостей.

Для полноценной работы установите:
```bash
pip install torch torchaudio omnivoice
```

Или используйте Docker образ с предустановленными зависимостями.

### Медленная генерация

1. Используйте GPU если возможно
2. Уменьшите `num_step` в настройках генерации
3. Рассмотрите queue систему для больших нагрузок

---

## Поддержка

- GitHub Issues: [ссылка]
- Telegram поддержка: @omnivoice_support
- Документация OmniVoice: https://github.com/k2-fsa/OmniVoice
