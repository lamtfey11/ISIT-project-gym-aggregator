"""Контекст шаблона «Стратегия»: сервис тарификации (компонент core_tariff_service)."""

from __future__ import annotations

from .commission import CommissionStrategy, CommissionStrategyRegistry
from .domain import (
    InvalidPromoCodeError,
    PlacementModel,
    PlacementTerms,
    PlacementTermsMissingError,
    PriceQuote,
    PriceRequest,
    PricingInput,
    SubscriptionTariff,
    TariffNotFoundError,
)
from .ports import Calendar, TariffRepository
from .pricing import PricingStrategySelector


class TariffService:
    """Единственное место в системе, где считаются цена абонемента и доля комиссии.

    Вызывается сервисом абонементов (core_booking_service). Результат уходит в
    сервис интеграций как готовая разбивка суммы (контракт PaymentSplit), поэтому
    integration_service и аналитика комиссию не пересчитывают.
    """

    def __init__(
        self,
        repository: TariffRepository,
        pricing: PricingStrategySelector,
        commissions: CommissionStrategyRegistry,
        calendar: Calendar,
    ) -> None:
        self._repository = repository
        self._pricing = pricing
        self._commissions = commissions
        self._calendar = calendar

    def quote(self, request: PriceRequest) -> PriceQuote:
        tariff = self._repository.get_tariff(request.tariff_id)
        if tariff is None:
            raise TariffNotFoundError(f"Тариф {request.tariff_id} не найден")
        terms = self._repository.get_placement_terms(tariff.gym_id)
        if terms is None:
            raise PlacementTermsMissingError(f"Для зала {tariff.gym_id} не заданы условия размещения")
        promo = None
        if request.promo_code is not None:
            promo = self._repository.find_promo(request.promo_code)
            if promo is None or not promo.is_valid_on(self._calendar.today()):
                raise InvalidPromoCodeError(f"Промокод «{request.promo_code}» недействителен")

        pricing_input = PricingInput(tariff, promo, request.is_first_purchase, self._calendar.today())
        pricing_strategy = self._pricing.select(pricing_input)
        breakdown = pricing_strategy.price(pricing_input)
        commission_strategy = self._commissions.for_model(terms.model)
        split = commission_strategy.split(breakdown.total, terms)

        return PriceQuote(
            order_id=request.order_id,
            tariff_id=tariff.tariff_id,
            list_price=breakdown.list_price,
            discount=breakdown.discount,
            total=breakdown.total,
            gym_share=split.gym_share,
            platform_commission=split.platform_commission,
            pricing_strategy=pricing_strategy.name,
            commission_strategy=commission_strategy.name,
        )

    def save_tariff(self, tariff: SubscriptionTariff) -> None:
        """Тариф абонемента от администратора зала (через core_admin_tariff_api)."""
        if self._repository.get_placement_terms(tariff.gym_id) is None:
            raise PlacementTermsMissingError("Нельзя публиковать тарифы зала без условий размещения")
        self._repository.save_tariff(tariff)

    def set_placement_terms(self, terms: PlacementTerms) -> None:
        """Условия размещения и комиссия от оператора платформы."""
        self._repository.save_placement_terms(terms)

    def use_commission_strategy(self, model: PlacementModel, strategy: CommissionStrategy) -> None:
        """Динамическая подмена алгоритма разбивки для модели размещения."""
        self._commissions.register(model, strategy)
