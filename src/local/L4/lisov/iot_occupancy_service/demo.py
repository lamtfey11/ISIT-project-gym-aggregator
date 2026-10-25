"""Демонстрация: один поток событий, разные стратегии, подмена во время работы.

Запуск из папки компонента: python demo.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parents[1] / "contracts" / "python")]

from fitagg_contracts import Direction, GymUpdated  # noqa: E402

from iot_occupancy_service import OccupancyEvent, OccupancyService, build_default_registry  # noqa: E402
from iot_occupancy_service.adapters_memory import (  # noqa: E402
    FixedClock,
    InMemoryAccessEventSource,
    InMemoryGymSettingsStore,
    InMemoryOccupancyHistory,
    InMemoryOccupancyPublisher,
)


def main() -> None:
    start = datetime(2026, 10, 20, 17, 0, tzinfo=UTC)
    gym = uuid4()
    clock = FixedClock(start - timedelta(days=10))
    events = InMemoryAccessEventSource()
    registry = build_default_registry()
    service = OccupancyService(
        registry,
        events,
        InMemoryOccupancyHistory(),
        InMemoryOccupancyPublisher(),
        InMemoryGymSettingsStore(),
        clock,
        default_strategy_name="exact_balance",
    )
    service.apply_gym_update(GymUpdated(gym_id=gym, capacity=20))

    visitors = [uuid4() for _ in range(14)]
    for i, person in enumerate(visitors):
        events.add(OccupancyEvent(gym, person, Direction.IN, start + timedelta(minutes=5 * i)))
    for person in visitors[:6]:
        events.add(OccupancyEvent(gym, person, Direction.OUT, start + timedelta(minutes=80)))
    clock.set(start + timedelta(hours=4))

    print("Вечер, вместимость зала 20; 14 входов, 6 выходов; у 8 человек выход не зафиксирован.")
    print(f"{'стратегия':<28}{'людей':>7}{'индекс':>8}")
    for name in registry.names():
        service.use_strategy(gym, name)
        snapshot = service.recalculate(gym)
        print(f"{name:<28}{snapshot.visitors!s:>7}{snapshot.index!s:>8}")


if __name__ == "__main__":
    main()
