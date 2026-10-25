"""Порты компонента: интерфейсы соседних компонентов контейнера iot_service.

Сервис зависит от абстракций (принцип DIP). Реализации живут в инфраструктурном
слое: iot_repository (SQLAlchemy) и iot_cache_client (Redis) из диаграммы L3.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from .domain import GymOccupancySettings, OccupancyEvent, OccupancySnapshot


class AccessEventSource(Protocol):
    """Чтение учёта посещений (реализует iot_repository)."""

    def events_since(self, gym_id: UUID, since: datetime) -> Sequence[OccupancyEvent]: ...


class OccupancyHistoryRepository(Protocol):
    """История индекса загруженности (реализует iot_repository)."""

    def save(self, snapshot: OccupancySnapshot) -> None: ...


class OccupancyPublisher(Protocol):
    """Публикация актуального индекса для core_api (реализует iot_cache_client)."""

    def publish(self, snapshot: OccupancySnapshot) -> None: ...


class GymSettingsStore(Protocol):
    """Параметры залов: вместимость и выбранная стратегия (реализует iot_repository)."""

    def get(self, gym_id: UUID) -> GymOccupancySettings | None: ...

    def save(self, settings: GymOccupancySettings) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
