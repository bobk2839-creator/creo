"""
Точка входа для Telegram бота
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

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
    
    # Инициализация базы данных
    db_manager = DatabaseManager(config.database_url)
    await db_manager.init_db()
    logger.info("✅ База данных инициализирована")
    
    # Предварительная загрузка модели TTS (опционально)
    # Можно закомментировать для ленивой загрузки
    logger.info("🎤 Инициализация TTS сервиса...")
    try:
        tts_service = get_tts_service(config.omnivoice_model, config.inference_device)
        # tts_service.load_model()  # Раскомментировать для предзагрузки
        logger.info("✅ TTS сервис инициализирован")
    except ImportError as e:
        logger.warning(f"⚠️ TTS сервис недоступен: {e}")
        logger.warning("Бот будет работать в демо-режиме без генерации аудио")
        tts_service = None
    
    # Инициализация бота
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Создание диспетчера
    dp = Dispatcher()
    
    # Регистрация обработчиков
    register_handlers(dp, db_manager)
    
    # Сохранение объектов в хранилище диспетчера
    dp["db_manager"] = db_manager
    dp["tts_service"] = tts_service
    
    logger.info("✅ Обработчики зарегистрированы")
    logger.info(f"🤖 Бот запущен! @{(await bot.get_me()).username}")
    logger.info("💡 Для остановки нажмите Ctrl+C")
    
    # Запуск polling
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("👋 Остановка бота...")
    finally:
        await bot.session.close()
        logger.info("✅ Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
