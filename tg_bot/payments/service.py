"""
Платежный сервис для обработки платежей и подписок
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

from models.database import SubscriptionTier


class PaymentProvider(Enum):
    """Поддерживаемые платежные провайдеры"""
    STripe = "stripe"
    YOOKASSA = "yookassa"
    CRYPTO = "crypto"
    TELEGRAM_STARS = "telegram_stars"


class PaymentService:
    """Сервис для обработки платежей"""
    
    def __init__(self, provider_token: str = "", provider: str = "telegram_stars"):
        self.provider_token = provider_token
        self.provider = provider
        self._invoices: Dict[str, Dict] = {}  # Хранилище инвойсов (в production использовать Redis/DB)
    
    def create_invoice(self, user_id: int, amount: float, description: str, 
                       currency: str = "USD") -> Dict[str, Any]:
        """
        Создать инвойс для оплаты
        
        Args:
            user_id: ID пользователя в Telegram
            amount: Сумма в центах
            description: Описание платежа
            currency: Валюта (USD, RUB, EUR)
        
        Returns:
            Данные инвойса для отправки пользователю
        """
        invoice_id = f"inv_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Конвертация из центов в основную валюту
        amount_in_currency = amount / 100 if currency == "USD" else amount
        
        invoice_data = {
            "invoice_id": invoice_id,
            "user_id": user_id,
            "amount": amount,
            "amount_in_currency": amount_in_currency,
            "currency": currency,
            "description": description,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        self._invoices[invoice_id] = invoice_data
        
        return {
            "title": "OmniVoice Bot",
            "description": description,
            "payload": invoice_id,
            "provider_token": self.provider_token if self.provider != "telegram_stars" else "",
            "currency": currency,
            "prices": [
                {"label": description, "amount": int(amount_in_currency) * 100}
            ],
            "start_parameter": f"pay_{invoice_id}",
            "need_name": False,
            "need_email": False,
            "need_phone_number": False,
            "need_shipping_address": False,
            "is_flexible": False
        }
    
    def create_subscription_invoice(self, user_id: int, tier: SubscriptionTier, 
                                    months: int = 1, config=None) -> Dict[str, Any]:
        """
        Создать инвойс для оплаты подписки
        
        Args:
            user_id: ID пользователя
            tier: Уровень подписки
            months: Количество месяцев
            config: Конфигурация с ценами
        
        Returns:
            Данные инвойса
        """
        if config is None:
            # Цены по умолчанию
            prices = {
                SubscriptionTier.BASIC: 999,
                SubscriptionTier.PRO: 2999,
                SubscriptionTier.PREMIUM: 9999
            }
        else:
            prices = {
                SubscriptionTier.BASIC: config.subscription_basic,
                SubscriptionTier.PRO: config.subscription_pro,
                SubscriptionTier.PREMIUM: config.subscription_premium
            }
        
        base_price = prices.get(tier, 0)
        total_amount = base_price * months
        
        tier_names = {
            SubscriptionTier.BASIC: "Basic",
            SubscriptionTier.PRO: "Pro",
            SubscriptionTier.PREMIUM: "Premium"
        }
        
        description = f"📅 Подписка {tier_names[tier]} на {months} мес."
        
        return self.create_invoice(
            user_id=user_id,
            amount=total_amount,
            description=description
        )
    
    async def process_payment(self, invoice_id: str, payment_data: Dict) -> bool:
        """
        Обработать успешный платеж
        
        Args:
            invoice_id: ID инвойса
            payment_data: Данные платежа от провайдера
        
        Returns:
            True если платеж успешно обработан
        """
        if invoice_id not in self._invoices:
            return False
        
        invoice = self._invoices[invoice_id]
        invoice["status"] = "completed"
        invoice["payment_data"] = payment_data
        invoice["completed_at"] = datetime.utcnow()
        
        # В production здесь будет вызов API платежного провайдера для верификации
        # и webhook для подтверждения платежа
        
        return True
    
    def get_subscription_expires_at(self, tier: SubscriptionTier, 
                                    months: int = 1, 
                                    current_expires: Optional[datetime] = None) -> datetime:
        """
        Рассчитать дату окончания подписки
        
        Args:
            tier: Уровень подписки (влияет на длительность бонусов)
            months: Количество месяцев
            current_expires: Текущая дата окончания (для продления)
        
        Returns:
            Дата окончания подписки
        """
        now = datetime.utcnow()
        
        # Если текущая подписка еще активна, продлеваем от текущей даты
        if current_expires and current_expires > now:
            start_date = current_expires
        else:
            start_date = now
        
        # Добавляем месяцы
        expires = start_date + timedelta(days=30 * months)
        
        # Бонусы для премиум подписок
        if tier == SubscriptionTier.PREMIUM:
            expires += timedelta(days=7)  # +7 дней бонусом
        elif tier == SubscriptionTier.PRO:
            expires += timedelta(days=3)  # +3 дня бонусом
        
        return expires
    
    def get_payment_methods_text(self) -> str:
        """Вернуть текст с доступными методами оплаты"""
        return """
💳 **Доступные способы оплаты:**

• 🌟 Telegram Stars (мгновенно)
• 💳 Банковская карта (Visa, Mastercard, MIR)
• 🪙 Криптовалюта (USDT, BTC, ETH)
• 📱 ЮMoney, QIWI (для РФ)

Минимальная сумма пополнения: $1
        """.strip()
    
    def get_subscription_benefits(self, tier: SubscriptionTier) -> str:
        """Вернуть описание преимуществ подписки"""
        benefits = {
            SubscriptionTier.FREE: """
🆓 **Free**
• 5 минут генерации в день
• Стандартное качество
• Базовая поддержка
            """,
            SubscriptionTier.BASIC: """
🥉 **Basic** - $9.99/мес
• 60 минут генерации в день
• Высокое качество
• Приоритетная очередь
• 5 клонирований голоса
            """,
            SubscriptionTier.PRO: """
🥈 **Pro** - $29.99/мес
• 300 минут генерации в день
• Премиум качество
• Быстрая генерация
• Безлимитное клонирование
• Доступ к премиум голосам
• API доступ
            """,
            SubscriptionTier.PREMIUM: """
🥇 **Premium** - $99.99/мес
• Безлимитная генерация
• Максимальное качество
• Мгновенная генерация
• Все премиум голоса
• Приоритетная поддержка
• Custom голоса на заказ
            """
        }
        
        return benefits.get(tier, benefits[SubscriptionTier.FREE]).strip()


# Глобальный экземпляр сервиса
payment_service: Optional[PaymentService] = None


def get_payment_service(provider_token: str = "", provider: str = "telegram_stars") -> PaymentService:
    """Получить или создать экземпляр платежного сервиса"""
    global payment_service
    if payment_service is None:
        payment_service = PaymentService(provider_token=provider_token, provider=provider)
    return payment_service
