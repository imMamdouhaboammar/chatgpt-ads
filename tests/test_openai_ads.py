"""Synthetic documented-shape contracts; never evidence of live account support."""
from __future__ import annotations

import json
import socket
import unittest
from decimal import Decimal

from chatgpt_ads_brain.capabilities import CapabilityStatus
from chatgpt_ads_brain.openai_ads import (
    AdsApiError,
    AdsApiTransport,
    OpenAIAdsAdapter,
    TransportResponse,
)


class FakeSender:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def response(status, value, headers=None):
    body = value if isinstance(value, bytes) else json.dumps(value).encode()
    return TransportResponse(status, headers or {}, body)


class AdsApiTransportTests(unittest.TestCase):
    def test_missing_key_is_explicit_and_request_is_not_sent(self):
        sender = FakeSender()
        transport = AdsApiTransport(api_key="", sender=sender)
        with self.assertRaisesRegex(AdsApiError, "not_configured"):
            transport.request("GET", "/ad_account")
        self.assertEqual(sender.requests, [])

    def test_authentication_permission_and_client_errors_are_not_retried(self):
        for status, code in ((401, "authentication_failed"), (403, "permission_denied"), (400, "invalid_request")):
            with self.subTest(status=status):
                sender = FakeSender(response(status, {"error": "secret sk-private"}))
                transport = AdsApiTransport(api_key="sk-private", sender=sender)
                with self.assertRaises(AdsApiError) as caught:
                    transport.request("GET", "/ad_account")
                self.assertEqual(caught.exception.code, code)
                self.assertNotIn("sk-private", str(caught.exception))
                self.assertEqual(len(sender.requests), 1)

    def test_rate_limit_and_server_errors_retry_with_bounded_backoff(self):
        sleeps = []
        sender = FakeSender(
            response(429, {}, {"Retry-After": "0.25"}),
            response(503, {}),
            response(200, {"id": "adacct_1"}),
        )
        transport = AdsApiTransport(api_key="key", sender=sender, sleeper=sleeps.append, max_retries=2)
        self.assertEqual(transport.request("GET", "/ad_account")["id"], "adacct_1")
        self.assertEqual(len(sender.requests), 3)
        self.assertEqual(sleeps, [0.25, 1.0])

    def test_timeout_retries_then_returns_structured_error(self):
        sender = FakeSender(socket.timeout(), socket.timeout())
        transport = AdsApiTransport(api_key="key", sender=sender, sleeper=lambda _: None, max_retries=1)
        with self.assertRaises(AdsApiError) as caught:
            transport.request("GET", "/ad_account")
        self.assertEqual(caught.exception.code, "timeout")
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(len(sender.requests), 2)

    def test_malformed_response_and_unsafe_path_fail_closed(self):
        transport = AdsApiTransport(api_key="key", sender=FakeSender(response(200, b"not-json")))
        with self.assertRaisesRegex(AdsApiError, "invalid_response"):
            transport.request("GET", "/ad_account")
        with self.assertRaises(ValueError):
            transport.request("GET", "https://evil.example/path")

    def test_transport_is_strictly_read_only_and_origin_locked(self):
        with self.assertRaises(ValueError):
            AdsApiTransport(api_key="secret", base_url="https://api.ads.openai.com@evil.example/v1")
        transport = AdsApiTransport(api_key="secret", sender=FakeSender())
        with self.assertRaises(ValueError):
            transport.request("POST", "/campaigns", json_body={"name": "mutation"})
        with self.assertRaises(ValueError):
            transport.request("GET", "/ad_account", json_body={"unexpected": True})

    def test_sender_exception_and_invalid_key_are_redacted(self):
        secret = "sk-CONFIDENTIAL"
        sender = FakeSender(ValueError(f"leaked {secret}"))
        with self.assertRaises(AdsApiError) as caught:
            AdsApiTransport(api_key=secret, sender=sender).request("GET", "/ad_account")
        self.assertNotIn(secret, str(caught.exception))
        with self.assertRaises(AdsApiError) as caught:
            AdsApiTransport(api_key="bad\nkey", sender=FakeSender()).request("GET", "/ad_account")
        self.assertNotIn("bad", str(caught.exception))

    def test_pagination_uses_documented_last_id_cursor(self):
        sender = FakeSender(
            response(200, {"object": "list", "data": [{"id": "cmpn_1"}], "last_id": "cmpn_1", "has_more": True}),
            response(200, {"object": "list", "data": [{"id": "cmpn_2"}], "last_id": "cmpn_2", "has_more": False}),
        )
        transport = AdsApiTransport(api_key="key", sender=sender)
        rows = transport.get_paginated("/campaigns", {"limit": 1})
        self.assertEqual([row["id"] for row in rows], ["cmpn_1", "cmpn_2"])
        self.assertIn("after=cmpn_1", sender.requests[1][0].full_url)


