"""Компонент iot_occupancy_service «Сервис индекса загруженности» контейнера iot_service (C4 L4)."""

from .domain import GymOccupancySettings, OccupancyEvent, OccupancySnapshot, OccupancyStatus
from .scale import OccupancyScale
from .service import OccupancyService
from .strategies import (
    ExactBalanceStrategy,
    OccupancyStrategy,
    OccupancyStrategyRegistry,
    SmoothedStrategy,
    VisitTimeoutStrategy,
    build_default_registry,
)

__all__ = [
    "ExactBalanceStrategy",
    "GymOccupancySettings",
    "OccupancyEvent",
    "OccupancyScale",
    "OccupancyService",
    "OccupancySnapshot",
    "OccupancyStatus",
    "OccupancyStrategy",
    "OccupancyStrategyRegistry",
    "SmoothedStrategy",
    "VisitTimeoutStrategy",
    "build_default_registry",
]
