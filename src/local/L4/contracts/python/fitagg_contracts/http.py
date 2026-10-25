"""HTTP-контракты между контейнерами, на которых сопрягаются компоненты ЛР3."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .events import Direction
from .money import Money


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PaymentSplit(_Frozen):
    """core_api -> integration_service (TCP 8002): платёж с готовой разбивкой суммы.

    Долю комиссии считает только core_tariff_service (core_api); integration_service её не пересчитывает.
    """

    order_id: UUID
    total: Money
    gym_share: Money
    platform_commission: Money

    @model_validator(mode="after")
    def _shares_sum_to_total(self) -> Self:
        if self.gym_share.amount_minor + self.platform_commission.amount_minor != self.total.amount_minor:
            raise ValueError("gym_share + platform_commission должно равняться total")
        return self


class MarkMethod(StrEnum):
    SCAN = "SCAN"
    MANUAL = "MANUAL"


class AdminAccessMarkRequest(_Frozen):
    """admin_web -> api_gateway -> iot_service (TCP 8004): скан QR или ручная отметка администратора."""

    gym_id: UUID
    method: MarkMethod
    direction: Direction
    pass_token: str | None = Field(default=None, min_length=16, max_length=512)
    user_id: UUID | None = None
    note: str | None = Field(default=None, max_length=200)
    idempotency_key: UUID
    client_time: datetime

    @model_validator(mode="after")
    def _identity_matches_method(self) -> Self:
        if self.method is MarkMethod.SCAN and (self.pass_token is None or self.user_id is not None):
            raise ValueError("SCAN требует pass_token и не допускает user_id")
        if self.method is MarkMethod.MANUAL and (self.user_id is None or self.pass_token is not None):
            raise ValueError("MANUAL требует user_id и не допускает pass_token")
        return self


class AccessMarkResult(_Frozen):
    """Ответ iot_service на отметку администратора."""

    decision: Literal["ALLOWED", "DENIED"]
    direction: Direction
    reason: str | None = None
    visit_event_id: UUID | None = None


class RateLimitedError(_Frozen):
    """Тело ответа API-шлюза 429; число секунд дублируется в заголовке Retry-After."""

    error: Literal["rate_limited"]
    retry_after: int = Field(ge=1)
