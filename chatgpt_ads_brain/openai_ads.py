"""Read-only OpenAI Advertiser API transport and normalized adapter."""
from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.message import Message
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .adapters import AdsAdapter, CapabilityUnavailable
from .capabilities import CapabilityState, CapabilityStatus
from .domain import (
    Account,
    Ad,
    AdGroup,
    Campaign,
    ConversionEventSetting,
    ConversionInsight,
    ConversionSource,
    InsightRow,
    MeasurementContext,
    SourceMetadata,
)

BASE_URL = "https://api.ads.openai.com/v1"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
READ_CAPABILITIES = (
    "account.read",
    "campaign.read",
    "ad_group.read",
    "ad.read",
    "insights.account.read",
    "insights.campaign.read",
    "insights.ad_group.read",
    "insights.ad.read",
    "conversion_sources.read",
    "conversion_settings.read",
    "conversion_insights.read",
)


@dataclass(frozen=True, slots=True)
class TransportResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class AdsApiError(RuntimeError):
    """A redacted, stable API failure safe for CLI output."""

    def __init__(self, code: str, message: str, *, status: int | None = None, retryable: bool = False):
        self.code = code
        self.status = status
        self.retryable = retryable
        super().__init__(f"{code}: {message}")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


_DEFAULT_OPENER = build_opener(_NoRedirect)


def _urllib_sender(request: Request, timeout: float) -> TransportResponse:
    try:
        with _DEFAULT_OPENER.open(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            return TransportResponse(response.status, dict(response.headers.items()), body)
    except HTTPError as exc:
        body = exc.read(MAX_RESPONSE_BYTES + 1)
        return TransportResponse(exc.code, dict(exc.headers.items()) if exc.headers else {}, body)
    except URLError as exc:
        if isinstance(exc.reason, socket.timeout):
            raise socket.timeout() from None
        raise OSError("network request failed") from None


class AdsApiTransport:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = BASE_URL,
        timeout: float = 15.0,
        max_retries: int = 2,
        sender: Callable[[Request, float], TransportResponse] = _urllib_sender,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        if base_url.rstrip("/") != BASE_URL:
            raise ValueError("base_url must be the documented Advertiser API origin and version")
        if timeout <= 0 or max_retries < 0 or max_retries > 5:
            raise ValueError("invalid transport retry or timeout configuration")
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_ADS_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._sender = sender
        self._sleep = sleeper
        self.allow_account_verification = sender is _urllib_sender

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        retryable_request: bool | None = None,
    ) -> dict[str, Any]:
        method = method.upper()
        if not path.startswith("/") or "://" in path or ".." in path.split("/"):
            raise ValueError("path must be a relative API path")
        if not self.configured:
            raise AdsApiError("not_configured", "OPENAI_ADS_API_KEY is not configured")
        if any(ord(char) < 33 or ord(char) == 127 for char in self.api_key):
            raise AdsApiError("invalid_configuration", "API key contains unsupported characters")
        if method == "GET" and json_body is not None:
            raise ValueError("GET requests cannot include a JSON body")
        if method == "POST" and path != "/conversions/insights":
            raise ValueError("read-only transport permits POST only for conversion-insights retrieval")
        if method not in {"GET", "POST"}:
            raise ValueError("read-only transport permits GET and documented retrieval POST only")
        if retryable_request is None:
            retryable_request = method == "GET"
        encoded_query = _encode_query(query or {})
        url = self.base_url + path + ("?" + encoded_query if encoded_query else "")
        body = None if json_body is None else json.dumps(json_body, separators=(",", ":")).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=body, headers=headers, method=method)

        attempt = 0
        while True:
            try:
                response = self._sender(request, self.timeout)
            except (socket.timeout, TimeoutError):
                if retryable_request and attempt < self.max_retries:
                    self._sleep(0.5 * (2**attempt))
                    attempt += 1
                    continue
                raise AdsApiError("timeout", "request timed out", retryable=True) from None
            except OSError:
                if retryable_request and attempt < self.max_retries:
                    self._sleep(0.5 * (2**attempt))
                    attempt += 1
                    continue
                raise AdsApiError("network_error", "network request failed", retryable=True) from None
            except (ValueError, TypeError, UnicodeError):
                raise AdsApiError("transport_error", "request transport rejected the request") from None

            if len(response.body) > MAX_RESPONSE_BYTES:
                raise AdsApiError("invalid_response", "response exceeds size limit", status=response.status)
            if 200 <= response.status < 300:
                try:
                    value = json.loads(response.body)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    raise AdsApiError("invalid_response", "response is not valid JSON", status=response.status) from None
                if not isinstance(value, dict):
                    raise AdsApiError("invalid_response", "response root must be an object", status=response.status)
                return value

            retryable = response.status in RETRYABLE_STATUSES
            if retryable and retryable_request and attempt < self.max_retries:
                self._sleep(_retry_delay(response.headers, attempt))
                attempt += 1
                continue
            code = {
                400: "invalid_request",
                401: "authentication_failed",
                403: "permission_denied",
                404: "capability_unavailable",
                429: "rate_limited",
            }.get(response.status, "server_error" if response.status >= 500 else "http_error")
            raise AdsApiError(code, "Advertiser API request failed", status=response.status, retryable=retryable)

    def get_paginated(self, path: str, query: Mapping[str, Any] | None = None, *, max_pages: int = 100, max_rows: int = 100_000) -> list[dict[str, Any]]:
        if max_pages < 1 or max_pages > 100 or max_rows < 1:
            raise ValueError("invalid pagination limits")
        params = dict(query or {})
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for _ in range(max_pages):
            payload = self.request("GET", path, query=params)
            data = _list_data(payload)
            if len(rows) + len(data) > max_rows:
                raise AdsApiError("pagination_limit", "pagination exceeded the row limit")
            rows.extend(data)
            if "has_more" not in payload:
                raise AdsApiError("invalid_response", "has_more is required for paginated responses")
            has_more = payload["has_more"]
            if not isinstance(has_more, bool):
                raise AdsApiError("invalid_response", "has_more must be a boolean")
            if not has_more:
                return rows
            cursor = payload.get("last_id")
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise AdsApiError("invalid_response", "pagination cursor is missing or repeated")
            seen.add(cursor)
            params["after"] = cursor
        raise AdsApiError("pagination_limit", "pagination exceeded the page limit")


