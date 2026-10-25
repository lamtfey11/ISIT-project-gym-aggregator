"""Модель предметной области модуля контроля качества данных (компонент etl_dq_validator)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

import pandas as pd


class Severity(StrEnum):
    """CRITICAL — контрольное правило: нарушение отбраковывает партию целиком.
    WARNING — предупреждающее правило: судьбу строк решает политика отбраковки."""

    CRITICAL = "CRITICAL"
    WARNING = "WARNING"


class BatchStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    ACCEPTED_WITH_QUARANTINE = "ACCEPTED_WITH_QUARANTINE"
    REJECTED = "REJECTED"


class UnknownDatasetError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Batch:
    """Партия, подготовленная модулем преобразования (etl_transform_engine)."""

    batch_id: UUID
    dataset: str
    frame: pd.DataFrame


@dataclass(frozen=True, slots=True)
class ValidationContext:
    """Внешние данные для правил: момент проверки и ключи справочников из СУБД."""

    now: datetime
    reference_keys: Mapping[str, frozenset[str]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuleResult:
    rule_name: str
    severity: Severity
    failed_rows: frozenset[int]
    batch_level: bool = False
    message: str = ""

    @property
    def passed(self) -> bool:
        return not self.failed_rows and not self.batch_level


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    status: BatchStatus
    accepted_rows: frozenset[int]
    quarantined_rows: frozenset[int]
    reason: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Итог проверки: что передаётся загрузчику витрин (etl_mart_loader) и пишется в журнал загрузок."""

    batch_id: UUID
    dataset: str
    status: BatchStatus
    policy_name: str
    checked_at: datetime
    total_rows: int
    accepted: pd.DataFrame
    quarantined: pd.DataFrame
    results: tuple[RuleResult, ...]
    reason: str

    @property
    def failed_rules(self) -> list[str]:
        return [r.rule_name for r in self.results if not r.passed]
