from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from uuid import UUID

from fitagg_contracts import AccessPassed, Direction


@dataclass(frozen=True, slots=True)
class OccupancyEvent:

    gym_id: UUID
    visitor_id: UUID
    direction: Direction
    occurred_at: datetime

    @classmethod
    def from_access_passed(cls, event: AccessPassed) -> OccupancyEvent:
        return cls(
            gym_id=event.gym_id,
            visitor_id=event.user_id,
            direction=event.direction,
            occurred_at=event.occurred_at,
        )


@dataclass(frozen=True, slots=True)
class GymOccupancySettings:

    gym_id: UUID
    capacity: int
    strategy_name: str
    connected_since: datetime
    closing_time: time | None = None

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("Вместимость зала должна быть не меньше 1")


class OccupancyStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True, slots=True)
class OccupancySnapshot:

    gym_id: UUID
    status: OccupancyStatus
    visitors: int | None
    index: int | None
    strategy_name: str | None
    calculated_at: datetime
