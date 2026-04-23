"""
Обработчики команд Telegram бота OmniVoice
"""
import logging
import os
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, FSInputFile, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import config
from database.manager import DatabaseManager
from services.tts import get_tts_service
from payments.service import get_payment_service
from models.database import SubscriptionTier

logger = logging.getLogger(__name__)


class TextGeneration(StatesGroup):
    """Состояния для генерации текста в речь"""
    waiting_for_text = State()
    waiting_for_ref_audio = State()
    waiting_for_ref_text = State()
    waiting_for_voice_design = State()
    waiting_for_voice_select = State()


def create_main_keyboard(user) -> InlineKeyboardMarkup:
    """Создать главное меню"""
    buttons = [
        [InlineKeyboardButton(text="🎤 Генерация речи", callback_data="generate")],
        [InlineKeyboardButton(text="👥 Клонирование голоса", callback_data="clone_voice")],
        [InlineKeyboardButton(text="🎭 Дизайн голоса", callback_data="design_voice")],
        [InlineKeyboardButton(text="💳 Баланс и подписка", callback_data="balance")],
        [InlineKeyboardButton(text="📊 История", callback_data="history")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")],
    ]
    
    if config.is_admin(user.telegram_id):
        buttons.append([InlineKeyboardButton(text="🔧 Админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_subscription_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру с тарифами"""
    buttons = [
        [InlineKeyboardButton(text="🥉 Basic - $9.99", callback_data="sub_basic")],
        [InlineKeyboardButton(text="🥈 Pro - $29.99", callback_data="sub_pro")],
        [InlineKeyboardButton(text="🥇 Premium - $99.99", callback_data="sub_premium")],
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="topup_balance")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_generation_mode_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру выбора режима генерации"""
    buttons = [
        [InlineKeyboardButton(text="🤖 Авто голос", callback_data="mode_auto")],
        [InlineKeyboardButton(text="👥 Клонировать голос", callback_data="mode_clone")],
        [InlineKeyboardButton(text="🎭 Дизайн голоса", callback_data="mode_design")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def cmd_start(message: Message, db_manager: DatabaseManager):
    """Обработчик команды /start"""
    user = message.from_user
    
    await db_manager.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я **OmniVoice Bot** - твой персональный генератор речи с поддержкой 600+ языков!

🎯 **Что я умею:**
• 🎤 Генерация речи из текста
• 👥 Клонирование любого голоса
• 🎭 Создание уникальных голосов
• 💳 Гибкая система оплаты

Выбери действие в меню ниже 👇
    """
    
    db_user = await db_manager.get_user(user.id)
    await message.answer(
        welcome_text,
        reply_markup=create_main_keyboard(db_user),
        parse_mode="Markdown"
    )


async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
📖 **Помощь по OmniVoice Bot**

🎤 **Генерация речи:**
Отправьте текст, и бот преобразует его в речь

👥 **Клонирование голоса:**
1. Отправьте аудио с голосом для клонирования
2. (Опционально) Отправьте текст этого аудио
3. Отправьте текст для генерации

🎭 **Дизайн голоса:**
Опишите желаемый голос: "женский, низкий тембр, британский акцент"

💳 **Оплата:**
• Free: 5 мин/день бесплатно
• Basic: $9.99/мес - 60 мин/день
• Pro: $29.99/мес - 300 мин/день
• Premium: $99.99/мес - безлимит

📞 **Поддержка:** @omnivoice_support
    """
    
    await message.answer(help_text, parse_mode="Markdown")


async def cmd_cancel(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """Отмена текущего действия"""
    await state.clear()
    user = await db_manager.get_user(message.from_user.id)
    
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=create_main_keyboard(user)
    )


async def callback_generate(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала генерации"""
    await state.set_state(TextGeneration.waiting_for_text)
    
    text = """
🎤 **Генерация речи**

Отправьте текст, который нужно преобразовать в речь.

Максимальная длина: 1000 символов

Для отмены нажмите /cancel
    """
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


async def handle_text_for_generation(message: Message, state: FSMContext, 
                                     db_manager: DatabaseManager):
    """Обработка текста для генерации"""
    text = message.text
    
    if len(text) > 1000:
        await message.answer("❌ Текст слишком длинный. Максимум 1000 символов.")
        return
    
    await state.update_data(generation_text=text)
    await state.set_state(TextGeneration.waiting_for_voice_select)
    
    keyboard = create_generation_mode_keyboard()
    await message.answer(
        "🎯 Выберите режим генерации:",
        reply_markup=keyboard
    )


async def callback_mode_auto(callback: CallbackQuery, state: FSMContext, 
                             db_manager: DatabaseManager):
    """Генерация с авто-голосом"""
    data = await state.get_data()
    text = data.get("generation_text")
    
    if not text:
        await callback.message.edit_text("❌ Ошибка: текст не найден. Начните сначала.")
        await state.clear()
        return
    
    await callback.message.edit_text("⏳ Генерация... Пожалуйста, подождите.")
    await callback.answer()
    
    user = await db_manager.get_user(callback.from_user.id)
    tts_service = get_tts_service(config.omnivoice_model, config.inference_device)
    
    try:
        estimated_duration = await tts_service.estimate_duration(text)
        duration_minutes = estimated_duration / 60
        
        can_generate, error_msg = await db_manager.can_generate(user, duration_minutes, config)
        
        if not can_generate:
            await callback.message.edit_text(error_msg)
            await state.clear()
            return
        
        file_path, output_duration, error = await tts_service.generate_audio(
            text=text,
            mode="auto"
        )
        
        if error:
            await callback.message.edit_text(error)
            await state.clear()
            return
        
        user.daily_minutes_used += output_duration / 60
        user.total_minutes_generated += output_duration / 60
        await db_manager.update_user(user)
        
        audio_file = FSInputFile(file_path)
        await callback.message.answer_audio(audio_file, caption=f"⏱ Длительность: {output_duration:.2f} сек")
        
        tts_service.cleanup_temp_file(file_path)
        
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        await callback.message.edit_text(f"❌ Произошла ошибка: {str(e)}")
    
    await state.clear()
    
    user = await db_manager.get_user(callback.from_user.id)
    await callback.message.answer(
        "✅ Готово! Что еще хотите сделать?",
        reply_markup=create_main_keyboard(user)
    )


async def callback_clone_voice(callback: CallbackQuery, state: FSMContext):
    """Начало клонирования голоса"""
    await state.set_state(TextGeneration.waiting_for_ref_audio)
    
    text = """
👥 **Клонирование голоса**

Шаг 1/3: Отправьте аудиофайл с голосом для клонирования.

Требования:
• Чистый голос без шума
• Длительность 5-30 секунд
• Формат: MP3, WAV, OGG

Для отмены нажмите /cancel
    """
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


async def handle_ref_audio(message: Message, state: FSMContext):
    """Обработка референсного аудио"""
    if not message.audio and not message.voice:
        await message.answer("❌ Пожалуйста, отправьте аудиофайл или голосовое сообщение.")
        return
    
    audio_file = message.audio or message.voice
    file_id = audio_file.file_id
    
    file = await message.bot.get_file(file_id)
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/ref_{message.from_user.id}_{file.file_unique_id}.wav"
    
    await message.bot.download_file(file.file_path, file_path)
    
    await state.update_data(ref_audio_path=file_path)
    await state.set_state(TextGeneration.waiting_for_ref_text)
    
    await message.answer(
        "✅ Аудио получено!\n\n"
        "Шаг 2/3: Отправьте текст, который был записан в этом аудио.\n"
        "Это поможет точнее клонировать голос.\n\n"
        "Если не знаете текст, напишите 'не знаю'."
    )


async def handle_ref_text(message: Message, state: FSMContext):
    """Обработка текста референса"""
    ref_text = message.text
    
    await state.update_data(ref_text=ref_text)
    await state.set_state(TextGeneration.waiting_for_text)
    
    await message.answer(
        "✅ Текст получен!\n\n"
        "Шаг 3/3: Теперь отправьте текст, который нужно озвучить клонированным голосом.\n\n"
        "Максимальная длина: 1000 символов."
    )


async def callback_mode_clone(callback: CallbackQuery, state: FSMContext, 
                              db_manager: DatabaseManager):
    """Генерация с клонированием голоса"""
    data = await state.get_data()
    text = data.get("generation_text")
    ref_audio_path = data.get("ref_audio_path")
    ref_text = data.get("ref_text", "")
    
    if not text or not ref_audio_path:
        await callback.message.edit_text("❌ Ошибка: недостаточно данных для генерации.")
        await state.clear()
        return
    
    await callback.message.edit_text("⏳ Клонирование голоса и генерация... Пожалуйста, подождите.")
    await callback.answer()
    
    user = await db_manager.get_user(callback.from_user.id)
    tts_service = get_tts_service(config.omnivoice_model, config.inference_device)
    
    try:
        estimated_duration = await tts_service.estimate_duration(text)
        duration_minutes = estimated_duration / 60
        
        can_generate, error_msg = await db_manager.can_generate(user, duration_minutes, config)
        
        if not can_generate:
            await callback.message.edit_text(error_msg)
            await state.clear()
            return
        
        file_path, output_duration, error = await tts_service.generate_audio(
            text=text,
            mode="clone",
            ref_audio_path=ref_audio_path,
            ref_text=ref_text
        )
        
        if error:
            await callback.message.edit_text(error)
            await state.clear()
            return
        
        user.daily_minutes_used += output_duration / 60
        user.total_minutes_generated += output_duration / 60
        await db_manager.update_user(user)
        
        audio_file = FSInputFile(file_path)
        await callback.message.answer_audio(audio_file, caption=f"⏱ Длительность: {output_duration:.2f} сек")
        
        tts_service.cleanup_temp_file(file_path)
        tts_service.cleanup_temp_file(ref_audio_path)
        
    except Exception as e:
        logger.error(f"Ошибка клонирования: {e}")
        await callback.message.edit_text(f"❌ Произошла ошибка: {str(e)}")
    
    await state.clear()
    
    user = await db_manager.get_user(callback.from_user.id)
    await callback.message.answer(
        "✅ Голос клонирован и аудио создано! Что еще хотите сделать?",
        reply_markup=create_main_keyboard(user)
    )


async def callback_design_voice(callback: CallbackQuery, state: FSMContext):
    """Начало дизайна голоса"""
    await state.set_state(TextGeneration.waiting_for_voice_design)
    
    text = """
🎭 **Дизайн голоса**

Опишите желаемый голос своими словами.

Примеры:
• "женский, низкий тембр, британский акцент"
• "мужской, молодой, энергичный, американский"
• "старик, мудрый, медленная речь"

Для отмены нажмите /cancel
    """
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


async def handle_voice_design_text(message: Message, state: FSMContext):
    """Обработка описания голоса"""
    voice_design = message.text
    
    await state.update_data(voice_design=voice_design)
    await state.set_state(TextGeneration.waiting_for_text)
    
    await message.answer(
        f"✅ Описание голоса сохранено: \"{voice_design}\"\n\n"
        "Теперь отправьте текст, который нужно озвучить этим голосом.\n\n"
        "Максимальная длина: 1000 символов."
    )


async def callback_mode_design(callback: CallbackQuery, state: FSMContext,
                               db_manager: DatabaseManager):
    """Генерация с дизайном голоса"""
    data = await state.get_data()
    text = data.get("generation_text")
    voice_design = data.get("voice_design")
    
    if not text:
        await callback.message.edit_text("❌ Сначала отправьте текст для генерации.")
        await state.set_state(TextGeneration.waiting_for_text)
        return
    
    await callback.message.edit_text("⏳ Создание голоса по описанию и генерация... Подождите.")
    await callback.answer()
    
    user = await db_manager.get_user(callback.from_user.id)
    tts_service = get_tts_service(config.omnivoice_model, config.inference_device)
    
    try:
        estimated_duration = await tts_service.estimate_duration(text)
        duration_minutes = estimated_duration / 60
        
        can_generate, error_msg = await db_manager.can_generate(user, duration_minutes, config)
        
        if not can_generate:
            await callback.message.edit_text(error_msg)
            await state.clear()
            return
        
        file_path, output_duration, error = await tts_service.generate_audio(
            text=text,
            mode="design",
            voice_description=voice_design
        )
        
        if error:
            await callback.message.edit_text(error)
            await state.clear()
            return
        
        user.daily_minutes_used += output_duration / 60
        user.total_minutes_generated += output_duration / 60
        await db_manager.update_user(user)
        
        audio_file = FSInputFile(file_path)
        await callback.message.answer_audio(audio_file, caption=f"⏱ Длительность: {output_duration:.2f} сек")
        
        tts_service.cleanup_temp_file(file_path)
        
    except Exception as e:
        logger.error(f"Ошибка дизайна голоса: {e}")
        await callback.message.edit_text(f"❌ Произошла ошибка: {str(e)}")
    
    await state.clear()
    
    user = await db_manager.get_user(callback.from_user.id)
    await callback.message.answer(
        "✅ Уникальный голос создан! Что еще хотите сделать?",
        reply_markup=create_main_keyboard(user)
    )


async def callback_balance(callback: CallbackQuery, db_manager: DatabaseManager):
    """Показать баланс и подписку"""
    user = await db_manager.get_user(callback.from_user.id)
    
    tier_names = {
        SubscriptionTier.FREE: "Free",
        SubscriptionTier.BASIC: "Basic",
        SubscriptionTier.PRO: "Pro",
        SubscriptionTier.PREMIUM: "Premium"
    }
    
    tier_emoji = {
        SubscriptionTier.FREE: "🆓",
        SubscriptionTier.BASIC: "🥉",
        SubscriptionTier.PRO: "🥈",
        SubscriptionTier.PREMIUM: "🥇"
    }
    
    if user.subscription_expires_at:
        expires_str = user.subscription_expires_at.strftime("%d.%m.%Y %H:%M")
    else:
        expires_str = "Не активна"
    
    balance_text = f"""
💳 **Ваш баланс и подписка**

{tier_emoji[user.subscription_tier]} **Тариф:** {tier_names[user.subscription_tier]}
📅 **Истекает:** {expires_str}

💰 **Баланс:** ${user.balance / 100:.2f}

📊 **Статистика:**
• Всего сгенерировано: {user.total_minutes_generated:.1f} мин
• Сегодня использовано: {user.daily_minutes_used:.1f} мин
• Дневной лимит: {config.free_daily_limit} мин

    """
    
    await callback.message.edit_text(
        balance_text,
        reply_markup=create_subscription_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


async def callback_history(callback: CallbackQuery, db_manager: DatabaseManager):
    """Показать историю генераций"""
    user = await db_manager.get_user(callback.from_user.id)
    
    history = await db_manager.get_generation_history(user, limit=5)
    
    if not history:
        await callback.message.edit_text("📭 История пуста")
        await callback.answer()
        return
    
    history_text = "📊 **Последние генерации:**\n\n"
    
    for req in history:
        status_emoji = {"completed": "✅", "failed": "❌", "processing": "⏳"}.get(req.status, "⏳")
        date_str = req.created_at.strftime("%d.%m %H:%M")
        history_text += f"{status_emoji} {date_str} - {req.mode} ({req.output_duration or 0:.1f} сек)\n"
    
    history_text += "\nДля деталей используйте /mygenerations"
    
    await callback.message.edit_text(history_text, parse_mode="Markdown")
    await callback.answer()


async def callback_back_to_main(callback: CallbackQuery, db_manager: DatabaseManager):
    """Возврат в главное меню"""
    user = await db_manager.get_user(callback.from_user.id)
    
    await callback.message.edit_text(
        "🏠 Главное меню",
        reply_markup=create_main_keyboard(user)
    )
    await callback.answer()


def register_handlers(dp: Dispatcher, db_manager: DatabaseManager):
    """Регистрация всех обработчиков"""
    
    dp["db_manager"] = db_manager
    
    # Команды
    dp.message.register(lambda msg: cmd_start(msg, db_manager), CommandStart())
    dp.message.register(lambda msg: cmd_help(msg), Command("help"))
    dp.message.register(lambda msg: cmd_cancel(msg, FSMContext(), db_manager), Command("cancel"))
    
    # Генерация текста
    dp.callback_query.register(lambda cb: callback_generate(cb, FSMContext()), F.data == "generate")
    dp.message.register(lambda msg, state: handle_text_for_generation(msg, state, db_manager), TextGeneration.waiting_for_text)
    
    # Клонирование голоса
    dp.callback_query.register(lambda cb: callback_clone_voice(cb, FSMContext()), F.data == "clone_voice")
    dp.message.register(lambda msg, state: handle_ref_audio(msg, state), TextGeneration.waiting_for_ref_audio)
    dp.message.register(lambda msg, state: handle_ref_text(msg, state), TextGeneration.waiting_for_ref_text)
    
    # Дизайн голоса
    dp.callback_query.register(lambda cb: callback_design_voice(cb, FSMContext()), F.data == "design_voice")
    dp.message.register(lambda msg, state: handle_voice_design_text(msg, state), TextGeneration.waiting_for_voice_design)
    
    # Режимы генерации
    dp.callback_query.register(lambda cb, state: callback_mode_auto(cb, state, db_manager), F.data == "mode_auto")
    dp.callback_query.register(lambda cb, state: callback_mode_clone(cb, state, db_manager), F.data == "mode_clone")
    dp.callback_query.register(lambda cb, state: callback_mode_design(cb, state, db_manager), F.data == "mode_design")
    
    # Баланс и подписка
    dp.callback_query.register(lambda cb: callback_balance(cb, db_manager), F.data == "balance")
    
    # История
    dp.callback_query.register(lambda cb: callback_history(cb, db_manager), F.data == "history")
    
    # Навигация
    dp.callback_query.register(lambda cb: callback_back_to_main(cb, db_manager), F.data == "back_to_main")
