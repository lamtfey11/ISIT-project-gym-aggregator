"""Реализации портов в памяти для тестов и демо; в системе их заменяет core_db_repository."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from .domain import PlacementTerms, PromoCode, SubscriptionTariff


class InMemoryTariffRepository:
    def __init__(self) -> None:
        self._tariffs: dict[UUID, SubscriptionTariff] = {}
        self._terms: dict[UUID, PlacementTerms] = {}
        self._promos: dict[str, PromoCode] = {}

    def get_tariff(self, tariff_id: UUID) -> SubscriptionTariff | None:
        return self._tariffs.get(tariff_id)

    def save_tariff(self, tariff: SubscriptionTariff) -> None:
        self._tariffs[tariff.tariff_id] = tariff

    def get_placement_terms(self, gym_id: UUID) -> PlacementTerms | None:
        return self._terms.get(gym_id)

    def save_placement_terms(self, terms: PlacementTerms) -> None:
        self._terms[terms.gym_id] = terms

    def find_promo(self, code: str) -> PromoCode | None:
        return self._promos.get(code.upper())

    def add_promo(self, promo: PromoCode) -> None:
        self._promos[promo.code.upper()] = promo


class FixedCalendar:
    def __init__(self, day: date) -> None:
        self._day = day

    def today(self) -> date:
        return self._day
