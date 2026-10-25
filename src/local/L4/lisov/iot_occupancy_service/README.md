# iot_occupancy_service — сервис индекса загруженности (ЛР3, C4 L4)

Контейнер: `iot_service` (Python 3.12 / FastAPI, asyncio, aiomqtt). Компонент: `iot_occupancy_service` (на L3 — `occupancy_comp`). Автор: Лисов М. И.

Компонент считает, сколько людей сейчас в зале, по парам событий «вход / выход» из трёх источников
(турникет, сканер администратора, ручная отметка) и переводит это в индекс загруженности от 1 до 10.

## Шаблон «Стратегия»

| Роль | Класс |
|---|---|
| Контекст | `OccupancyService` |
| Интерфейс стратегии | `OccupancyStrategy.estimate(events, now) -> int` |
| Стратегии | `ExactBalanceStrategy`, `VisitTimeoutStrategy`, `SmoothedStrategy` (оборачивает любую другую) |
| Выбор стратегии | по `strategy_name` в настройках зала, подмена во время работы: `use_strategy()` |

* `exact_balance` — входы минус выходы. Точно, если выходы фиксируются всегда.
* `visit_timeout` — пары по посетителю; вход без выхода дольше 3 ч считается ушедшим, двойной вход не удваивает счётчик.
* `smoothed_*` — среднее за 10 минут поверх базовой стратегии, чтобы индекс не «прыгал».
* По умолчанию `smoothed_visit_timeout`: устойчив и к забытым выходам, и к одиночным всплескам.

## Запуск

```bash
pip install -e ".[dev]"            # или: pip install pydantic mypy pytest
python demo.py                      # одни и те же события, четыре стратегии
python -m pytest                    # или: PYTHONPATH=src:../../contracts/python python -m unittest discover -s tests
mypy                                # строгий режим включён в pyproject.toml
python ../../integration/check_annotations.py src tests
```

## Файлы

* `diagram/L4_iot_occupancy_service.puml` — UML-диаграмма классов (C4 L4)
* `src/iot_occupancy_service/` — код компонента; `adapters_memory.py` — реализации портов для тестов и демо
* `tests/` — 16 тестов, в том числе подмена стратегии без изменения контекста (OCP)
