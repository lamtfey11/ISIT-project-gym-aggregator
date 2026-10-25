"""Модель предметной области компонента core_tariff_service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

from fitagg_contracts import Money, PaymentSplit

# Базовая ошибка тарификации
class TariffError(Exception):
    ''

class TariffNotFoundError(TariffError):
    pass


class PlacementTermsMissingError(TariffError):
    pass


class InvalidPromoCodeError(TariffError):
    pass


@dataclass(frozen=True, slots=True)
class SubscriptionTariff:
    """Тариф абонемента: цену назначает администратор зала."""

    tariff_id: UUID
    gym_id: UUID
    title: str
    list_price: Money
    duration_days: int
    visits_total: int | None = None

    def __post_init__(self) -> None:
        if self.list_price.amount_minor <= 0:
            raise TariffError("Цена тарифа должна быть больше нуля")
        if self.duration_days < 1:
            raise TariffError("Срок действия абонемента должен быть не меньше 1 дня")


class PlacementModel(StrEnum):
    """Условия размещения зала на платформе (настраивает оператор платформы)."""

    COMMISSION = "COMMISSION"
    COMMISSION_WITH_MINIMUM = "COMMISSION_WITH_MINIMUM"
    SUBSCRIPTION = "SUBSCRIPTION"


@dataclass(frozen=True, slots=True)
class PlacementTerms:
    gym_id: UUID
    model: PlacementModel
    commission_rate: Decimal = Decimal("0")
    minimum_fee: Money = Money(amount_minor=0)
    monthly_fee: Money = Money(amount_minor=0)

    def __post_init__(self) -> None:
        if not Decimal("0") <= self.commission_rate <= Decimal("0.5"):
            raise TariffError("Ставка комиссии должна быть от 0 до 50 %")


@dataclass(frozen=True, slots=True)
class PromoCode:
    code: str
    percent_off: int
    valid_until: date
    max_discount: Money | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.percent_off <= 90:
            raise TariffError("Скидка по промокоду должна быть от 1 до 90 %")

    def is_valid_on(self, day: date) -> bool:
        return day <= self.valid_until


@dataclass(frozen=True, slots=True)
class PriceRequest:
    """Запрос сервиса абонементов (core_booking_service) на расчёт цены заказа."""

    order_id: UUID
    tariff_id: UUID
    user_id: UUID
    promo_code: str | None = None
    is_first_purchase: bool = False


@dataclass(frozen=True, slots=True)
class PricingInput:
    """Всё, что нужно стратегии цены; собирается контекстом из запроса и хранилища."""

    tariff: SubscriptionTariff
    promo: PromoCode | None
    is_first_purchase: bool
    today: date


@dataclass(frozen=True, slots=True)
class PriceBreakdown:
    list_price: Money
    discount: Money
    total: Money


@dataclass(frozen=True, slots=True)
class RevenueSplit:
    gym_share: Money
    platform_commission: Money


@dataclass(frozen=True, slots=True)
class PriceQuote:
    """Итог расчёта: цена для клиента и разбивка суммы между залом и платформой."""

    order_id: UUID
    tariff_id: UUID
    list_price: Money
    discount: Money
    total: Money
    gym_share: Money
    platform_commission: Money
    pricing_strategy: str
    commission_strategy: str

    def to_payment_split(self) -> PaymentSplit:
        """Контракт стыка core_api -> integration_service: готовая разбивка суммы."""
        return PaymentSplit(
            order_id=self.order_id,
            total=self.total,
            gym_share=self.gym_share,
            platform_commission=self.platform_commission,
        )


def percent_of(money: Money, share: Decimal) -> Money:
    """Доля суммы с округлением до копейки по правилу «половина вверх»."""
    value = (Decimal(money.amount_minor) * share).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return Money(amount_minor=int(value))
