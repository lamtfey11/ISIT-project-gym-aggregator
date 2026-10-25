# ЛР3 (C4, уровень 4 — Code): интеграция работ команды

Материал для тимлида (роль Enterprise-архитектора по семинару 2): реестр шаблонов, стыки между
компонентами и результаты автоматических проверок. Отчёт по этому файлу не нужен — он для ревью PR.

## 1. Выбор компонентов

Семинар 2: диаграмма кода строится только для нетривиального компонента своего контейнера.
Каждый взял компонент с реальной вариативностью алгоритма — иначе «Стратегия» была бы искусственной.

| Участник | Контейнер | Компонент (глобальный ID) | Язык (по стеку L2/L3) | Нотация L4 |
|---|---|---|---|---|
| Лисов М. (тимлид) | iot_service | iot_occupancy_service (на L3 — occupancy_comp) — индекс загруженности | Python 3.12 | UML Class Diagram |
| Кутенков С. | core_api | core_tariff_service (на L3 — tariff_service) — цена абонемента и комиссия | Python 3.12 | UML Class Diagram |
| Эрендженова М. | etl_service | etl_dq_validator (на L3 — dq_validator) — контроль качества партии | Python 3.12, pandas | UML Class Diagram |
| Дамакальщиков М. | api_gateway | gw_ratelimit (на L3 — ratelimit_comp) — ограничение нагрузки | TypeScript → njs (Nginx) | UML Class Diagram |
| Осипов И. | admin_web | adm_access_controller — контроллер допуска | TypeScript (React/Redux) | UML Class Diagram |

В таблицах ниже компоненты названы глобальными ID из глоссария интеграционного отчёта ЛР2; они же — имена Python/TS-пакетов.

## 2. Реестр шаблонов «Стратегия»

У каждого компонента два независимых семейства стратегий: что считать и как поступить с результатом.
Общих базовых классов стратегий между компонентами нет (независимость шаблонов), общие только контракты.

| Компонент | Контекст | Семейство 1 | Семейство 2 / выбор | Подмена во время работы |
|---|---|---|---|---|
| iot_occupancy_service | `OccupancyService` | `OccupancyStrategy`: exact_balance, visit_timeout, smoothed_* (декоратор) | `OccupancyStrategyRegistry` по `strategy_name` зала | `use_strategy(gym_id, name)`, `set_default_strategy` |
| core_tariff_service | `TariffService` | `PricingStrategy`: standard, promo_code, first_purchase (`PricingStrategySelector` — лучшая цена, без суммирования скидок) | `CommissionStrategy`: percentage, percentage_with_minimum, subscription_plan — по `PlacementModel` | `use_commission_strategy(model, strategy)` |
| etl_dq_validator | `DataQualityValidator` | `QualityRule`: schema, not_null, unique, range, allowed, reference, sum_equals, not_in_future | `RejectionPolicy`: strict_batch, quarantine_rows, audit_only — в профиле витрины | `use_policy(dataset, policy)`, `add_rule(dataset, rule)` |
| gw_ratelimit | `RateLimiter` | `RateLimitAlgorithm`: fixed_window, sliding_window, token_bucket | `ClientKeyStrategy`: ip, bearer_token — в политике маршрута | `useAlgorithm(policy, a)`, `useKeyStrategy(policy, k)` |
| adm_access_controller | `AccessController` | `MarkModeStrategy`: scan, manual | `DeliveryPolicy`: online_only, queue_exits_offline | `setMode(name)`, `useDeliveryPolicy(p)` |

SOLID во всех пяти компонентах одинаково:

* **S** — контекст только выбирает и вызывает стратегию; хранилища, часы, сеть вынесены в порты.
* **O** — новая стратегия добавляется классом без правки контекста (в каждом наборе тестов есть такой тест).
* **L** — все стратегии взаимозаменяемы через один интерфейс, контекст не проверяет конкретный тип.
* **I** — интерфейсы стратегий из 1–3 методов; порты узкие (`Clock`, `TariffRepository`, `AccessApi`…).
* **D** — контекст зависит от абстракций (Protocol / ABC / interface), реализации внедряются в конструктор.

## 3. Стыки между компонентами (конъюнкция сигнатур)

