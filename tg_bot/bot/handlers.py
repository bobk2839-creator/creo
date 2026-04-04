"""
Обработчики команд Telegram бота
"""
import logging
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
    
    # Добавить кнопку админки для админов
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
    
    # Регистрация пользователя в БД
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
    
    await message.answer(
        welcome_text,
        reply_markup=create_main_keyboard(await db_manager.get_user(user.id)),
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
    
    await callback.message.edit_text("⏳ Генерация... Пожалуйста, подождите.")
    await callback.answer()
    
    # Получение пользователя
    user = await db_manager.get_user(callback.from_user.id)
    
    # Оценка длительности
    tts_service = get_tts_service(config.omnivoice_model, config.inference_device)
    estimated_duration = await tts_service.estimate_duration(text)
    duration_minutes = estimated_duration / 60
    
    # Проверка лимитов
    can_generate, error_msg = await db_manager.can_generate(user, duration_minutes, config)
    
    if not can_generate:
        await callback.message.edit_text(error_msg)
        await state.clear()
        return
    
    # Генерация аудио
    file_path, output_duration, error = await tts_service.generate_audio(
        text=text,
        mode="auto"
    )
    
    if error:
        await callback.message.edit_text(error)
        await state.clear()
        return
    
    # Обновление статистики
    user.daily_minutes_used += output_duration / 60
    user.total_minutes_generated += output_duration / 60
    await db_manager.update_user(user)
    
    # Отправка аудио
    audio_file = FSInputFile(file_path)
    await callback.message.answer_audio(audio_file, caption=f"⏱ Длительность: {output_duration:.2f} сек")
    
    # Очистка временного файла
    tts_service.cleanup_temp_file(file_path)
    
    await state.clear()
    
    # Возврат главного меню
    await callback.message.answer(
        "✅ Готово! Что еще хотите сделать?",
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
    
    # Форматирование даты окончания подписки
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


def register_handlers(dp: Dispatcher, db_manager: DatabaseManager):
    """Регистрация всех обработчиков"""
    
    # Команды
    dp.message.register(lambda msg: cmd_start(msg, db_manager), CommandStart())
    dp.message.register(cmd_help, Command("help"))
    
    # Генерация текста
    dp.callback_query.register(lambda cb: callback_generate(cb, FSMContext()), F.data == "generate")
    dp.message.register(lambda msg, state: handle_text_for_generation(msg, state, db_manager), TextGeneration.waiting_for_text)
    
    # Режимы генерации
    dp.callback_query.register(lambda cb, state: callback_mode_auto(cb, state, db_manager), F.data == "mode_auto")
    
    # Баланс и подписка
    dp.callback_query.register(lambda cb: callback_balance(cb, db_manager), F.data == "balance")
    
    # История
    dp.callback_query.register(lambda cb: callback_history(cb, db_manager), F.data == "history")
