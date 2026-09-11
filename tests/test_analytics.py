from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from chatgpt_ads_brain.analytics import compare_periods, rank_entities
from chatgpt_ads_brain.domain import InsightRow, MeasurementContext


class AnalyticsTests(unittest.TestCase):
    def context(self, **changes):
        values = {"currency": "USD", "timezone": "UTC", "grain": "campaign", "period_start": datetime(2026, 1, 1, tzinfo=timezone.utc), "period_end": datetime(2026, 1, 2, tzinfo=timezone.utc)}
        values.update(changes)
        return MeasurementContext(**values)

    def test_compatible_period_comparison_is_deterministic(self):
        previous = [InsightRow(self.context(), campaign_id="a", clicks=100, spend=Decimal("50"))]
        current = [InsightRow(self.context(period_start=datetime(2026, 1, 2, tzinfo=timezone.utc), period_end=datetime(2026, 1, 3, tzinfo=timezone.utc)), campaign_id="a", clicks=80, spend=Decimal("60"))]
        change = compare_periods(current, previous, "clicks")
        self.assertEqual(change.absolute_change, Decimal("-20"))
        self.assertEqual(change.relative_change, Decimal("-0.2"))

    def test_missing_metric_propagates_and_zero_baseline_has_no_ratio(self):
        missing = compare_periods([InsightRow(self.context(), clicks=None)], [InsightRow(self.context(), clicks=10)], "clicks")
        self.assertIsNone(missing.current)
        self.assertIsNone(missing.relative_change)
        zero = compare_periods([InsightRow(self.context(), clicks=2)], [InsightRow(self.context(), clicks=0)], "clicks")
        self.assertEqual(zero.absolute_change, Decimal("2"))
        self.assertIsNone(zero.relative_change)

    def test_incompatible_measurement_context_is_rejected(self):
        current = [InsightRow(self.context(currency="EUR"), spend=Decimal("1"))]
        previous = [InsightRow(self.context(currency="USD"), spend=Decimal("1"))]
        with self.assertRaisesRegex(ValueError, "incompatible"):
            compare_periods(current, previous, "spend")

    def test_ranking_omits_missing_but_keeps_zero(self):
        rows = [
            InsightRow(self.context(), campaign_id="missing", clicks=None),
            InsightRow(self.context(), campaign_id="zero", clicks=0),
            InsightRow(self.context(), campaign_id="winner", clicks=9),
        ]
        ranked = rank_entities(rows, "clicks")
        self.assertEqual([(item.entity_id, item.value) for item in ranked], [("winner", Decimal("9")), ("zero", Decimal("0"))])


if __name__ == "__main__":
    unittest.main()
