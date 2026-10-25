"""Стратегии цены абонемента для клиента (семейство стратегий № 1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from fitagg_contracts import Money

from .domain import InvalidPromoCodeError, PriceBreakdown, PricingInput, percent_of


class PricingStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def is_applicable(self, pricing_input: PricingInput) -> bool: ...

    @abstractmethod
    def price(self, pricing_input: PricingInput) -> PriceBreakdown: ...


class StandardPricing(PricingStrategy):
    """Цена тарифа без скидки: применима всегда."""

    @property
    def name(self) -> str:
        return "standard"

    def is_applicable(self, pricing_input: PricingInput) -> bool:
        return True

    def price(self, pricing_input: PricingInput) -> PriceBreakdown:
        list_price = pricing_input.tariff.list_price
        return PriceBreakdown(list_price, Money(amount_minor=0), list_price)


class PromoCodePricing(PricingStrategy):
    """Скидка по действующему промокоду, ограниченная max_discount."""

    @property
    def name(self) -> str:
        return "promo_code"

    def is_applicable(self, pricing_input: PricingInput) -> bool:
        promo = pricing_input.promo
        return promo is not None and promo.is_valid_on(pricing_input.today)

    def price(self, pricing_input: PricingInput) -> PriceBreakdown:
        promo = pricing_input.promo
        if promo is None or not promo.is_valid_on(pricing_input.today):
            raise InvalidPromoCodeError("Промокод отсутствует или истёк")
        list_price = pricing_input.tariff.list_price
        discount = percent_of(list_price, Decimal(promo.percent_off) / 100)
        if promo.max_discount is not None and discount.amount_minor > promo.max_discount.amount_minor:
            discount = promo.max_discount
        return PriceBreakdown(list_price, discount, list_price - discount)


class FirstPurchasePricing(PricingStrategy):
    """Приветственная скидка на первую покупку: снижает порог для нового клиента."""

    def __init__(self, percent_off: int = 10) -> None:
        if not 1 <= percent_off <= 50:
            raise ValueError("Приветственная скидка должна быть от 1 до 50 %")
        self._percent_off = percent_off

    @property
    def name(self) -> str:
        return "first_purchase"

    def is_applicable(self, pricing_input: PricingInput) -> bool:
        return pricing_input.is_first_purchase

    def price(self, pricing_input: PricingInput) -> PriceBreakdown:
        list_price = pricing_input.tariff.list_price
        discount = percent_of(list_price, Decimal(self._percent_off) / 100)
        return PriceBreakdown(list_price, discount, list_price - discount)


class PricingStrategySelector:
    """Выбирает одну стратегию цены: скидки не суммируются, клиенту даётся лучшая."""

    def __init__(self, strategies: list[PricingStrategy]) -> None:
        if not any(isinstance(s, StandardPricing) for s in strategies):
            raise ValueError("Среди стратегий должна быть StandardPricing как вариант по умолчанию")
        self._strategies = list(strategies)

    def add(self, strategy: PricingStrategy) -> None:
        self._strategies.append(strategy)

    def select(self, pricing_input: PricingInput) -> PricingStrategy:
        applicable = [s for s in self._strategies if s.is_applicable(pricing_input)]
        return min(applicable, key=lambda s: s.price(pricing_input).total.amount_minor)