class OpenAIAdsAdapterTests(unittest.TestCase):
    def test_account_read_normalizes_documented_shape(self):
        sender = FakeSender(response(200, {
            "id": "adacct_1", "name": "Acme", "url": "https://example.test", "status": "active",
            "timezone": "UTC", "currency_code": "USD", "review": {"status": "approved"},
        }))
        adapter = OpenAIAdsAdapter(AdsApiTransport(api_key="key", sender=sender))
        account = adapter.get_account()
        self.assertEqual((account.id, account.currency, account.review_status), ("adacct_1", "USD", "approved"))
        self.assertNotIn("key", repr(account))
        self.assertTrue(all(state.status is CapabilityStatus.NOT_VERIFIED for state in adapter.capabilities()))
        self.assertTrue(all(not state.account_verified for state in adapter.capabilities()))

    def test_campaign_ad_group_and_ad_lists_normalize_and_paginate(self):
        sender = FakeSender(
            response(200, {"id": "adacct_1", "timezone": "UTC", "currency_code": "USD"}),
            response(200, {"object": "list", "data": [{"id": "cmpn_1", "name": "Launch", "status": "active"}], "has_more": False}),
            response(200, {"object": "list", "data": [{"id": "adgrp_1", "name": "US", "status": "active"}], "has_more": False}),
            response(200, {"object": "list", "data": [{"id": "ad_1", "name": "Card", "status": "active"}], "has_more": False}),
        )
        adapter = OpenAIAdsAdapter(AdsApiTransport(api_key="key", sender=sender))
        self.assertEqual(adapter.list_campaigns()[0].id, "cmpn_1")
        self.assertEqual(adapter.list_ad_groups("cmpn_1")[0].campaign_id, "cmpn_1")
        self.assertEqual(adapter.list_ads("adgrp_1")[0].ad_group_id, "adgrp_1")

    def test_insights_preserve_null_zero_currency_timezone_and_period(self):
        sender = FakeSender(
            response(200, {"id": "adacct_1", "timezone": "UTC", "currency_code": "USD"}),
            response(200, {"object": "list", "data": [{
                "id": "row_1", "campaign_id": "cmpn_1", "start_time": 1735689600, "end_time": 1735776000,
                "impressions": 0, "clicks": None, "spend": 0, "conversions": None,
            }], "has_more": False}),
        )
        adapter = OpenAIAdsAdapter(AdsApiTransport(api_key="key", sender=sender))
        adapter.get_account()
        row = adapter.get_account_insights({"aggregation_level": "campaign"})[0]
        self.assertEqual(row.impressions, 0)
        self.assertIsNone(row.clicks)
        self.assertEqual(row.spend, Decimal("0"))
        self.assertIsNone(row.conversions)
        self.assertEqual((row.context.currency, row.context.timezone, row.context.grain), ("USD", "UTC", "campaign"))
        self.assertLess(row.context.period_start, row.context.period_end)

    def test_conversion_settings_sources_and_insights_remain_distinct(self):
        sender = FakeSender(
            response(200, {"object": "list", "data": [{
                "id": "ces_1", "name": "Purchase", "event_type": "order_created",
                "attribution_window_days": 30, "archived": False,
                "sources": [{"id": "src_1", "name": "Site pixel"}],
            }], "has_more": False}),
            response(200, {"object": "list", "data": [{
                "id": "ces_1", "name": "Purchase", "event_type": "order_created",
                "attribution_window_days": 30, "archived": False,
                "sources": [{"id": "src_1", "name": "Site pixel"}],
            }], "has_more": False}),
            response(200, {"id": "adacct_1", "timezone": "UTC", "currency_code": "USD"}),
            response(200, {"object": "list", "data": [{"entity_id": "cmpn_1", "conversions": 2, "view_through_conversions": 1}], "count": 1}),
        )
        adapter = OpenAIAdsAdapter(AdsApiTransport(api_key="key", sender=sender))
        self.assertEqual(adapter.list_conversion_settings()[0].attribution_window_days, 30)
        self.assertEqual(adapter.list_conversion_sources()[0].id, "src_1")
        conversion = adapter.get_conversion_insights({"aggregation_level": "campaign", "time_ranges": []})[0]
        self.assertEqual(conversion.conversions, Decimal("2"))
        self.assertEqual(conversion.view_through_conversions, Decimal("1"))

    def test_capabilities_do_not_claim_account_verification(self):
        configured = OpenAIAdsAdapter(AdsApiTransport(api_key="key", sender=FakeSender())).capabilities()
        self.assertTrue(all(state.status is CapabilityStatus.NOT_VERIFIED for state in configured if state.configured))
        self.assertTrue(all(not state.account_verified for state in configured))
        missing = OpenAIAdsAdapter(AdsApiTransport(api_key="", sender=FakeSender())).capabilities()
        self.assertTrue(all(state.status is CapabilityStatus.NOT_CONFIGURED for state in missing))


if __name__ == "__main__":
    unittest.main()
