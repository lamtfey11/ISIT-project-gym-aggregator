"""Профили проверок витрин: набор правил + политика отбраковки для каждого набора данных."""

from __future__ import annotations

from dataclasses import dataclass

from fitagg_contracts import AccessSource, Direction

from .domain import Severity, UnknownDatasetError
from .policies import QuarantineRowsPolicy, RejectionPolicy, StrictBatchPolicy
from .rules import (
    AllowedValuesRule,
    NotInFutureRule,
    NotNullRule,
    QualityRule,
    RangeRule,
    ReferenceRule,
    SchemaRule,
    SumEqualsRule,
    UniqueRule,
)


@dataclass(slots=True)
class DatasetProfile:
    dataset: str
    rules: list[QualityRule]
    policy: RejectionPolicy


class ProfileRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, DatasetProfile] = {}

    def register(self, profile: DatasetProfile) -> None:
        self._profiles[profile.dataset] = profile

    def get(self, dataset: str) -> DatasetProfile:
        try:
            return self._profiles[dataset]
        except KeyError:
            raise UnknownDatasetError(f"Для набора «{dataset}» нет профиля проверок") from None

    def datasets(self) -> list[str]:
        return sorted(self._profiles)


def build_default_registry() -> ProfileRegistry:
    """Профили фактов из событий payment.succeeded и access.passed (колонки — как в контрактах)."""
    registry = ProfileRegistry()
    registry.register(
        DatasetProfile(
            "fact_payments",
            [
                SchemaRule(
                    {
                        "event_id": "str",
                        "order_id": "str",
                        "gym_id": "str",
                        "total_minor": "int",
                        "gym_share_minor": "int",
                        "platform_commission_minor": "int",
                        "occurred_at": "datetime",
                    }
                ),
                NotNullRule(["event_id", "order_id", "gym_id", "occurred_at"]),
                UniqueRule(["event_id"]),
                RangeRule("total_minor", 1, None, Severity.CRITICAL),
                SumEqualsRule(["gym_share_minor", "platform_commission_minor"], "total_minor"),
                ReferenceRule("gym_id", "gyms", Severity.CRITICAL),
                NotInFutureRule("occurred_at", severity=Severity.CRITICAL),
            ],
            StrictBatchPolicy(),
        )
    )
    registry.register(
        DatasetProfile(
            "fact_visits",
            [
                SchemaRule(
                    {
                        "event_id": "str",
                        "visit_event_id": "str",
                        "gym_id": "str",
                        "user_id": "str",
                        "direction": "str",
                        "source": "str",
                        "occurred_at": "datetime",
                    }
                ),
                NotNullRule(["event_id", "visit_event_id", "gym_id", "direction", "source", "occurred_at"]),
                UniqueRule(["event_id"]),
                AllowedValuesRule("direction", [d.value for d in Direction]),
                AllowedValuesRule("source", [s.value for s in AccessSource]),
                ReferenceRule("gym_id", "gyms"),
                NotInFutureRule("occurred_at"),
            ],
            QuarantineRowsPolicy(max_quarantine_share=0.05),
        )
    )
    return registry