| № | Откуда → куда | Контракт | Где описан | Проверка |
|---|---|---|---|---|
| 1 | core_tariff_service (core_api) → integration_service | `PaymentSplit` (total = gym_share + platform_commission) | `fitagg_contracts.http` | тест `test_to_payment_split_contract`; валидатор модели |
| 2 | integration_service → etl (`payment.succeeded`) → etl_dq_validator | колонки `fact_payments` из `PaymentSucceeded` | `fitagg_contracts.events` | правило `sum_equals` — тот же инвариант, что в п. 1 |
| 3 | iot_service → etl (`access.passed`) → etl_dq_validator | `direction` ∈ Direction, `source` ∈ AccessSource | `fitagg_contracts.events` | `AllowedValuesRule` берёт значения из перечислений контракта |
| 4 | core_api (`gym.updated`) → iot_occupancy_service | `GymUpdated.capacity`, `closing_time` | `fitagg_contracts.events` | `apply_gym_update(GymUpdated)` |
| 5 | iot_service (`access.passed`) → iot_occupancy_service | `AccessPassed` → `OccupancyEvent` | `fitagg_contracts.events` | `OccupancyEvent.from_access_passed` |
| 6 | adm_access_controller → api_gateway → iot_service | `AdminAccessMarkRequest` / `AccessMarkResult` | `contracts.ts` ↔ `fitagg_contracts.http` | `check_contracts.py`: поля + живые образцы из TS проходят pydantic |
| 7 | gw_ratelimit → все клиенты (429) | `RateLimitedError` + `Retry-After` | `contracts.ts` ↔ `fitagg_contracts.http` | `check_contracts.py`; adm_access_controller обрабатывает 429 (`RateLimitedApiError`) |
| 8 | gw_ratelimit → adm_access_controller | политика `access_marks`: token_bucket, всплеск 30 сканов | `policies.ts` | очередь у стойки в час пик не упирается в лимит общего API |

Повтор отметки администратора без связи безопасен только потому, что `iot_service` распознаёт повтор по
`idempotency_key` (контракт п. 6) — это требование к владельцу iot_service, оно в `iot_occupancy_service` не входит,
но закреплено в контракте.

## 4. Изменения на L3, вызванные ЛР3

| Диаграмма | Компонент | Было | Стало |
|---|---|---|---|
| L3_etl_analyst | dq_validator | «Python, Great Expectations» | «Python, pandas»; описание дополнено карантином строк |
| L3_devops_api_gateway | ratelimit_comp | «Nginx / limit_req, limit_conn» | «Nginx / njs (TypeScript), limit_conn»; описание — политики маршрутов |
| L3_2_teamlead (iot_service) | связь occupancy_comp → iot_repo_comp | «Сохраняет и читает историю загруженности» | «Читает журнал входов и выходов, читает и сохраняет параметры зала (вместимость, стратегия), сохраняет историю загруженности» — так работает код |
| L3_2_teamlead (iot_service) | iot_repo_comp | описание без параметров залов | добавлены «параметры залов для расчёта загруженности» |

Все три диаграммы уже исправлены в приложенных L3 (`.puml` + `.png`); состав компонентов и связи с другими контейнерами не менялись.

Идентификаторы в материалах ЛР3 следуют глоссарию компонентов из интеграционного отчёта ЛР2:
в коде, README и диаграммах L4 используются глобальные ID (`iot_occupancy_service`, `core_tariff_service`,
`etl_dq_validator`, `gw_ratelimit`, `adm_access_controller`, порты — `iot_repository`, `iot_cache_client`,
`core_db_repository`), а локальный ID из L3-диаграммы автора указан в заголовке каждой L4 («на L3 — …»),
чтобы от L4 можно было перейти к своей L3. Локальные .puml уровня L3 по-прежнему используют локальные ID.
Новый компонент `adm_access_controller` (добавлен в L3 admin_web при исправлении ЛР2) в глоссарий
не входил; его глобальный ID совпадает с локальным, так как он уже начинается с префикса `adm_`.

## 5. Автоматические проверки (запуск из папки lab3)

| Проверка | Команда | Результат |
|---|---|---|
| Тесты Python | `python -m pytest` в папке компонента | 16 + 14 + 13 — все проходят |
| Тесты TypeScript | `npm test` | 14 + 11 — все проходят |
| Строгая типизация TS | `npm run typecheck` | 0 ошибок (strict, exactOptionalPropertyTypes, noUncheckedIndexedAccess) |
| Аннотации Python | `python integration/check_annotations.py <папки>` | 0 замечаний |
| Контракты TS ↔ Python | `python integration/check_contracts.py` | 3 контракта, 2 перечисления, 3 живых образца — 0 расхождений |
| Диаграммы ↔ код | `python integration/check_diagram_code.py` | в обе стороны: всё с диаграммы есть в коде и все классы кода есть на диаграмме; ID L3 в заголовке; условные обозначения. 5 диаграмм, 138 элементов, 80 методов — 0 расхождений |
| mypy --strict | `mypy && mypy tests demo.py` в папке компонента | 0 ошибок во всех трёх компонентах, в `contracts/` и `integration/`; для etl_dq_validator локально без pandas-stubs (типы pandas = Any), в CI — со stubs |

CI: `.github/workflows/lab3.yml` — три задания (Python, TypeScript, стыки); запрет `skinparam`, `Rel_*`, `Lay_*` в диаграммах сохранён.

## 6. Порядок PR

Каждый открывает свой PR с папкой своего компонента; тимлид делает ревью по чек-листу:
диаграмма совпадает с кодом (CI), стратегия подменяется без правки контекста (тест OCP),
сообщения на стыке — только через `contracts/`. Первым вливается PR с `contracts/` и `integration/`.