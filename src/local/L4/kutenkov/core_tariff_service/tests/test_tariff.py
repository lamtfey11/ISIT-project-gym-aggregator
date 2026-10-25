"""Тесты core_tariff_service. Запуск: python -m unittest (или pytest)."""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from fitagg_contracts import Money, PaymentSplit

from core_tariff_service import (
    CommissionStrategy,
    CommissionStrategyRegistry,
    InvalidPromoCodeError,
    PlacementModel,
    PlacementTerms,
    PlacementTermsMissingError,
    PriceRequest,
    PromoCode,
    SubscriptionTariff,
    TariffError,
    TariffNotFoundError,
    TariffService,
    build_default_selector,
)
from core_tariff_service.adapters_memory import FixedCalendar, InMemoryTariffRepository
from core_tariff_service.domain import PlacementTerms as _Terms
from core_tariff_service.domain import RevenueSplit
from core_tariff_service.pricing import PricingStrategySelector, PromoCodePricing, StandardPricing

TODAY = date(2026, 10, 24)


class FlatFeeCommission(CommissionStrategy):
    """Новая стратегия, добавленная без изменения TariffService (проверка OCP)."""

    @property
    def name(self) -> str:
        return "flat_fee"

    def split(self, total: Money, terms: _Terms) -> RevenueSplit:
        fee = Money(amount_minor=min(5000, total.amount_minor))
        return RevenueSplit(gym_share=total - fee, platform_commission=fee)


class TariffServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryTariffRepository()
        self.gym_id: UUID = uuid4()
        self.service = TariffService(
            self.repo, build_default_selector(), CommissionStrategyRegistry(), FixedCalendar(TODAY)
        )
        self.service.set_placement_terms(
            PlacementTerms(self.gym_id, PlacementModel.COMMISSION, commission_rate=Decimal("0.15"))
        )
        self.tariff = SubscriptionTariff(uuid4(), self.gym_id, "Месяц безлимит", Money.rub(3000), 30)
        self.service.save_tariff(self.tariff)

    def request(self, promo: str | None = None, first: bool = False) -> PriceRequest:
        return PriceRequest(uuid4(), self.tariff.tariff_id, uuid4(), promo, first)

    def test_standard_price_and_percentage_commission(self) -> None:
        quote = self.service.quote(self.request())
        self.assertEqual(quote.total, Money.rub(3000))
        self.assertEqual(quote.platform_commission, Money.rub(450))
        self.assertEqual(quote.gym_share, Money.rub(2550))
        self.assertEqual((quote.pricing_strategy, quote.commission_strategy), ("standard", "percentage"))

    def test_promo_code_discount_with_cap(self) -> None:
        self.repo.add_promo(PromoCode("FIT20", 20, TODAY, max_discount=Money.rub(500)))
        quote = self.service.quote(self.request("fit20"))
        self.assertEqual(quote.discount, Money.rub(500))
        self.assertEqual(quote.total, Money.rub(2500))
        self.assertEqual(quote.pricing_strategy, "promo_code")

    def test_best_discount_chosen_not_stacked(self) -> None:
        self.repo.add_promo(PromoCode("SMALL5", 5, TODAY))
        quote = self.service.quote(self.request("SMALL5", first=True))
        self.assertEqual(quote.pricing_strategy, "first_purchase")
        self.assertEqual(quote.total, Money.rub(2700))

    def test_expired_promo_rejected(self) -> None:
        self.repo.add_promo(PromoCode("OLD", 30, date(2026, 1, 1)))
        with self.assertRaises(InvalidPromoCodeError):
            self.service.quote(self.request("OLD"))

    def test_unknown_promo_rejected(self) -> None:
        with self.assertRaises(InvalidPromoCodeError):
            self.service.quote(self.request("NOPE"))

    def test_minimum_fee_commission(self) -> None:
        self.service.set_placement_terms(
            PlacementTerms(
                self.gym_id,
                PlacementModel.COMMISSION_WITH_MINIMUM,
                commission_rate=Decimal("0.10"),
                minimum_fee=Money.rub(100),
            )
        )
        cheap = SubscriptionTariff(uuid4(), self.gym_id, "Разовое", Money.rub(500), 1, visits_total=1)
        self.service.save_tariff(cheap)
        quote = self.service.quote(PriceRequest(uuid4(), cheap.tariff_id, uuid4()))
        self.assertEqual(quote.platform_commission, Money.rub(100))
        self.assertEqual(quote.commission_strategy, "percentage_with_minimum")

    def test_subscription_plan_no_commission(self) -> None:
        self.service.set_placement_terms(
            PlacementTerms(self.gym_id, PlacementModel.SUBSCRIPTION, monthly_fee=Money.rub(9900))
        )
        quote = self.service.quote(self.request())
        self.assertEqual(quote.platform_commission, Money(amount_minor=0))
        self.assertEqual(quote.gym_share, quote.total)

    def test_runtime_strategy_swap_ocp(self) -> None:
        self.service.use_commission_strategy(PlacementModel.COMMISSION, FlatFeeCommission())
        quote = self.service.quote(self.request())
        self.assertEqual(quote.commission_strategy, "flat_fee")
        self.assertEqual(quote.platform_commission, Money.rub(50))

    def test_rounding_half_up_and_split_sums_to_total(self) -> None:
        self.service.set_placement_terms(
            PlacementTerms(self.gym_id, PlacementModel.COMMISSION, commission_rate=Decimal("0.125"))
        )
        odd = SubscriptionTariff(uuid4(), self.gym_id, "Неделя", Money(amount_minor=99999), 7)
        self.service.save_tariff(odd)
        quote = self.service.quote(PriceRequest(uuid4(), odd.tariff_id, uuid4()))
        self.assertEqual(quote.platform_commission.amount_minor, 12500)  # 12499.875 -> 12500
        self.assertEqual(
            quote.gym_share.amount_minor + quote.platform_commission.amount_minor, quote.total.amount_minor
        )

    def test_to_payment_split_contract(self) -> None:
        quote = self.service.quote(self.request())
        split = quote.to_payment_split()
        self.assertIsInstance(split, PaymentSplit)
        self.assertEqual(split.order_id, quote.order_id)
        self.assertEqual(split.total, quote.total)

    def test_unknown_tariff(self) -> None:
        with self.assertRaises(TariffNotFoundError):
            self.service.quote(PriceRequest(uuid4(), uuid4(), uuid4()))

    def test_tariff_requires_placement_terms(self) -> None:
        other_gym = SubscriptionTariff(uuid4(), uuid4(), "Месяц", Money.rub(2000), 30)
        with self.assertRaises(PlacementTermsMissingError):
            self.service.save_tariff(other_gym)

    def test_domain_validation(self) -> None:
        with self.assertRaises(TariffError):
            SubscriptionTariff(uuid4(), self.gym_id, "Бесплатно", Money(amount_minor=0), 30)
        with self.assertRaises(TariffError):
            PlacementTerms(self.gym_id, PlacementModel.COMMISSION, commission_rate=Decimal("0.9"))
        with self.assertRaises(TariffError):
            PromoCode("X", 95, TODAY)

    def test_selector_requires_standard(self) -> None:
        with self.assertRaises(ValueError):
            PricingStrategySelector([PromoCodePricing()])
        PricingStrategySelector([StandardPricing()])


if __name__ == "__main__":
    unittest.main()
