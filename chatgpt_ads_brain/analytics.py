"""Deterministic analytics over compatible normalized insight rows."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .domain import InsightRow

METRICS = {
    "impressions", "clicks", "spend", "ctr", "cpc", "cpm",
    "conversions", "conversion_value", "view_through_conversions",
}


@dataclass(frozen=True, slots=True)
class MetricChange:
    metric: str
    current: Decimal | None
    previous: Decimal | None
    absolute_change: Decimal | None
    relative_change: Decimal | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RankedMetric:
    entity_id: str
    value: Decimal


def _metric(row: InsightRow, metric: str) -> Decimal | None:
    if metric not in METRICS:
        raise ValueError(f"unsupported metric: {metric}")
    value = getattr(row, metric)
    return Decimal(value) if isinstance(value, int) else value


def _compatible(rows: list[InsightRow]) -> None:
    if not rows:
        raise ValueError("at least one insight row is required")
    reference = rows[0].context
    if any(not reference.compatible_with(row.context) for row in rows[1:]):
        raise ValueError("incompatible measurement contexts")


def _total(rows: list[InsightRow], metric: str) -> Decimal | None:
    values = [_metric(row, metric) for row in rows]
    if any(value is None for value in values):
        return None
    return sum((value for value in values if value is not None), Decimal("0"))


def compare_periods(current: Iterable[InsightRow], previous: Iterable[InsightRow], metric: str) -> MetricChange:
    current_rows, previous_rows = list(current), list(previous)
    _compatible(current_rows)
    _compatible(previous_rows)
    if not current_rows[0].context.compatible_with(previous_rows[0].context):
        raise ValueError("incompatible measurement contexts across periods")
    current_total, previous_total = _total(current_rows, metric), _total(previous_rows, metric)
    if current_total is None or previous_total is None:
        return MetricChange(metric, current_total, previous_total, None, None, "missing measurements are not treated as zero")
    absolute = current_total - previous_total
    relative = None if previous_total == 0 else absolute / previous_total
    reason = "relative change is undefined because the previous value is zero" if previous_total == 0 else None
    return MetricChange(metric, current_total, previous_total, absolute, relative, reason)


def rank_entities(rows: Iterable[InsightRow], metric: str, *, descending: bool = True) -> list[RankedMetric]:
    values = list(rows)
    _compatible(values)
    grain = values[0].context.grain
    id_field = {"account": "account_id", "campaign": "campaign_id", "ad_group": "ad_group_id", "ad": "ad_id"}.get(grain)
    if id_field is None:
        raise ValueError(f"ranking requires an entity grain, got {grain}")
    ranked = []
    for row in values:
        value = _metric(row, metric)
        entity_id = getattr(row, id_field)
        if value is not None and entity_id:
            ranked.append(RankedMetric(entity_id, value))
    ranked.sort(key=lambda item: ((-item.value if descending else item.value), item.entity_id))
    return ranked