def _encode_query(query: Mapping[str, Any]) -> str:
    pairs: list[tuple[str, Any]] = []
    for key, value in query.items():
        if value is None:
            continue
        values = value if isinstance(value, (list, tuple)) else [value]
        for item in values:
            if isinstance(item, (dict, list)):
                item = json.dumps(item, separators=(",", ":"))
            elif isinstance(item, bool):
                item = str(item).lower()
            pairs.append((str(key), item))
    return urlencode(pairs)


def _retry_delay(headers: Mapping[str, str], attempt: int) -> float:
    value = headers.get("Retry-After") or headers.get("retry-after")
    if value is not None:
        try:
            return max(0.0, min(float(value), 30.0))
        except ValueError:
            pass
    return min(0.5 * (2**attempt), 30.0)


def _list_data(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if payload.get("object") != "list" or not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise AdsApiError("invalid_response", "expected a documented list response")
    return data


def _required_id(row: Mapping[str, Any]) -> str:
    value = row.get("id")
    if not isinstance(value, str) or not value:
        raise AdsApiError("invalid_response", "resource id is missing")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AdsApiError("invalid_response", "expected string or null")
    return value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise AdsApiError("invalid_response", "expected integer or null")
    return value


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise AdsApiError("invalid_response", "expected numeric value or null")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise AdsApiError("invalid_response", "numeric value is invalid") from None


def _timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdsApiError("invalid_response", "timestamp must be numeric or null")
    return datetime.fromtimestamp(value, tz=timezone.utc)


class OpenAIAdsAdapter(AdsAdapter):
    provider = "advertiser_api"

    def __init__(self, transport: AdsApiTransport | None = None):
        self.transport = transport or AdsApiTransport()
        self._account: Account | None = None
        self._verified_capabilities: set[str] = set()

    def capabilities(self) -> tuple[CapabilityState, ...]:
        if not self.transport.configured:
            return tuple(CapabilityState(name, self.provider, CapabilityStatus.NOT_CONFIGURED, "OPENAI_ADS_API_KEY is not configured") for name in READ_CAPABILITIES)
        return tuple(
            CapabilityState(
                name,
                self.provider,
                CapabilityStatus.SUPPORTED if name in self._verified_capabilities else CapabilityStatus.NOT_VERIFIED,
                "capability verified through the native transport in this process" if name in self._verified_capabilities else "adapter implemented and configured; endpoint access not verified",
                configured=True,
                account_verified="account.read" in self._verified_capabilities,
            )
            for name in READ_CAPABILITIES
        )

    def _mark_verified(self, capability: str) -> None:
        if self.transport.allow_account_verification:
            self._verified_capabilities.add(capability)

    def get_account(self) -> Account:
        row = self.transport.request("GET", "/ad_account")
        review = row.get("review")
        if review is not None and not isinstance(review, dict):
            raise AdsApiError("invalid_response", "review must be an object or null")
        account = Account(
            id=_required_id(row),
            name=_optional_string(row.get("name")),
            url=_optional_string(row.get("url")),
            status=_optional_string(row.get("status")),
            timezone=_optional_string(row.get("timezone")),
            currency=_optional_string(row.get("currency_code")),
            review_status=_optional_string(review.get("status")) if review else None,
            source=self._source(row),
        )
        self._account = account
        self._mark_verified("account.read")
        return account

    def _ensure_account(self) -> Account:
        return self._account or self.get_account()

    def list_campaigns(self) -> list[Campaign]:
        account = self._ensure_account()
        rows = self.transport.get_paginated("/campaigns", {"limit": 500})
        self._mark_verified("campaign.read")
        return [Campaign(id=_required_id(row), name=_optional_string(row.get("name")), status=_optional_string(row.get("status")), account_id=account.id, source=self._source(row)) for row in rows]

    def get_campaign(self, campaign_id: str) -> Campaign:
        for campaign in self.list_campaigns():
            if campaign.id == campaign_id:
                return campaign
        raise CapabilityUnavailable("campaign.read", "campaign_not_found")

    def list_ad_groups(self, campaign_id: str | None = None) -> list[AdGroup]:
        if not campaign_id:
            raise ValueError("campaign_id is required by the Advertiser API")
        self._ensure_account()
        rows = self.transport.get_paginated("/ad_groups", {"campaign_id": campaign_id, "limit": 500})
        self._mark_verified("ad_group.read")
        return [AdGroup(id=_required_id(row), campaign_id=campaign_id, name=_optional_string(row.get("name")), status=_optional_string(row.get("status")), source=self._source(row)) for row in rows]

    def list_ads(self, ad_group_id: str | None = None) -> list[Ad]:
        if not ad_group_id:
            raise ValueError("ad_group_id is required by the Advertiser API")
        self._ensure_account()
        rows = self.transport.get_paginated("/ads", {"ad_group_id": ad_group_id, "limit": 500})
        self._mark_verified("ad.read")
        return [Ad(id=_required_id(row), ad_group_id=ad_group_id, name=_optional_string(row.get("name")), status=_optional_string(row.get("status")), source=self._source(row)) for row in rows]

    def get_account_insights(self, query: Mapping[str, Any]) -> list[InsightRow]:
        return self._insights("/ad_account/insights", query, "account")

    def get_campaign_insights(self, campaign_id: str, query: Mapping[str, Any]) -> list[InsightRow]:
        return self._insights(f"/campaigns/{quote(campaign_id, safe='')}/insights", query, "campaign")

    def get_ad_group_insights(self, ad_group_id: str, query: Mapping[str, Any]) -> list[InsightRow]:
        return self._insights(f"/ad_groups/{quote(ad_group_id, safe='')}/insights", query, "ad_group")

    def get_ad_insights(self, ad_id: str, query: Mapping[str, Any]) -> list[InsightRow]:
        return self._insights(f"/ads/{quote(ad_id, safe='')}/insights", query, "ad")

    def list_conversion_settings(self) -> list[ConversionEventSetting]:
        rows = self.transport.get_paginated("/conversions/event_settings", {"limit": 500})
        self._mark_verified("conversion_settings.read")
        return [self._event_setting(row) for row in rows]

    def list_conversion_sources(self) -> list[ConversionSource]:
        sources: dict[str, ConversionSource] = {}
        rows = self.transport.get_paginated("/conversions/event_settings", {"limit": 500})
        self._mark_verified("conversion_sources.read")
        for row in rows:
            nested = row.get("sources", [])
            if not isinstance(nested, list) or not all(isinstance(item, dict) for item in nested):
                raise AdsApiError("invalid_response", "event setting sources must be a list")
            for item in nested:
                source_id = _required_id(item)
                sources[source_id] = ConversionSource(id=source_id, name=_optional_string(item.get("name")), source=self._source(item))
        return [sources[key] for key in sorted(sources)]

    def get_conversion_insights(self, query: Mapping[str, Any]) -> list[ConversionInsight]:
        self._ensure_account()
        payload = self.transport.request("POST", "/conversions/insights", json_body=dict(query), retryable_request=True)
        self._mark_verified("conversion_insights.read")
        context = self._context(query, str(query.get("aggregation_level", "account")))
        return [ConversionInsight(context=context, entity_id=_optional_string(row.get("entity_id")), conversions=_optional_decimal(row.get("conversions")), conversion_value=_optional_decimal(row.get("conversion_value")), view_through_conversions=_optional_decimal(row.get("view_through_conversions")), source=self._source(row)) for row in _list_data(payload)]

    def _insights(self, path: str, query: Mapping[str, Any], default_grain: str) -> list[InsightRow]:
        self._ensure_account()
        rows = self.transport.get_paginated(path, query)
        self._mark_verified(f"insights.{default_grain}.read")
        return [self._insight(row, query, default_grain) for row in rows]

    def _insight(self, row: Mapping[str, Any], query: Mapping[str, Any], default_grain: str) -> InsightRow:
        grain = str(query.get("aggregation_level", default_grain))
        context = self._context(query, grain, row)
        dimensions = {key: _optional_string(row.get(key)) for key in ("product_id", "country", "device", "platform", "readable_time") if key in row}
        return InsightRow(
            context=context,
            account_id=self._account.id if self._account else None,
            campaign_id=_optional_string(row.get("campaign_id")),
            ad_group_id=_optional_string(row.get("ad_group_id")),
            ad_id=_optional_string(row.get("ad_id")),
            dimensions=dimensions,
            impressions=_optional_int(row.get("impressions")),
            clicks=_optional_int(row.get("clicks")),
            spend=_optional_decimal(row.get("spend")),
            ctr=_optional_decimal(row.get("ctr")),
            cpc=_optional_decimal(row.get("cpc")),
            cpm=_optional_decimal(row.get("cpm")),
            conversions=_optional_decimal(row.get("conversions")),
            conversion_value=_optional_decimal(row.get("conversion_value")),
            view_through_conversions=_optional_decimal(row.get("view_through_conversions")),
            source=self._source(row),
        )

    def _context(self, query: Mapping[str, Any], grain: str, row: Mapping[str, Any] | None = None) -> MeasurementContext:
        row = row or {}
        return MeasurementContext(
            currency=self._account.currency if self._account else None,
            timezone=self._account.timezone if self._account else None,
            attribution_window_days=_optional_int(query.get("attribution_window_days")),
            conversion_definition=_optional_string(query.get("conversion_definition")),
            revenue_definition=_optional_string(query.get("revenue_definition")),
            grain=grain,
            period_start=_timestamp(row.get("start_time")),
            period_end=_timestamp(row.get("end_time")),
        )

    def _event_setting(self, row: Mapping[str, Any]) -> ConversionEventSetting:
        archived = row.get("archived")
        if archived is not None and not isinstance(archived, bool):
            raise AdsApiError("invalid_response", "archived must be a boolean or null")
        return ConversionEventSetting(
            id=_required_id(row),
            event_name=_optional_string(row["event_type"] if "event_type" in row else row.get("custom_event_name") if "custom_event_name" in row else row.get("name")),
            status="archived" if archived is True else "active" if archived is False else None,
            attribution_window_days=_optional_int(row.get("attribution_window_days")),
            source=self._source(row),
        )

    def _source(self, raw: Mapping[str, Any]) -> SourceMetadata:
        return SourceMetadata(provider=self.provider, retrieved_at=datetime.now(timezone.utc), raw=dict(raw))
