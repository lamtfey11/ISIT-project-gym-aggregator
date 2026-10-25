"""Общие контракты на стыках контейнеров ИС «Агрегатор фитнес-клубов».

Пакет ведёт тимлид (зона Enterprise-архитектора). Компоненты ЛР3 импортируют отсюда
типы стыков, чтобы сигнатуры на границах контейнеров совпадали по построению.
"""

from .events import (
    AccessPassed,
    AccessSource,
    Direction,
    EventEnvelope,
    GymUpdated,
    OrderCreated,
    PaymentFailed,
    PaymentRefunded,
    PaymentSucceeded,
    ReportReady,
    SubscriptionActivated,
    SubscriptionExpiring,
)
from .http import AccessMarkResult, AdminAccessMarkRequest, MarkMethod, PaymentSplit, RateLimitedError
from .money import Money

__all__ = [
    "AccessMarkResult",
    "AccessPassed",
    "AccessSource",
    "AdminAccessMarkRequest",
    "Direction",
    "EventEnvelope",
    "GymUpdated",
    "MarkMethod",
    "Money",
    "OrderCreated",
    "PaymentFailed",
    "PaymentRefunded",
    "PaymentSplit",
    "PaymentSucceeded",
    "RateLimitedError",
    "ReportReady",
    "SubscriptionActivated",
    "SubscriptionExpiring",
]
