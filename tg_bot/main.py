"""
Точка входа для Telegram бота OmniVoice
"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import config
from database.manager import DatabaseManager
from bot.handlers import register_handlers
from services.tts import get_tts_service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    
    # Проверка токена
    if not config.bot_token:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
        logger.error("Получите токен у @BotFather и добавьте его в .env файл")
        return
    
    logger.info("🚀 Запуск OmniVoice Bot...")
    
    # Создание папки temp
    os.makedirs("temp", exist_ok=True)
    
    # Инициализация базы данных
    db_manager = DatabaseManager(config.database_url)
    await db_manager.init_db()
    logger.info("✅ База данных инициализирована")
    
    # Предварительная загрузка модели TTS (опционально)
    logger.info("🎤 Инициализация TTS сервиса...")
    tts_service = None
    try:
        tts_service = get_tts_service(config.omnivoice_model, config.inference_device)
        logger.info("✅ TTS сервис инициализирован")
    except ImportError as e:
        logger.warning(f"⚠️ TTS сервис недоступен: {e}")
        logger.warning("Бот будет работать в демо-режиме без генерации аудио")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка инициализации TTS: {e}")
        logger.warning("Бот будет работать в демо-режиме без генерации аудио")
    
    # Инициализация бота
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Создание диспетчера с хранилищем состояний
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Сохранение объектов в хранилище диспетчера
    dp["db_manager"] = db_manager
    dp["tts_service"] = tts_service
    
    # Регистрация обработчиков
    register_handlers(dp, db_manager)
    
    logger.info("✅ Обработчики зарегистрированы")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"🤖 Бот запущен! @{bot_info.username}")
        logger.info("💡 Для остановки нажмите Ctrl+C")
        
        # Запуск polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("👋 Остановка бота...")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()
        await storage.close()
        logger.info("✅ Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
