"""Политики отбраковки (семейство стратегий № 2: что делать с партией по итогам проверок)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .domain import BatchStatus, PolicyDecision, RuleResult, Severity


def _critical_failed(results: Sequence[RuleResult]) -> list[str]:
    return [r.rule_name for r in results if r.severity is Severity.CRITICAL and not r.passed]


def _warning_rows(results: Sequence[RuleResult]) -> frozenset[int]:
    rows: set[int] = set()
    for result in results:
        if result.severity is Severity.WARNING:
            rows |= result.failed_rows
    return frozenset(rows)


class RejectionPolicy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def decide(self, rows: frozenset[int], results: Sequence[RuleResult]) -> PolicyDecision: ...


class StrictBatchPolicy(RejectionPolicy):
    """Нарушено контрольное правило — партия отбраковывается целиком; предупреждения только в отчёт.

    Для денежных витрин (выручка, комиссии, выплаты): частичная загрузка исказит сверку с 1С.
    """

    @property
    def name(self) -> str:
        return "strict_batch"

    def decide(self, rows: frozenset[int], results: Sequence[RuleResult]) -> PolicyDecision:
        critical = _critical_failed(results)
        if critical:
            return PolicyDecision(BatchStatus.REJECTED, frozenset(), rows, "контрольные правила: " + ", ".join(critical))
        warnings = [r.rule_name for r in results if not r.passed]
        return PolicyDecision(BatchStatus.ACCEPTED, rows, frozenset(), "предупреждения: " + ", ".join(warnings) if warnings else "")


class QuarantineRowsPolicy(RejectionPolicy):
    """Контрольные правила — как в строгой политике; строки с предупреждениями уходят в карантин,
    остальное загружается. Если в карантин уходит больше порога — партия отбраковывается целиком.

    Для витрины посещений: единичный «битый» проход не должен задерживать загрузку остальных.
    """

    def __init__(self, max_quarantine_share: float = 0.05) -> None:
        if not 0 <= max_quarantine_share < 1:
            raise ValueError("Порог карантина должен быть в диапазоне [0, 1)")
        self._max_share = max_quarantine_share

    @property
    def name(self) -> str:
        return "quarantine_rows"

    def decide(self, rows: frozenset[int], results: Sequence[RuleResult]) -> PolicyDecision:
        critical = _critical_failed(results)
        if critical:
            return PolicyDecision(BatchStatus.REJECTED, frozenset(), rows, "контрольные правила: " + ", ".join(critical))
        bad = _warning_rows(results) & rows
        if rows and len(bad) / len(rows) > self._max_share:
            return PolicyDecision(
                BatchStatus.REJECTED, frozenset(), rows, f"в карантине {len(bad)} из {len(rows)} строк — выше порога"
            )
        status = BatchStatus.ACCEPTED_WITH_QUARANTINE if bad else BatchStatus.ACCEPTED
        return PolicyDecision(status, rows - bad, bad, f"в карантине {len(bad)} строк" if bad else "")


class AuditOnlyPolicy(RejectionPolicy):
    """Ничего не отбраковывает, только фиксирует нарушения: для первичной загрузки истории
    и подбора порогов на новом источнике."""

    @property
    def name(self) -> str:
        return "audit_only"

    def decide(self, rows: frozenset[int], results: Sequence[RuleResult]) -> PolicyDecision:
        failed = [r.rule_name for r in results if not r.passed]
        return PolicyDecision(BatchStatus.ACCEPTED, rows, frozenset(), "аудит: " + ", ".join(failed) if failed else "")
