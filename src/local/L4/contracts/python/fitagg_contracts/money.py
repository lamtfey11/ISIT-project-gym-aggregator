"""Денежная сумма в копейках: целые числа исключают ошибки округления float."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Money(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    amount_minor: int = Field(ge=0, description="Сумма в копейках")
    currency: Literal["RUB"] = "RUB"

    def __add__(self, other: Money) -> Money:
        return Money(amount_minor=self.amount_minor + other.amount_minor, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        return Money(amount_minor=self.amount_minor - other.amount_minor, currency=self.currency)

    @classmethod
    def rub(cls, rubles: int, kopecks: int = 0) -> Money:
        return cls(amount_minor=rubles * 100 + kopecks)
