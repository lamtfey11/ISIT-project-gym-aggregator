# etl_dq_validator — модуль контроля качества данных (ЛР3, C4 L4)

Контейнер: `etl_service` (Python 3.12 / Apache Airflow, pandas). Компонент: `etl_dq_validator` (на L3 — `dq_validator`). Автор: Эрендженова М.

Получает от модуля преобразования (`etl_transform_engine`) подготовленную партию в виде `pandas.DataFrame`,
проверяет полноту, типы и бизнес-правила и передаёт загрузчику витрин (`etl_mart_loader`) только допущенные
строки вместе с отчётом. В хранилища сам не пишет — так и на диаграмме L3.

## Шаблон «Стратегия» (два семейства)

| Роль | Что проверить | Что делать с партией |
|---|---|---|
| Контекст | `DataQualityValidator` | `DataQualityValidator` |
| Интерфейс | `QualityRule.evaluate(frame, context) -> RuleResult` | `RejectionPolicy.decide(rows, results) -> PolicyDecision` |
| Стратегии | `SchemaRule`, `NotNullRule`, `UniqueRule`, `RangeRule`, `AllowedValuesRule`, `ReferenceRule`, `SumEqualsRule`, `NotInFutureRule` | `StrictBatchPolicy`, `QuarantineRowsPolicy`, `AuditOnlyPolicy` |
| Выбор | набор правил в профиле витрины, `add_rule()` | политика в профиле витрины, подмена `use_policy()` |

Профили по умолчанию (`build_default_registry`):

* `fact_payments` (из `payment.succeeded`) — `strict_batch`: доля зала + комиссия = сумма платежа,
  уникальный `event_id`, зал есть в справочнике. Любое нарушение отбраковывает партию целиком,
  иначе разойдётся сверка выплат с 1С.
* `fact_visits` (из `access.passed`) — `quarantine_rows`: направление только `IN/OUT`, источник —
  турникет, сканер администратора или ручная отметка; строки с неизвестным залом или временем
  «из будущего» уходят в карантин, если их не больше 5 % партии.

## Изменение на L3

В L3 у компонента указана технология «Python, Great Expectations». Правила реализованы собственным
интерфейсом `QualityRule` поверх pandas: так шаблон «Стратегия» виден в коде явно и нет тяжёлой
зависимости. В L3 нужно поменять строку технологии на **«Python, pandas»**.

## Запуск

```bash
pip install -e ".[dev]"
python demo.py
python -m pytest            # или: PYTHONPATH=src:../../contracts/python python -m unittest discover -s tests
mypy                        # строгий режим, нужны pandas-stubs
python ../../integration/check_annotations.py src tests
```

## Файлы

* `diagram/L4_etl_dq_validator.puml` — UML-диаграмма классов (C4 L4)
* `src/etl_dq_validator/` — код компонента
* `tests/` — 13 тестов, в том числе подмена политики во время работы и новое правило без изменения валидатора (OCP)
