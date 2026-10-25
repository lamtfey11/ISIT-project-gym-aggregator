from __future__ import annotations

import unittest
from collections.abc import Sequence
from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4

from fitagg_contracts import Direction, GymUpdated

from iot_occupancy_service import (
    ExactBalanceStrategy,
    OccupancyEvent,
    OccupancyScale,
    OccupancyService,
    OccupancyStatus,
    OccupancyStrategy,
    SmoothedStrategy,
    VisitTimeoutStrategy,
    build_default_registry,
)
from iot_occupancy_service.adapters_memory import (
    FixedClock,
    InMemoryAccessEventSource,
    InMemoryGymSettingsStore,
    InMemoryOccupancyHistory,
    InMemoryOccupancyPublisher,
)

T0 = datetime(2026, 10, 20, 18, 0, tzinfo=UTC)
GYM = uuid4()


def ev(visitor: UUID, direction: Direction, minutes: int) -> OccupancyEvent:
    return OccupancyEvent(GYM, visitor, direction, T0 + timedelta(minutes=minutes))


class ScaleTest(unittest.TestCase):
    def test_bounds_and_rounding(self) -> None:
        scale = OccupancyScale()
        self.assertEqual(scale.to_index(0, 40), 1)
        self.assertEqual(scale.to_index(4, 40), 1)
        self.assertEqual(scale.to_index(5, 40), 2)
        self.assertEqual(scale.to_index(40, 40), 10)
        self.assertEqual(scale.to_index(55, 40), 10)

    def test_capacity_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            OccupancyScale().to_index(1, 0)


class StrategiesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.a, self.b, self.c = uuid4(), uuid4(), uuid4()

    def test_exact_balance_counts_in_minus_out(self) -> None:
        events = [ev(self.a, Direction.IN, 0), ev(self.b, Direction.IN, 1), ev(self.a, Direction.OUT, 30)]
        self.assertEqual(ExactBalanceStrategy().estimate(events, T0 + timedelta(minutes=40)), 1)

    def test_exact_balance_never_negative(self) -> None:
        events = [ev(self.a, Direction.OUT, 0), ev(self.b, Direction.IN, 5)]
        self.assertEqual(ExactBalanceStrategy().estimate(events, T0 + timedelta(minutes=10)), 1)

    def test_exact_balance_ignores_future_events(self) -> None:
        events = [ev(self.a, Direction.IN, 0), ev(self.b, Direction.IN, 60)]
        self.assertEqual(ExactBalanceStrategy().estimate(events, T0 + timedelta(minutes=10)), 1)

    def test_timeout_drops_forgotten_exit(self) -> None:
        events = [ev(self.a, Direction.IN, 0), ev(self.b, Direction.IN, 170)]
        now = T0 + timedelta(minutes=200)
        self.assertEqual(ExactBalanceStrategy().estimate(events, now), 2)
        self.assertEqual(VisitTimeoutStrategy(timedelta(hours=3)).estimate(events, now), 1)

    def test_timeout_counts_double_entry_once(self) -> None:
        events = [ev(self.a, Direction.IN, 0), ev(self.a, Direction.IN, 2)]
        now = T0 + timedelta(minutes=5)
        self.assertEqual(ExactBalanceStrategy().estimate(events, now), 2)
        self.assertEqual(VisitTimeoutStrategy().estimate(events, now), 1)

    def test_smoothed_dampens_spike(self) -> None:
        events = [ev(uuid4(), Direction.IN, 9) for _ in range(10)]
        now = T0 + timedelta(minutes=10)
        exact = ExactBalanceStrategy()
        self.assertEqual(exact.estimate(events, now), 10)
        self.assertLess(SmoothedStrategy(exact).estimate(events, now), 5)

    def test_invalid_parameters_rejected(self) -> None:
        with self.assertRaises(ValueError):
            VisitTimeoutStrategy(timedelta(0))
        with self.assertRaises(ValueError):
            SmoothedStrategy(ExactBalanceStrategy(), window=timedelta(minutes=1), step=timedelta(minutes=5))


class ConstantStrategy(OccupancyStrategy):
    @property
    def name(self) -> str:
        return "constant"

    def estimate(self, events: Sequence[OccupancyEvent], now: datetime) -> int:
        return 30


class ServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FixedClock(T0 - timedelta(days=8))
        self.events = InMemoryAccessEventSource()
        self.history = InMemoryOccupancyHistory()
        self.publisher = InMemoryOccupancyPublisher()
        self.registry = build_default_registry()
        self.service = OccupancyService(
            self.registry,
            self.events,
            self.history,
            self.publisher,
            InMemoryGymSettingsStore(),
            self.clock,
            default_strategy_name="exact_balance",
        )
        self.service.apply_gym_update(GymUpdated(gym_id=GYM, capacity=40))
        self.clock.set(T0 + timedelta(minutes=30))

    def feed(self, *events: OccupancyEvent) -> None:
        for event in events:
            self.events.add(event)

    def test_unknown_gym_has_insufficient_data(self) -> None:
        snapshot = self.service.recalculate(uuid4())
        self.assertIs(snapshot.status, OccupancyStatus.INSUFFICIENT_DATA)
        self.assertIsNone(snapshot.index)

    def test_new_gym_is_hidden_during_warmup(self) -> None:
        other = uuid4()
        self.service.apply_gym_update(GymUpdated(gym_id=other, capacity=10))
        self.assertIs(self.service.recalculate(other).status, OccupancyStatus.INSUFFICIENT_DATA)

    def test_on_access_publishes_and_saves(self) -> None:
        a = uuid4()
        self.feed(ev(a, Direction.IN, 0))
        snapshot = self.service.on_access(ev(a, Direction.IN, 0))
        self.assertIs(snapshot.status, OccupancyStatus.AVAILABLE)
        self.assertEqual(snapshot.visitors, 1)
        self.assertEqual(self.publisher.latest[GYM], snapshot)
        self.assertEqual(self.history.snapshots[-1], snapshot)

    def test_strategy_swapped_at_runtime_without_changing_context(self) -> None:
        a = uuid4()
        self.clock.set(T0 + timedelta(minutes=200))
        self.feed(ev(a, Direction.IN, 0))
        self.assertEqual(self.service.recalculate(GYM).visitors, 1)
        self.service.use_strategy(GYM, "visit_timeout")
        self.assertEqual(self.service.recalculate(GYM).visitors, 0)

    def test_new_strategy_plugged_via_registry(self) -> None:
        self.registry.register(ConstantStrategy())
        self.service.use_strategy(GYM, "constant")
        snapshot = self.service.recalculate(GYM)
        self.assertEqual((snapshot.visitors, snapshot.index, snapshot.strategy_name), (30, 8, "constant"))

    def test_unknown_strategy_rejected(self) -> None:
        with self.assertRaises(KeyError):
            self.service.use_strategy(GYM, "no_such_strategy")

    def test_counter_resets_after_closing_time(self) -> None:
        self.service.apply_gym_update(GymUpdated(gym_id=GYM, capacity=40, closing_time=time(23, 0)))
        self.feed(ev(uuid4(), Direction.IN, 0))
        self.clock.set(T0 + timedelta(hours=6))
        self.assertEqual(self.service.recalculate(GYM).visitors, 0)


if __name__ == "__main__":
    unittest.main()
