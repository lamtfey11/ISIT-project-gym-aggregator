"""Правила качества данных (семейство стратегий № 1: алгоритм проверки).

Каждое правило — отдельная стратегия с общим интерфейсом evaluate(); набор правил
для витрины собирается в профиле, новые правила добавляются без изменения валидатора.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection, Mapping, Sequence
from datetime import timedelta

import pandas as pd

from .domain import RuleResult, Severity, ValidationContext


def _rows(mask: pd.Series[bool]) -> frozenset[int]:
    return frozenset(int(i) for i in mask[mask].index)


class QualityRule(ABC):
    def __init__(self, severity: Severity) -> None:
        self._severity = severity

    @property
    def severity(self) -> Severity:
        return self._severity

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult: ...

    def _result(self, failed: frozenset[int], message: str = "") -> RuleResult:
        return RuleResult(self.name, self._severity, failed, message=message)


class SchemaRule(QualityRule):
    """Полнота состава и типы колонок; нарушение относится ко всей партии."""

    _KINDS: Mapping[str, str] = {"int": "iu", "float": "fiu", "str": "OSU", "datetime": "M", "bool": "b"}

    def __init__(self, columns: Mapping[str, str], severity: Severity = Severity.CRITICAL) -> None:
        super().__init__(severity)
        self._columns = dict(columns)

    @property
    def name(self) -> str:
        return "schema"

    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult:
        problems: list[str] = []
        for column, kind in self._columns.items():
            if column not in frame.columns:
                problems.append(f"нет колонки {column}")
            elif frame[column].dtype.kind not in self._KINDS[kind]:
                problems.append(f"{column}: ожидался {kind}, получен {frame[column].dtype}")
        return RuleResult(self.name, self.severity, frozenset(), bool(problems), "; ".join(problems))


class NotNullRule(QualityRule):
    def __init__(self, columns: Sequence[str], severity: Severity = Severity.CRITICAL) -> None:
        super().__init__(severity)
        self._columns = list(columns)

    @property
    def name(self) -> str:
        return f"not_null[{','.join(self._columns)}]"

    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult:
        return self._result(_rows(frame[self._columns].isna().any(axis=1)))


class UniqueRule(QualityRule):
    """Идентификатор события уникален в партии: повторная доставка не должна удвоить факт."""

    def __init__(self, columns: Sequence[str], severity: Severity = Severity.CRITICAL) -> None:
        super().__init__(severity)
        self._columns = list(columns)

    @property
    def name(self) -> str:
        return f"unique[{','.join(self._columns)}]"

    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult:
        return self._result(_rows(frame.duplicated(subset=self._columns, keep="first")))


class RangeRule(QualityRule):
    def __init__(
        self, column: str, minimum: float | None, maximum: float | None, severity: Severity = Severity.WARNING
    ) -> None:
        super().__init__(severity)
        self._column = column
        self._minimum = minimum
        self._maximum = maximum

    @property
    def name(self) -> str:
        return f"range[{self._column}]"

    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult:
        values = frame[self._column]
        bad = pd.Series(False, index=frame.index)
        if self._minimum is not None:
            bad |= values < self._minimum
        if self._maximum is not None:
            bad |= values > self._maximum
        return self._result(_rows(bad))


class AllowedValuesRule(QualityRule):
    def __init__(self, column: str, allowed: Collection[str], severity: Severity = Severity.CRITICAL) -> None:
        super().__init__(severity)
        self._column = column
        self._allowed = frozenset(allowed)

    @property
    def name(self) -> str:
        return f"allowed[{self._column}]"

    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult:
        return self._result(_rows(~frame[self._column].isin(self._allowed)))


class ReferenceRule(QualityRule):
    """Ссылочная целостность факта со справочником (например, gym_id есть среди залов)."""

    def __init__(self, column: str, reference: str, severity: Severity = Severity.WARNING) -> None:
        super().__init__(severity)
        self._column = column
        self._reference = reference

    @property
    def name(self) -> str:
        return f"reference[{self._column}->{self._reference}]"

    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult:
        known = context.reference_keys.get(self._reference, frozenset())
        return self._result(_rows(~frame[self._column].astype(str).isin(known)))


class SumEqualsRule(QualityRule):
    """Бизнес-правило выплат: доля зала + комиссия = сумма платежа (копейка в копейку)."""

    def __init__(self, parts: Sequence[str], total: str, severity: Severity = Severity.CRITICAL) -> None:
        super().__init__(severity)
        self._parts = list(parts)
        self._total = total

    @property
    def name(self) -> str:
        return f"sum_equals[{'+'.join(self._parts)}={self._total}]"

    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult:
        return self._result(_rows(frame[self._parts].sum(axis=1) != frame[self._total]))


class NotInFutureRule(QualityRule):
    """Время события не позже момента проверки (с допуском на рассинхрон часов)."""

    def __init__(
        self, column: str, tolerance: timedelta = timedelta(minutes=5), severity: Severity = Severity.WARNING
    ) -> None:
        super().__init__(severity)
        self._column = column
        self._tolerance = tolerance

    @property
    def name(self) -> str:
        return f"not_in_future[{self._column}]"

    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult:
        limit = pd.Timestamp(context.now + self._tolerance)
        return self._result(_rows(frame[self._column] > limit))
