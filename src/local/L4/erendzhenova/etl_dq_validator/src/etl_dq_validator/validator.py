"""Контекст шаблона «Стратегия»: модуль контроля качества данных (компонент etl_dq_validator)."""

from __future__ import annotations

from collections.abc import Mapping

from .domain import Batch, RuleResult, ValidationContext, ValidationReport
from .policies import RejectionPolicy
from .ports import Clock
from .profiles import ProfileRegistry
from .rules import QualityRule, SchemaRule


class DataQualityValidator:
    """Получает партию от etl_transform_engine, прогоняет правила профиля и по решению политики
    отдаёт etl_mart_loader только допущенные строки. Сам ничего не пишет в хранилища."""

    def __init__(self, profiles: ProfileRegistry, clock: Clock) -> None:
        self._profiles = profiles
        self._clock = clock

    def validate(self, batch: Batch, reference_keys: Mapping[str, frozenset[str]] | None = None) -> ValidationReport:
        profile = self._profiles.get(batch.dataset)
        frame = batch.frame.reset_index(drop=True)
        context = ValidationContext(self._clock.now(), reference_keys or {})

        schema_rules = [r for r in profile.rules if isinstance(r, SchemaRule)]
        results: list[RuleResult] = [rule.evaluate(frame, context) for rule in schema_rules]
        if all(r.passed for r in results):  # без нужных колонок остальные правила проверять нельзя
            results += [rule.evaluate(frame, context) for rule in profile.rules if rule not in schema_rules]

        decision = profile.policy.decide(frozenset(range(len(frame))), results)
        return ValidationReport(
            batch_id=batch.batch_id,
            dataset=batch.dataset,
            status=decision.status,
            policy_name=profile.policy.name,
            checked_at=context.now,
            total_rows=len(frame),
            accepted=frame.loc[sorted(decision.accepted_rows)],
            quarantined=frame.loc[sorted(decision.quarantined_rows)],
            results=tuple(results),
            reason=decision.reason,
        )

    def use_policy(self, dataset: str, policy: RejectionPolicy) -> None:
        """Динамическая подмена политики отбраковки (например, audit_only на время первичной загрузки)."""
        self._profiles.get(dataset).policy = policy

    def add_rule(self, dataset: str, rule: QualityRule) -> None:
        """Новое правило подключается без изменения валидатора (OCP)."""
        self._profiles.get(dataset).rules.append(rule)
