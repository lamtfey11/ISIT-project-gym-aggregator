"""Стратегии оценки числа посетителей в зале по событиям входа и выхода.

Шаблон «Стратегия»: контекст OccupancyService зависит только от интерфейса
OccupancyStrategy; конкретный алгоритм выбирается для каждого зала по имени
и может быть заменён во время работы без изменения контекста (принцип OCP).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from fitagg_contracts import Direction

from .domain import OccupancyEvent


class OccupancyStrategy(ABC):
    """Интерфейс стратегии: сколько людей находится в зале в момент now."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def estimate(self, events: Sequence[OccupancyEvent], now: datetime) -> int: ...


class ExactBalanceStrategy(OccupancyStrategy):
    """Точный баланс: число входов минус число выходов.

    Подходит залам, где выход фиксируется надёжно (двусторонний турникет).
    Выход без предшествующего входа не уводит счётчик ниже нуля.
    """

    @property
    def name(self) -> str:
        return "exact_balance"

    def estimate(self, events: Sequence[OccupancyEvent], now: datetime) -> int:
        inside = 0
        for event in sorted(events, key=lambda e: e.occurred_at):
            if event.occurred_at > now:
                break
            inside = inside + 1 if event.direction is Direction.IN else max(inside - 1, 0)
        return inside


class VisitTimeoutStrategy(OccupancyStrategy):
    """Баланс по посетителям с коррекцией «забытых выходов».

    Пара вход/выход сопоставляется по посетителю. Если после входа выход не
    зафиксирован дольше max_visit (сбой сканера, выход вместе с другим клиентом),
    посетитель считается ушедшим. Повторный вход без выхода не удваивает счётчик.
    """

    def __init__(self, max_visit: timedelta = timedelta(hours=3)) -> None:
        if max_visit <= timedelta(0):
            raise ValueError("max_visit должен быть положительным")
        self._max_visit = max_visit

    @property
    def name(self) -> str:
        return "visit_timeout"

    def estimate(self, events: Sequence[OccupancyEvent], now: datetime) -> int:
        last_entry: dict[UUID, datetime | None] = {}
        for event in sorted(events, key=lambda e: e.occurred_at):
            if event.occurred_at > now:
                break
            last_entry[event.visitor_id] = event.occurred_at if event.direction is Direction.IN else None
        return sum(
            1
            for entered_at in last_entry.values()
            if entered_at is not None and now - entered_at <= self._max_visit
        )


class SmoothedStrategy(OccupancyStrategy):
    """Сглаживание поверх любой базовой стратегии (композиция стратегий).

    Среднее значение базовой оценки по точкам за последние window минут.
    Индекс не «прыгает» от одиночного входа или выхода, а клиент видит
    устойчивую картину при выборе времени визита.
    """

    def __init__(
        self,
        base: OccupancyStrategy,
        window: timedelta = timedelta(minutes=10),
        step: timedelta = timedelta(minutes=1),
    ) -> None:
        if window <= timedelta(0) or step <= timedelta(0) or step > window:
            raise ValueError("Нужно 0 < step <= window")
        self._base = base
        self._window = window
        self._step = step

    @property
    def name(self) -> str:
        return f"smoothed_{self._base.name}"

    def estimate(self, events: Sequence[OccupancyEvent], now: datetime) -> int:
        samples: list[int] = []
        moment = now - self._window
        while moment <= now:
            samples.append(self._base.estimate(events, moment))
            moment += self._step
        return round(sum(samples) / len(samples))


class OccupancyStrategyRegistry:
    """Реестр стратегий по имени: точка подключения новых алгоритмов без правки контекста."""

    def __init__(self) -> None:
        self._strategies: dict[str, OccupancyStrategy] = {}

    def register(self, strategy: OccupancyStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> OccupancyStrategy:
        try:
            return self._strategies[name]
        except KeyError:
            raise KeyError(f"Стратегия «{name}» не зарегистрирована") from None

    def names(self) -> list[str]:
        return sorted(self._strategies)


def build_default_registry() -> OccupancyStrategyRegistry:
    registry = OccupancyStrategyRegistry()
    exact = ExactBalanceStrategy()
    timeout = VisitTimeoutStrategy()
    for strategy in (exact, timeout, SmoothedStrategy(exact), SmoothedStrategy(timeout)):
        registry.register(strategy)
    return registry
