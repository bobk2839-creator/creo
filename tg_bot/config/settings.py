"""
Конфигурация приложения
"""
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

load_dotenv()


class Config(BaseModel):
    """Конфигурация бота"""
    
    # Telegram
    bot_token: str = Field(default=os.getenv("BOT_TOKEN", ""))
    
    # Database
    database_url: str = Field(default=os.getenv("DATABASE_URL", "sqlite:///bot.db"))
    
    # OmniVoice
    omnivoice_model: str = Field(default=os.getenv("OMNIVOICE_MODEL", "k2-fsa/OmniVoice"))
    inference_device: str = Field(default=os.getenv("INFERENCE_DEVICE", "cuda"))
    
    # Payments
    payment_provider_token: str = Field(default=os.getenv("PAYMENT_PROVIDER_TOKEN", ""))
    price_per_minute: int = Field(default=int(os.getenv("PRICE_PER_MINUTE", "10")))
    
    # Subscriptions (monthly price in cents)
    subscription_basic: int = Field(default=int(os.getenv("SUBSCRIPTION_BASIC", "999")))
    subscription_pro: int = Field(default=int(os.getenv("SUBSCRIPTION_PRO", "2999")))
    subscription_premium: int = Field(default=int(os.getenv("SUBSCRIPTION_PREMIUM", "9999")))
    
    # Free tier
    free_daily_limit: int = Field(default=int(os.getenv("FREE_DAILY_LIMIT", "5")))
    
    # Admin
    admin_ids: List[int] = Field(
        default=[int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    )
    
    # Redis (optional)
    redis_url: str = Field(default=os.getenv("REDIS_URL", ""))
    
    @property
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь админом"""
        return user_id in self.admin_ids
    
    class Config:
        arbitrary_types_allowed = True


# Глобальный экземпляр конфигурации
config = Config()
