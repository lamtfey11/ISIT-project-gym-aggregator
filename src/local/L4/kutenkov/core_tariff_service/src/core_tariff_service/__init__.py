"""Компонент core_tariff_service «Сервис тарификации» контейнера core_api (C4 L4)."""

from .commission import (
    CommissionStrategy,
    CommissionStrategyRegistry,
    MinimumFeeCommission,
    PercentageCommission,
    SubscriptionPlanCommission,
)
from .domain import (
    InvalidPromoCodeError,
    PlacementModel,
    PlacementTerms,
    PlacementTermsMissingError,
    PriceQuote,
    PriceRequest,
    PromoCode,
    SubscriptionTariff,
    TariffError,
    TariffNotFoundError,
)
from .pricing import FirstPurchasePricing, PricingStrategy, PricingStrategySelector, PromoCodePricing, StandardPricing
from .service import TariffService


def build_default_selector() -> PricingStrategySelector:
    return PricingStrategySelector([StandardPricing(), PromoCodePricing(), FirstPurchasePricing()])


__all__ = [
    "CommissionStrategy",
    "CommissionStrategyRegistry",
    "FirstPurchasePricing",
    "InvalidPromoCodeError",
    "MinimumFeeCommission",
    "PercentageCommission",
    "PlacementModel",
    "PlacementTerms",
    "PlacementTermsMissingError",
    "PriceQuote",
    "PriceRequest",
    "PricingStrategy",
    "PricingStrategySelector",
    "PromoCode",
    "PromoCodePricing",
    "StandardPricing",
    "SubscriptionPlanCommission",
    "SubscriptionTariff",
    "TariffError",
    "TariffNotFoundError",
    "TariffService",
    "build_default_selector",
]
