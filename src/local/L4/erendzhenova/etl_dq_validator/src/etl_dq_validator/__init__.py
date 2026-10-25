"""Компонент etl_dq_validator «Модуль контроля качества данных» контейнера etl_service (C4 L4)."""

from .domain import (
    Batch,
    BatchStatus,
    PolicyDecision,
    RuleResult,
    Severity,
    UnknownDatasetError,
    ValidationContext,
    ValidationReport,
)
from .policies import AuditOnlyPolicy, QuarantineRowsPolicy, RejectionPolicy, StrictBatchPolicy
from .ports import Clock, FixedClock, SystemClock
from .profiles import DatasetProfile, ProfileRegistry, build_default_registry
from .rules import (
    AllowedValuesRule,
    NotInFutureRule,
    NotNullRule,
    QualityRule,
    RangeRule,
    ReferenceRule,
    SchemaRule,
    SumEqualsRule,
    UniqueRule,
)
from .validator import DataQualityValidator

__all__ = [
    "AllowedValuesRule",
    "AuditOnlyPolicy",
    "Batch",
    "BatchStatus",
    "Clock",
    "DataQualityValidator",
    "DatasetProfile",
    "FixedClock",
    "NotInFutureRule",
    "NotNullRule",
    "PolicyDecision",
    "ProfileRegistry",
    "QualityRule",
    "QuarantineRowsPolicy",
    "RangeRule",
    "ReferenceRule",
    "RejectionPolicy",
    "RuleResult",
    "SchemaRule",
    "Severity",
    "StrictBatchPolicy",
    "SumEqualsRule",
    "SystemClock",
    "UniqueRule",
    "UnknownDatasetError",
    "ValidationContext",
    "ValidationReport",
    "build_default_registry",
]
