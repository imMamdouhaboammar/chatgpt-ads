from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from chatgpt_ads_brain.adapters import AdsAdapter
from chatgpt_ads_brain.capabilities import (
    CapabilityResolver,
    CapabilityState,
    CapabilityStatus,
)
from chatgpt_ads_brain.domain import InsightRow, MeasurementContext


class StubAdapter(AdsAdapter):
    def __init__(self, provider: str, states: list[CapabilityState]):
        self.provider = provider
        self._states = states

    def capabilities(self):
        return self._states


class DomainAndCapabilityTests(unittest.TestCase):
    def test_missing_measurements_remain_distinct_from_zero(self):
        context = MeasurementContext(
            currency="USD",
            timezone="America/New_York",
            grain="campaign",
            period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        missing = InsightRow(context=context, spend=None, clicks=None)
        zero = InsightRow(context=context, spend=Decimal("0"), clicks=0)
        self.assertIsNone(missing.spend)
        self.assertIsNone(missing.clicks)
        self.assertEqual(zero.spend, Decimal("0"))
        self.assertEqual(zero.clicks, 0)

    def test_measurement_context_rejects_invalid_period_and_grain(self):
        end = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "period_start"):
            MeasurementContext(grain="campaign", period_start=end, period_end=end)
        with self.assertRaisesRegex(ValueError, "grain"):
            MeasurementContext(grain="invented")

    def test_adapter_contract_is_runtime_inspectable(self):
        adapter = StubAdapter("normalized_csv", [])
        self.assertIsInstance(adapter, AdsAdapter)

    def test_resolver_prefers_usable_provider_in_explicit_order(self):
        host = StubAdapter("host_native", [CapabilityState("campaign.read", "host_native", CapabilityStatus.UNAVAILABLE, "host API absent")])
        api = StubAdapter("advertiser_api", [CapabilityState("campaign.read", "advertiser_api", CapabilityStatus.NOT_VERIFIED, "configured; account not verified", configured=True)])
        csv = StubAdapter("normalized_csv", [CapabilityState("campaign.read", "normalized_csv", CapabilityStatus.SUPPORTED, "local normalized input")])
        resolution = CapabilityResolver([csv, api, host]).resolve("campaign.read")
        self.assertEqual(resolution.provider, "normalized_csv")
        self.assertEqual(resolution.status, CapabilityStatus.SUPPORTED)
        self.assertTrue(resolution.usable)

    def test_resolver_reports_all_unavailable_reasons(self):
        native_csv = StubAdapter("native_csv", [CapabilityState("campaign.read", "native_csv", CapabilityStatus.REQUIRES_NATIVE_EVIDENCE, "native sample required")])
        knowledge = StubAdapter("knowledge", [CapabilityState("campaign.read", "knowledge", CapabilityStatus.UNAVAILABLE, "advisory only")])
        resolution = CapabilityResolver([native_csv, knowledge]).resolve("campaign.read")
        self.assertFalse(resolution.usable)
        self.assertIsNone(resolution.provider)
        self.assertEqual([item.provider for item in resolution.candidates], ["native_csv", "knowledge"])


if __name__ == "__main__":
    unittest.main()
