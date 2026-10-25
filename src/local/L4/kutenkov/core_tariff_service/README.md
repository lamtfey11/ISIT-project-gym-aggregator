# core_tariff_service — сервис тарификации (ЛР3, C4 L4)

Контейнер: `core_api` (Python 3.12 / FastAPI). Компонент: `core_tariff_service` «Сервис тарификации» (на L3 — `tariff_service`). Автор: Кутенков С.

Компонент считает цену абонемента для клиента и делит оплаченную сумму между залом и платформой.
Это единственное место в системе, где считается комиссия: результат уходит в `integration_service`
готовым контрактом `PaymentSplit`, и ни интеграции, ни аналитика её не пересчитывают.

## Шаблон «Стратегия» (два семейства)

| Роль | Цена для клиента | Разбивка суммы |
|---|---|---|
| Контекст | `TariffService` | `TariffService` |
| Интерфейс | `PricingStrategy.price(pricing_input)` | `CommissionStrategy.split(total, terms)` |
| Стратегии | `StandardPricing`, `PromoCodePricing`, `FirstPurchasePricing` | `PercentageCommission`, `MinimumFeeCommission`, `SubscriptionPlanCommission` |
| Выбор | `PricingStrategySelector`: из применимых — с наименьшей ценой, скидки не суммируются | `CommissionStrategyRegistry`: по `PlacementModel` зала, подмена через `use_commission_strategy()` |

Разделение понятий: **тариф абонемента** задаёт администратор зала (`save_tariff`),
**условия размещения и комиссию** — оператор платформы (`set_placement_terms`).
Модель «комиссия или подписка» (S4) — это просто разные стратегии разбивки.

Деньги хранятся в копейках (`Money.amount_minor: int`), доля считается в `Decimal` с округлением
«половина вверх», доля зала = итог − комиссия, поэтому сумма частей всегда равна итогу
(это же проверяет валидатор `PaymentSplit`).

## Запуск

```bash
pip install -e ".[dev]"
python demo.py
python -m pytest            # или: PYTHONPATH=src:../../contracts/python python -m unittest discover -s tests
mypy                        # строгий режим в pyproject.toml
python ../../integration/check_annotations.py src tests
```

## Файлы

* `diagram/L4_core_tariff_service.puml` — UML-диаграмма классов (C4 L4)
* `src/core_tariff_service/` — код; `adapters_memory.py` — реализации портов для тестов и демо
  (в системе `TariffRepository` реализует `core_db_repository`)
* `tests/` — 14 тестов, в том числе подмена стратегии без изменения контекста (OCP) и контракт `PaymentSplit`
