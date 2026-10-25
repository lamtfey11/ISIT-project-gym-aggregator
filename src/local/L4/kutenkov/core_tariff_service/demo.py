"""Демонстрация: один и тот же заказ при разных стратегиях цены и комиссии.

Запуск из папки компонента: python demo.py
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parents[1] / "contracts" / "python")]

from fitagg_contracts import Money  

from core_tariff_service import (  
    CommissionStrategyRegistry,
    PlacementModel,
    PlacementTerms,
    PriceQuote,
    PriceRequest,
    PromoCode,
    SubscriptionTariff,
    TariffService,
    build_default_selector,
)
from core_tariff_service.adapters_memory import FixedCalendar, InMemoryTariffRepository 


def rub(money: Money) -> str:
    return f"{money.amount_minor / 100:>9.2f} ₽"


def show(label: str, quote: PriceQuote) -> None:
    print(
        f"{label:<34} цена {rub(quote.total)} | залу {rub(quote.gym_share)} | платформе "
        f"{rub(quote.platform_commission)} | {quote.pricing_strategy} + {quote.commission_strategy}"
    )


def main() -> None:
    repo = InMemoryTariffRepository()
    service = TariffService(repo, build_default_selector(), CommissionStrategyRegistry(), FixedCalendar(date(2026, 10, 24)))
    gym_id = uuid4()
    service.set_placement_terms(PlacementTerms(gym_id, PlacementModel.COMMISSION, commission_rate=Decimal("0.15")))
    tariff = SubscriptionTariff(uuid4(), gym_id, "Месяц безлимит", Money.rub(3000), 30)
    service.save_tariff(tariff)
    repo.add_promo(PromoCode("FIT20", 20, date(2026, 12, 31), max_discount=Money.rub(500)))

    def order(promo: str | None = None, first: bool = False) -> PriceRequest:
        return PriceRequest(uuid4(), tariff.tariff_id, uuid4(), promo, first)

    show("Без скидки, комиссия 15 %", service.quote(order()))
    show("Промокод FIT20", service.quote(order("FIT20")))
    show("Первая покупка", service.quote(order(first=True)))

    service.set_placement_terms(
        PlacementTerms(gym_id, PlacementModel.COMMISSION_WITH_MINIMUM, Decimal("0.05"), minimum_fee=Money.rub(200))
    )
    show("Комиссия 5 %, но не меньше 200 ₽", service.quote(order()))

    service.set_placement_terms(PlacementTerms(gym_id, PlacementModel.SUBSCRIPTION, monthly_fee=Money.rub(9900)))
    show("Зал на подписке", service.quote(order()))
    print("Контракт для integration_service:", service.quote(order()).to_payment_split().model_dump_json())


if __name__ == "__main__":
    main()
