"""
Менеджер базы данных
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional, List

from models.database import Base, User, Transaction, GenerationRequest, VoicePreset, SubscriptionTier


class DatabaseManager:
    """Асинхронный менеджер базы данных"""
    
    def __init__(self, database_url: str):
        # Добавляем префикс для асинхронного SQLite драйвера если его нет
        if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite+aiosqlite:///"):
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_db(self):
        """Инициализация базы данных (создание таблиц)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        async with self.async_session_maker() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            return result.scalar_one_or_none()
    
    async def create_user(self, telegram_id: int, username: str = None, 
                         first_name: str = None, last_name: str = None) -> User:
        """Создать нового пользователя"""
        async with self.async_session_maker() as session:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def get_or_create_user(self, telegram_id: int, username: str = None,
                                 first_name: str = None, last_name: str = None) -> User:
        """Получить или создать пользователя"""
        user = await self.get_user(telegram_id)
        if not user:
            user = await self.create_user(telegram_id, username, first_name, last_name)
        return user
    
    async def reset_daily_usage(self, user: User):
        """Сбросить дневное использование если новый день"""
        today = datetime.utcnow().date()
        if not user.last_usage_date or user.last_usage_date.date() != today:
            user.daily_minutes_used = 0.0
            user.last_usage_date = datetime.utcnow()
    
    async def can_generate(self, user: User, duration_minutes: float, config) -> tuple[bool, str]:
        """Проверить, может ли пользователь сгенерировать аудио заданной длительности"""
        await self.reset_daily_usage(user)
        
        # Проверка для бесплатных пользователей
        if user.subscription_tier == SubscriptionTier.FREE:
            if user.daily_minutes_used + duration_minutes > config.free_daily_limit:
                remaining = config.free_daily_limit - user.daily_minutes_used
                return False, f"❌ Превышен дневной лимит ({config.free_daily_limit} мин). Осталось: {remaining:.1f} мин.\n\n💎 Оформите подписку для увеличения лимита!"
        
        # Проверка баланса для платных пользователей без подписки
        if user.subscription_tier == SubscriptionTier.FREE and user.balance <= 0:
            cost = duration_minutes * config.price_per_minute
            if user.balance < cost:
                return False, f"❌ Недостаточно средств на балансе.\n\n💰 Стоимость: {cost/100:.2f}$\n💳 Баланс: {user.balance/100:.2f}$"
        
        # Проверка активной подписки
        if user.subscription_tier != SubscriptionTier.FREE:
            if user.subscription_expires_at and user.subscription_expires_at < datetime.utcnow():
                # Подписка истекла
                user.subscription_tier = SubscriptionTier.FREE
                await self.update_user(user)
        
        return True, ""
    
    async def update_user(self, user: User):
        """Обновить данные пользователя"""
        async with self.async_session_maker() as session:
            await session.merge(user)
            await session.commit()
    
    async def add_balance(self, user: User, amount: float, description: str = "", 
                         payment_id: str = None) -> Transaction:
        """Добавить средства на баланс пользователя"""
        async with self.async_session_maker() as session:
            user.balance += amount
            
            transaction = Transaction(
                user_id=user.id,
                transaction_type="payment",
                amount=amount,
                status="completed",
                description=description,
                payment_id=payment_id
            )
            
            session.add(transaction)
            await session.commit()
            return transaction
    
    async def deduct_balance(self, user: User, amount: float, description: str = "") -> bool:
        """Списать средства с баланса пользователя"""
        if user.balance < amount:
            return False
        
        async with self.async_session_maker() as session:
            user.balance -= amount
            
            transaction = Transaction(
                user_id=user.id,
                transaction_type="debit",
                amount=-amount,
                status="completed",
                description=description
            )
            
            session.add(transaction)
            await session.commit()
            return True
    
    async def create_generation_request(self, user: User, text: str, mode: str,
                                       ref_audio_file_id: str = None, ref_text: str = None,
                                       voice_instruct: str = None, duration: float = None,
                                       speed: float = 1.0) -> GenerationRequest:
        """Создать запрос на генерацию"""
        async with self.async_session_maker() as session:
            request = GenerationRequest(
                user_id=user.id,
                text=text,
                mode=mode,
                ref_audio_file_id=ref_audio_file_id,
                ref_text=ref_text,
                voice_instruct=voice_instruct,
                duration=duration,
                speed=speed,
                status="pending"
            )
            
            session.add(request)
            await session.commit()
            await session.refresh(request)
            return request
    
    async def update_generation_request(self, request: GenerationRequest, **kwargs):
        """Обновить запрос на генерацию"""
        async with self.async_session_maker() as session:
            for key, value in kwargs.items():
                setattr(request, key, value)
            
            if request.status in ["completed", "failed"]:
                request.completed_at = datetime.utcnow()
            
            await session.commit()
    
    async def get_generation_history(self, user: User, limit: int = 10) -> List[GenerationRequest]:
        """Получить историю генераций пользователя"""
        async with self.async_session_maker() as session:
            result = await session.execute(
                select(GenerationRequest)
                .where(GenerationRequest.user_id == user.id)
                .order_by(GenerationRequest.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_transaction_history(self, user: User, limit: int = 10) -> List[Transaction]:
        """Получить историю транзакций пользователя"""
        async with self.async_session_maker() as session:
            result = await session.execute(
                select(Transaction)
                .where(Transaction.user_id == user.id)
                .order_by(Transaction.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_all_voice_presets(self) -> List[VoicePreset]:
        """Получить все доступные пресеты голосов"""
        async with self.async_session_maker() as session:
            result = await session.execute(
                select(VoicePreset).where(VoicePreset.is_active == True)
            )
            return result.scalars().all()
    
    async def get_voice_preset(self, preset_id: int) -> Optional[VoicePreset]:
        """Получить пресет голоса по ID"""
        async with self.async_session_maker() as session:
            result = await session.execute(select(VoicePreset).where(VoicePreset.id == preset_id))
            return result.scalar_one_or_none()
    
    async def upgrade_subscription(self, user: User, tier: SubscriptionTier, 
                                   expires_at: datetime, amount_paid: float) -> Transaction:
        """Обновить подписку пользователя"""
        async with self.async_session_maker() as session:
            user.subscription_tier = tier
            user.subscription_expires_at = expires_at
            
            transaction = Transaction(
                user_id=user.id,
                transaction_type="subscription",
                amount=-amount_paid,
                status="completed",
                description=f"Подписка {tier.value} до {expires_at.strftime('%Y-%m-%d')}"
            )
            
            session.add(transaction)
            await session.commit()
            return transaction
    
    async def get_stats(self) -> dict:
        """Получить общую статистику"""
        async with self.async_session_maker() as session:
            total_users = await session.execute(select(func.count(User.id)))
            total_revenue = await session.execute(
                select(func.sum(Transaction.amount)).where(Transaction.amount > 0)
            )
            total_generations = await session.execute(select(func.count(GenerationRequest.id)))
            
            return {
                "total_users": total_users.scalar(),
                "total_revenue": total_revenue.scalar() or 0,
                "total_generations": total_generations.scalar()
            }
