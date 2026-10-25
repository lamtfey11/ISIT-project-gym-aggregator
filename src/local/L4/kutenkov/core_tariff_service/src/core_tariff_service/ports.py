"""Порты компонента: хранилище реализует core_db_repository (SQLAlchemy, PostgreSQL)."""

from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from .domain import PlacementTerms, PromoCode, SubscriptionTariff


class TariffRepository(Protocol):
    def get_tariff(self, tariff_id: UUID) -> SubscriptionTariff | None: ...

    def save_tariff(self, tariff: SubscriptionTariff) -> None: ...

    def get_placement_terms(self, gym_id: UUID) -> PlacementTerms | None: ...

    def save_placement_terms(self, terms: PlacementTerms) -> None: ...

    def find_promo(self, code: str) -> PromoCode | None: ...


class Calendar(Protocol):
    def today(self) -> date: ...
