"""Тесты etl_dq_validator. Запуск: python -m unittest (или pytest)."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pandas as pd

from etl_dq_validator import (
    AuditOnlyPolicy,
    Batch,
    BatchStatus,
    DataQualityValidator,
    FixedClock,
    QualityRule,
    RuleResult,
    Severity,
    UnknownDatasetError,
    ValidationContext,
    build_default_registry,
)

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
GYM = str(uuid4())
REFS: dict[str, frozenset[str]] = {"gyms": frozenset({GYM})}


def payments(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": [str(uuid4()) for _ in range(n)],
            "order_id": [str(uuid4()) for _ in range(n)],
            "gym_id": [GYM] * n,
            "total_minor": [300000] * n,
            "gym_share_minor": [255000] * n,
            "platform_commission_minor": [45000] * n,
            "occurred_at": pd.to_datetime([NOW - timedelta(minutes=i) for i in range(n)], utc=True),
        }
    )


def visits(n: int = 40) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": [str(uuid4()) for _ in range(n)],
            "visit_event_id": [str(uuid4()) for _ in range(n)],
            "gym_id": [GYM] * n,
            "user_id": [str(uuid4()) for _ in range(n)],
            "direction": ["IN", "OUT"] * (n // 2),
            "source": ["TURNSTILE"] * n,
            "occurred_at": pd.to_datetime([NOW - timedelta(minutes=i) for i in range(n)], utc=True),
        }
    )


class NoNightVisitsRule(QualityRule):
    """Правило, добавленное без изменения валидатора (проверка OCP)."""

    @property
    def name(self) -> str:
        return "no_night_visits"

    def evaluate(self, frame: pd.DataFrame, context: ValidationContext) -> RuleResult:
        hours = frame["occurred_at"].dt.hour
        mask = (hours >= 1) & (hours < 5)
        return RuleResult(self.name, self.severity, frozenset(int(i) for i in mask[mask].index))


class DataQualityValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = DataQualityValidator(build_default_registry(), FixedClock(NOW))

    def check(self, dataset: str, frame: pd.DataFrame) -> tuple[BatchStatus, int, int, list[str]]:
        report = self.validator.validate(Batch(uuid4(), dataset, frame), REFS)
        return report.status, len(report.accepted), len(report.quarantined), report.failed_rules

    def test_clean_payments_accepted(self) -> None:
        self.assertEqual(self.check("fact_payments", payments()), (BatchStatus.ACCEPTED, 3, 0, []))

    def test_split_mismatch_rejects_whole_batch(self) -> None:
        frame = payments()
        frame.loc[1, "platform_commission_minor"] = 45001
        status, accepted, quarantined, failed = self.check("fact_payments", frame)
        self.assertEqual((status, accepted, quarantined), (BatchStatus.REJECTED, 0, 3))
        self.assertIn("sum_equals[gym_share_minor+platform_commission_minor=total_minor]", failed)

    def test_duplicate_event_rejected(self) -> None:
        frame = payments()
        frame.loc[2, "event_id"] = frame.loc[0, "event_id"]
        self.assertEqual(self.check("fact_payments", frame)[0], BatchStatus.REJECTED)

    def test_schema_violation_stops_other_rules(self) -> None:
        frame = payments().drop(columns=["gym_share_minor"])
        report = self.validator.validate(Batch(uuid4(), "fact_payments", frame), REFS)
        self.assertEqual(report.status, BatchStatus.REJECTED)
        self.assertEqual(report.failed_rules, ["schema"])
        self.assertIn("gym_share_minor", report.results[0].message)

    def test_wrong_type_detected(self) -> None:
        frame = payments()
        frame["total_minor"] = frame["total_minor"].astype(str)
        self.assertEqual(self.check("fact_payments", frame)[3], ["schema"])

    def test_visit_with_unknown_gym_goes_to_quarantine(self) -> None:
        frame = visits()
        frame.loc[5, "gym_id"] = str(uuid4())
        status, accepted, quarantined, _ = self.check("fact_visits", frame)
        self.assertEqual((status, accepted, quarantined), (BatchStatus.ACCEPTED_WITH_QUARANTINE, 39, 1))

    def test_quarantine_above_threshold_rejects(self) -> None:
        frame = visits()
        frame.loc[0:4, "occurred_at"] = pd.Timestamp(NOW + timedelta(hours=1))
        self.assertEqual(self.check("fact_visits", frame)[0], BatchStatus.REJECTED)

    def test_unknown_direction_is_critical(self) -> None:
        frame = visits()
        frame.loc[3, "direction"] = "SIDEWAYS"
        status, _, _, failed = self.check("fact_visits", frame)
        self.assertEqual(status, BatchStatus.REJECTED)
        self.assertIn("allowed[direction]", failed)

    def test_all_three_access_sources_allowed(self) -> None:
        frame = visits(6)
        frame["source"] = ["TURNSTILE", "TURNSTILE", "ADMIN_SCANNER", "ADMIN_SCANNER", "MANUAL", "MANUAL"]
        self.assertEqual(self.check("fact_visits", frame)[0], BatchStatus.ACCEPTED)

    def test_runtime_policy_swap(self) -> None:
        frame = payments()
        frame.loc[1, "platform_commission_minor"] = 1
        self.validator.use_policy("fact_payments", AuditOnlyPolicy())
        report = self.validator.validate(Batch(uuid4(), "fact_payments", frame), REFS)
        self.assertEqual((report.status, report.policy_name, len(report.accepted)), (BatchStatus.ACCEPTED, "audit_only", 3))
        self.assertTrue(report.reason.startswith("аудит"))

    def test_new_rule_without_changing_validator(self) -> None:
        self.validator.add_rule("fact_visits", NoNightVisitsRule(Severity.WARNING))
        frame = visits()
        frame.loc[7, "occurred_at"] = pd.Timestamp(datetime(2026, 10, 24, 3, 0, tzinfo=UTC))
        status, accepted, quarantined, failed = self.check("fact_visits", frame)
        self.assertEqual((status, accepted, quarantined), (BatchStatus.ACCEPTED_WITH_QUARANTINE, 39, 1))
        self.assertIn("no_night_visits", failed)

    def test_unknown_dataset(self) -> None:
        with self.assertRaises(UnknownDatasetError):
            self.validator.validate(Batch(uuid4(), "fact_unknown", payments()))

    def test_empty_batch_accepted(self) -> None:
        self.assertEqual(self.check("fact_payments", payments(1).iloc[0:0])[0], BatchStatus.ACCEPTED)


if __name__ == "__main__":
    unittest.main()
