from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import MappingProxyType

from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class RetentionRule:
    retention_days: int
    review_interval_days: int

    def __post_init__(self) -> None:
        if self.retention_days < 1:
            raise ValueError("retention_days must be positive")
        if self.review_interval_days < 1:
            raise ValueError("review_interval_days must be positive")
        if self.review_interval_days > self.retention_days:
            raise ValueError("review interval cannot exceed retention period")


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    version: int
    rules: Mapping[DataCategory, RetentionRule]
    prohibited_categories: frozenset[DataCategory]
    suppression_minimum_days: int
    backup_deletion_propagation_max_days: int
    restoration_requires_suppressions: bool

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("retention policy version must be positive")
        if self.suppression_minimum_days < 1:
            raise ValueError("suppression_minimum_days must be positive")
        if self.backup_deletion_propagation_max_days < 1:
            raise ValueError("backup deletion propagation must be positive")
        object.__setattr__(self, "rules", MappingProxyType(dict(self.rules)))

    def retention_deadline(
        self,
        category: DataCategory,
        collected_at: datetime,
    ) -> datetime:
        collected = require_aware_utc(collected_at, field_name="collected_at")
        if category in self.prohibited_categories:
            raise ValueError(f"category {category.value} is prohibited")
        try:
            rule = self.rules[category]
        except KeyError as exc:
            raise KeyError(f"no retention rule for {category.value}") from exc
        return collected + timedelta(days=rule.retention_days)

    def review_deadline(
        self,
        category: DataCategory,
        verified_at: datetime,
    ) -> datetime:
        verified = require_aware_utc(verified_at, field_name="verified_at")
        try:
            rule = self.rules[category]
        except KeyError as exc:
            raise KeyError(f"no retention rule for {category.value}") from exc
        return verified + timedelta(days=rule.review_interval_days)
