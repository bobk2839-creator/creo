"""
Модели данных для базы данных
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class SubscriptionTier(Enum):
    """Уровни подписки"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"


class User(Base):
    """Пользователь бота"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Подписка
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_expires_at = Column(DateTime, nullable=True)
    
    # Баланс (в центах)
    balance = Column(Float, default=0.0)
    
    # Статистика использования
    total_minutes_generated = Column(Float, default=0.0)
    daily_minutes_used = Column(Float, default=0.0)
    last_usage_date = Column(DateTime, nullable=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    transactions = relationship("Transaction", back_populates="user")
    generation_requests = relationship("GenerationRequest", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Transaction(Base):
    """Транзакции пользователей"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Тип транзакции
    transaction_type = Column(String(50), nullable=False)  # payment, refund, subscription, etc.
    
    # Сумма (в центах, может быть отрицательной для списаний)
    amount = Column(Float, nullable=False)
    
    # Статус
    status = Column(String(50), default="pending")  # pending, completed, failed
    
    # Описание
    description = Column(String(500), nullable=True)
    
    # ID платежа от провайдера
    payment_id = Column(String(255), nullable=True, unique=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount})>"


class GenerationRequest(Base):
    """Запросы на генерацию аудио"""
    __tablename__ = "generation_requests"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Входные данные
    text = Column(String(10000), nullable=False)
    mode = Column(String(50), nullable=False)  # clone, design, auto
    
    # Для клонирования голоса
    ref_audio_file_id = Column(String(255), nullable=True)
    ref_text = Column(String(1000), nullable=True)
    
    # Для дизайна голоса
    voice_instruct = Column(String(500), nullable=True)
    
    # Параметры генерации
    duration = Column(Float, nullable=True)
    speed = Column(Float, default=1.0)
    
    # Результат
    output_audio_file_id = Column(String(255), nullable=True)
    output_duration = Column(Float, nullable=True)
    
    # Стоимость (в центах)
    cost = Column(Float, default=0.0)
    
    # Статус
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(String(1000), nullable=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="generation_requests")
    
    def __repr__(self):
        return f"<GenerationRequest(id={self.id}, user_id={self.user_id}, status={self.status})>"


class VoicePreset(Base):
    """Пресеты голосов для продажи"""
    __tablename__ = "voice_presets"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(String(1000), nullable=True)
    
    # Параметры голоса
    voice_instruct = Column(String(500), nullable=False)
    
    # Цена (в центах)
    price = Column(Float, default=0.0)
    
    # Доступность
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    
    # Статистика
    purchase_count = Column(Integer, default=0)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<VoicePreset(id={self.id}, name={self.name})>"
