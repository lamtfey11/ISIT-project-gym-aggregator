from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from .domain import GymOccupancySettings, OccupancyEvent, OccupancySnapshot


class InMemoryAccessEventSource:
    def __init__(self) -> None:
        self._events: list[OccupancyEvent] = []

    def add(self, event: OccupancyEvent) -> None:
        self._events.append(event)

    def events_since(self, gym_id: UUID, since: datetime) -> Sequence[OccupancyEvent]:
        return [e for e in self._events if e.gym_id == gym_id and e.occurred_at >= since]


class InMemoryOccupancyHistory:
    def __init__(self) -> None:
        self.snapshots: list[OccupancySnapshot] = []

    def save(self, snapshot: OccupancySnapshot) -> None:
        self.snapshots.append(snapshot)


class InMemoryOccupancyPublisher:
    def __init__(self) -> None:
        self.latest: dict[UUID, OccupancySnapshot] = {}

    def publish(self, snapshot: OccupancySnapshot) -> None:
        self.latest[snapshot.gym_id] = snapshot


class InMemoryGymSettingsStore:
    def __init__(self) -> None:
        self._items: dict[UUID, GymOccupancySettings] = {}

    def get(self, gym_id: UUID) -> GymOccupancySettings | None:
        return self._items.get(gym_id)

    def save(self, settings: GymOccupancySettings) -> None:
        self._items[settings.gym_id] = settings


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now
