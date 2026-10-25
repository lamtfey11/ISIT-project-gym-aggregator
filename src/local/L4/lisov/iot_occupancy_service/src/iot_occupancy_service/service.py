from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID

from fitagg_contracts import GymUpdated

from .domain import GymOccupancySettings, OccupancyEvent, OccupancySnapshot, OccupancyStatus
from .ports import AccessEventSource, Clock, GymSettingsStore, OccupancyHistoryRepository, OccupancyPublisher
from .scale import OccupancyScale
from .strategies import OccupancyStrategyRegistry


class OccupancyService:

    def __init__(
        self,
        registry: OccupancyStrategyRegistry,
        events: AccessEventSource,
        history: OccupancyHistoryRepository,
        publisher: OccupancyPublisher,
        settings: GymSettingsStore,
        clock: Clock,
        default_strategy_name: str = "smoothed_visit_timeout",
        observation_window: timedelta = timedelta(hours=16),
        warmup: timedelta = timedelta(days=7),
        scale: OccupancyScale | None = None,
    ) -> None:
        registry.get(default_strategy_name)
        self._registry = registry
        self._events = events
        self._history = history
        self._publisher = publisher
        self._settings = settings
        self._clock = clock
        self._default_strategy_name = default_strategy_name
        self._window = observation_window
        self._warmup = warmup
        self._scale = scale or OccupancyScale()

    def on_access(self, event: OccupancyEvent) -> OccupancySnapshot:
        return self.recalculate(event.gym_id)

    def apply_gym_update(self, update: GymUpdated) -> None:
        current = self._settings.get(update.gym_id)
        if current is None:
            current = GymOccupancySettings(
                gym_id=update.gym_id,
                capacity=update.capacity,
                strategy_name=self._default_strategy_name,
                connected_since=self._clock.now(),
                closing_time=update.closing_time,
            )
        else:
            current = replace(current, capacity=update.capacity, closing_time=update.closing_time)
        self._settings.save(current)

    def use_strategy(self, gym_id: UUID, strategy_name: str) -> None:
        self._registry.get(strategy_name)
        current = self._settings.get(gym_id)
        if current is None:
            raise KeyError(f"Зал {gym_id} ещё не передал вместимость")
        self._settings.save(replace(current, strategy_name=strategy_name))

    def set_default_strategy(self, strategy_name: str) -> None:
        self._registry.get(strategy_name)
        self._default_strategy_name = strategy_name

    def recalculate(self, gym_id: UUID) -> OccupancySnapshot:
        now = self._clock.now()
        settings = self._settings.get(gym_id)
        if settings is None or now - settings.connected_since < self._warmup:
            snapshot = OccupancySnapshot(gym_id, OccupancyStatus.INSUFFICIENT_DATA, None, None, None, now)
        else:
            strategy = self._registry.get(settings.strategy_name)
            events = self._events.events_since(gym_id, self._since(settings, now))
            visitors = strategy.estimate(events, now)
            snapshot = OccupancySnapshot(
                gym_id=gym_id,
                status=OccupancyStatus.AVAILABLE,
                visitors=visitors,
                index=self._scale.to_index(visitors, settings.capacity),
                strategy_name=strategy.name,
                calculated_at=now,
            )
        self._history.save(snapshot)
        self._publisher.publish(snapshot)
        return snapshot

    def _since(self, settings: GymOccupancySettings, now: datetime) -> datetime:
        since = now - self._window
        if settings.closing_time is not None:
            closing_today = now.replace(
                hour=settings.closing_time.hour,
                minute=settings.closing_time.minute,
                second=0,
                microsecond=0,
            )
            last_closing = closing_today if closing_today <= now else closing_today - timedelta(days=1)
            since = max(since, last_closing)
        return since
