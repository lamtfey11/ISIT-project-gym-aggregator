from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from .domain import GymOccupancySettings, OccupancyEvent, OccupancySnapshot


class AccessEventSource(Protocol):
    def events_since(self, gym_id: UUID, since: datetime) -> Sequence[OccupancyEvent]: ...


class OccupancyHistoryRepository(Protocol):
    def save(self, snapshot: OccupancySnapshot) -> None: ...


class OccupancyPublisher(Protocol):
    def publish(self, snapshot: OccupancySnapshot) -> None: ...


class GymSettingsStore(Protocol):
    def get(self, gym_id: UUID) -> GymOccupancySettings | None: ...

    def save(self, settings: GymOccupancySettings) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
