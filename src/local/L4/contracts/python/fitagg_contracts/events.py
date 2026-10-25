"""Доменные события, которыми сервисы обмениваются через RabbitMQ.

Каталог событий зафиксирован в отчёте ЛР1 (таблица «Каталог доменных событий»):
у каждого события один издатель, каждый подписчик читает его из собственной очереди.
Все события упакованы в единый JSON-конверт EventEnvelope.
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .money import Money


class Direction(StrEnum):
    """Направление прохода. Посещение всегда учитывается парой IN и OUT."""

    IN = "IN"
    OUT = "OUT"


class AccessSource(StrEnum):
    """Источник события прохода (решение команды: турникет, сканер администратора, ручная отметка)."""

    TURNSTILE = "TURNSTILE"
    ADMIN_SCANNER = "ADMIN_SCANNER"
    MANUAL = "MANUAL"


EventType = Literal[
    "order.created",
    "payment.succeeded",
    "payment.failed",
    "payment.refunded",
    "subscription.activated",
    "subscription.expiring",
    "gym.updated",
    "access.passed",
    "report.ready",
]

Producer = Literal["core_api", "integration_service", "iot_service", "analytics_service"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EventEnvelope(_Frozen):
    """Единый конверт: по event_id подписчик распознаёт повтор события."""

    event_id: UUID
    event_type: EventType
    producer: Producer
    occurred_at: datetime
    version: int = Field(default=1, ge=1)
    payload: dict[str, object]


class OrderCreated(_Frozen):
    """order.created, издатель core_api."""

    order_id: UUID
    user_id: UUID
    gym_id: UUID
    tariff_id: UUID
    total: Money


class PaymentSucceeded(_Frozen):
    """payment.succeeded, издатель integration_service."""

    payment_id: UUID
    order_id: UUID
    total: Money
    gym_share: Money
    platform_commission: Money


class PaymentFailed(_Frozen):
    """payment.failed, издатель integration_service."""

    payment_id: UUID
    order_id: UUID
    reason: str


class PaymentRefunded(_Frozen):
    """payment.refunded, издатель integration_service."""

    payment_id: UUID
    order_id: UUID
    refunded: Money


class SubscriptionActivated(_Frozen):
    """subscription.activated, издатель core_api: оплаченный абонемент, можно выдавать пропуск."""

    subscription_id: UUID
    order_id: UUID
    user_id: UUID
    gym_id: UUID
    valid_from: date
    valid_to: date
    visits_total: int | None = Field(default=None, ge=1)


class SubscriptionExpiring(_Frozen):
    """subscription.expiring, издатель core_api."""

    subscription_id: UUID
    user_id: UUID
    gym_id: UUID
    valid_to: date


class GymUpdated(_Frozen):
    """gym.updated, издатель core_api. Вместимость нужна сервису загруженности."""

    gym_id: UUID
    capacity: int = Field(ge=1)
    closing_time: time | None = None


class AccessPassed(_Frozen):
    """access.passed, издатель iot_service: вход или выход из одного из трёх источников."""

    visit_event_id: UUID
    gym_id: UUID
    user_id: UUID
    subscription_id: UUID | None
    direction: Direction
    source: AccessSource
    occurred_at: datetime


class ReportReady(_Frozen):
    """report.ready, издатель analytics_service."""

    report_id: UUID
    recipient_user_id: UUID
    file_format: Literal["XLSX", "CSV"]
    download_url: str


PAYLOAD_BY_TYPE: dict[str, type[_Frozen]] = {
    "order.created": OrderCreated,
    "payment.succeeded": PaymentSucceeded,
    "payment.failed": PaymentFailed,
    "payment.refunded": PaymentRefunded,
    "subscription.activated": SubscriptionActivated,
    "subscription.expiring": SubscriptionExpiring,
    "gym.updated": GymUpdated,
    "access.passed": AccessPassed,
    "report.ready": ReportReady,
}
