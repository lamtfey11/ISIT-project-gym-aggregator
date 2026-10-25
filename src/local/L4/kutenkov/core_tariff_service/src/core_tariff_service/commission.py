"""Стратегии разбивки суммы между залом и платформой (семейство стратегий № 2).
задаётся условиями размещения зала и подменяется без изменения TariffService.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from fitagg_contracts import Money

from .domain import PlacementModel, PlacementTerms, RevenueSplit, percent_of


class CommissionStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def split(self, total: Money, terms: PlacementTerms) -> RevenueSplit: ...


class PercentageCommission(CommissionStrategy):
    """Платформа получает процент с каждой продажи."""

    @property
    def name(self) -> str:
        return "percentage"

    def split(self, total: Money, terms: PlacementTerms) -> RevenueSplit:
        commission = percent_of(total, terms.commission_rate)
        return RevenueSplit(gym_share=total - commission, platform_commission=commission)


class MinimumFeeCommission(CommissionStrategy):
    """Процент, но не меньше минимального сбора (для дешёвых разовых посещений)."""

    @property
    def name(self) -> str:
        return "percentage_with_minimum"

    def split(self, total: Money, terms: PlacementTerms) -> RevenueSplit:
        by_rate = percent_of(total, terms.commission_rate).amount_minor
        commission = min(max(by_rate, terms.minimum_fee.amount_minor), total.amount_minor)
        fee = Money(amount_minor=commission)
        return RevenueSplit(gym_share=total - fee, platform_commission=fee)


class SubscriptionPlanCommission(CommissionStrategy):
    """Зал платит ежемесячную подписку, поэтому с продажи комиссия не удерживается."""

    @property
    def name(self) -> str:
        return "subscription_plan"

    def split(self, total: Money, terms: PlacementTerms) -> RevenueSplit:
        return RevenueSplit(gym_share=total, platform_commission=Money(amount_minor=0))


class CommissionStrategyRegistry:
    """Соответствие модели размещения и стратегии разбивки; подмена во время работы."""

    def __init__(self) -> None:
        self._by_model: dict[PlacementModel, CommissionStrategy] = {
            PlacementModel.COMMISSION: PercentageCommission(),
            PlacementModel.COMMISSION_WITH_MINIMUM: MinimumFeeCommission(),
            PlacementModel.SUBSCRIPTION: SubscriptionPlanCommission(),
        }

    def register(self, model: PlacementModel, strategy: CommissionStrategy) -> None:
        self._by_model[model] = strategy

    def for_model(self, model: PlacementModel) -> CommissionStrategy:
        return self._by_model[model]
