"""Provider adapter boundary for normalized read-only ads operations."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .capabilities import CapabilityState
from .domain import (
    Account,
    Ad,
    AdGroup,
    Campaign,
    ConversionEventSetting,
    ConversionInsight,
    ConversionSource,
    InsightRow,
)


class CapabilityUnavailable(RuntimeError):
    def __init__(self, capability: str, reason: str = "capability_unavailable"):
        self.capability = capability
        self.reason = reason
        super().__init__(f"{capability}: {reason}")


class AdsAdapter:
    """Stable adapter interface; provider payloads stop at this boundary."""

    provider = "unknown"

    def capabilities(self) -> Iterable[CapabilityState]:
        raise NotImplementedError

    def get_account(self) -> Account:
        raise CapabilityUnavailable("account.read")

    def list_campaigns(self) -> list[Campaign]:
        raise CapabilityUnavailable("campaign.read")

    def get_campaign(self, campaign_id: str) -> Campaign:
        raise CapabilityUnavailable("campaign.read")

    def list_ad_groups(self, campaign_id: str | None = None) -> list[AdGroup]:
        raise CapabilityUnavailable("ad_group.read")

    def list_ads(self, ad_group_id: str | None = None) -> list[Ad]:
        raise CapabilityUnavailable("ad.read")

    def get_account_insights(self, query: Mapping[str, Any]) -> list[InsightRow]:
        raise CapabilityUnavailable("insights.account.read")

    def get_campaign_insights(self, campaign_id: str, query: Mapping[str, Any]) -> list[InsightRow]:
        raise CapabilityUnavailable("insights.campaign.read")

    def get_ad_group_insights(self, ad_group_id: str, query: Mapping[str, Any]) -> list[InsightRow]:
        raise CapabilityUnavailable("insights.ad_group.read")

    def get_ad_insights(self, ad_id: str, query: Mapping[str, Any]) -> list[InsightRow]:
        raise CapabilityUnavailable("insights.ad.read")

    def list_conversion_sources(self) -> list[ConversionSource]:
        raise CapabilityUnavailable("conversion_sources.read")

    def list_conversion_settings(self) -> list[ConversionEventSetting]:
        raise CapabilityUnavailable("conversion_settings.read")

    def get_conversion_insights(self, query: Mapping[str, Any]) -> list[ConversionInsight]:
        raise CapabilityUnavailable("conversion_insights.read")
