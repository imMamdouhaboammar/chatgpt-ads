"""Provider-neutral, read-only advertising domain models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Mapping


class EvidenceKind(StrEnum):
    DOCUMENTED_FACT = "documented_fact"
    ACCOUNT_OBSERVATION = "account_observation"
    DERIVED_METRIC = "derived_metric"
    RECOMMENDATION = "recommendation"
    SIMULATION = "simulation"
    APPROVED_CHANGE = "approved_change"
    EXECUTED_CHANGE = "executed_change"


GRAINS = {"account", "campaign", "ad_group", "ad", "product", "country", "device", "platform", "time"}


@dataclass(frozen=True, slots=True)
class MeasurementContext:
    currency: str | None = None
    timezone: str | None = None
    attribution_window_days: int | None = None
    conversion_definition: str | None = None
    revenue_definition: str | None = None
    grain: str = "account"
    period_start: datetime | None = None
    period_end: datetime | None = None

    def __post_init__(self) -> None:
        if self.grain not in GRAINS:
            raise ValueError(f"unsupported grain: {self.grain}")
        if self.period_start is not None and self.period_end is not None and self.period_start >= self.period_end:
            raise ValueError("period_start must be before period_end")
        if self.attribution_window_days is not None and self.attribution_window_days < 1:
            raise ValueError("attribution_window_days must be positive")

    def compatible_with(self, other: "MeasurementContext") -> bool:
        fields = ("currency", "timezone", "attribution_window_days", "conversion_definition", "revenue_definition", "grain")
        return all(getattr(self, name) == getattr(other, name) for name in fields)


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    provider: str
    evidence_kind: EvidenceKind = EvidenceKind.ACCOUNT_OBSERVATION
    retrieved_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Account:
    id: str
    name: str | None = None
    status: str | None = None
    url: str | None = None
    timezone: str | None = None
    currency: str | None = None
    review_status: str | None = None
    source: SourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class Campaign:
    id: str
    account_id: str | None = None
    name: str | None = None
    status: str | None = None
    source: SourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class AdGroup:
    id: str
    campaign_id: str | None = None
    name: str | None = None
    status: str | None = None
    source: SourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class Ad:
    id: str
    ad_group_id: str | None = None
    name: str | None = None
    status: str | None = None
    source: SourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class InsightRow:
    context: MeasurementContext
    account_id: str | None = None
    campaign_id: str | None = None
    ad_group_id: str | None = None
    ad_id: str | None = None
    dimensions: Mapping[str, str | None] = field(default_factory=dict)
    impressions: int | None = None
    clicks: int | None = None
    spend: Decimal | None = None
    ctr: Decimal | None = None
    cpc: Decimal | None = None
    cpm: Decimal | None = None
    conversions: Decimal | None = None
    conversion_value: Decimal | None = None
    view_through_conversions: Decimal | None = None
    source: SourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class ConversionInsight:
    context: MeasurementContext
    entity_id: str | None = None
    conversions: Decimal | None = None
    conversion_value: Decimal | None = None
    view_through_conversions: Decimal | None = None
    event_name: str | None = None
    source: SourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class ConversionSource:
    id: str
    name: str | None = None
    source_type: str | None = None
    status: str | None = None
    source: SourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class ConversionEventSetting:
    id: str
    event_name: str | None = None
    status: str | None = None
    attribution_window_days: int | None = None
    source: SourceMetadata | None = None
