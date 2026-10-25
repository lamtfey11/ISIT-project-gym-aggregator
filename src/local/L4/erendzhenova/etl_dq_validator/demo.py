"""Демонстрация: одна и та же «грязная» партия при разных политиках отбраковки.

Запуск из папки компонента: python demo.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parents[1] / "contracts" / "python")]

import pandas as pd  # noqa: E402

from etl_dq_validator import (  # noqa: E402
    AuditOnlyPolicy,
    Batch,
    DataQualityValidator,
    FixedClock,
    QuarantineRowsPolicy,
    StrictBatchPolicy,
    ValidationReport,
    build_default_registry,
)

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def visits_batch(gym: str) -> pd.DataFrame:
    n = 40
    frame = pd.DataFrame(
        {
            "event_id": [str(uuid4()) for _ in range(n)],
            "visit_event_id": [str(uuid4()) for _ in range(n)],
            "gym_id": [gym] * n,
            "user_id": [str(uuid4()) for _ in range(n)],
            "direction": ["IN", "OUT"] * (n // 2),
            "source": (["TURNSTILE"] * 6 + ["ADMIN_SCANNER", "MANUAL"]) * (n // 8),
            "occurred_at": pd.to_datetime([NOW - timedelta(minutes=i) for i in range(n)], utc=True),
        }
    )
    frame.loc[5, "gym_id"] = str(uuid4())  # зал ещё не попал в справочник
    return frame


def show(label: str, report: ValidationReport) -> None:
    print(
        f"{label:<22} {report.status:<25} загружено {len(report.accepted):>2} / карантин "
        f"{len(report.quarantined):>2} | {report.reason or '—'}"
    )


def main() -> None:
    gym = str(uuid4())
    refs = {"gyms": frozenset({gym})}
    validator = DataQualityValidator(build_default_registry(), FixedClock(NOW))
    frame = visits_batch(gym)

    show("quarantine_rows", validator.validate(Batch(uuid4(), "fact_visits", frame), refs))
    validator.use_policy("fact_visits", StrictBatchPolicy())
    show("strict_batch", validator.validate(Batch(uuid4(), "fact_visits", frame), refs))
    validator.use_policy("fact_visits", AuditOnlyPolicy())
    show("audit_only", validator.validate(Batch(uuid4(), "fact_visits", frame), refs))
    validator.use_policy("fact_visits", QuarantineRowsPolicy(max_quarantine_share=0.0))
    show("quarantine (порог 0)", validator.validate(Batch(uuid4(), "fact_visits", frame), refs))


if __name__ == "__main__":
    main()
