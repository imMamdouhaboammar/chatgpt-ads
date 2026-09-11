from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from chatgpt_ads_brain.adapters import AdsAdapter
from chatgpt_ads_brain.capabilities import CapabilityState, CapabilityStatus
from chatgpt_ads_brain.cli import main
from chatgpt_ads_brain.domain import Account, Campaign


class CliAdapter(AdsAdapter):
    provider = "advertiser_api"

    def capabilities(self):
        return (CapabilityState("campaign.read", self.provider, CapabilityStatus.SUPPORTED, "synthetic test transport", configured=True, account_verified=False),)

    def get_account(self):
        return Account("adacct_test", "Test", timezone="UTC", currency="USD")

    def list_campaigns(self):
        return [Campaign("cmpn_1", name="Launch", status="active")]


class ProductCliTests(unittest.TestCase):
    def invoke(self, argv, adapter=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv, adapter=adapter)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_capabilities_json_is_stable_and_does_not_read_secret(self):
        code, out, err = self.invoke(["capabilities", "--json"], CliAdapter())
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["capabilities"][0]["capability"], "campaign.read")
        self.assertEqual(err, "")

    def test_account_status_and_campaign_commands_support_json(self):
        adapter = CliAdapter()
        code, out, _ = self.invoke(["account", "status", "--json"], adapter)
        self.assertEqual((code, json.loads(out)["account"]["currency"]), (0, "USD"))
        code, out, _ = self.invoke(["campaigns", "list", "--json"], adapter)
        self.assertEqual(json.loads(out)["campaigns"][0]["id"], "cmpn_1")
        code, out, _ = self.invoke(["campaigns", "show", "Launch", "--json"], adapter)
        self.assertEqual(json.loads(out)["campaign"]["id"], "cmpn_1")

    def test_missing_configuration_has_safe_error_and_exit_code(self):
        code, out, err = self.invoke(["account", "status", "--json"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        payload = json.loads(err)
        self.assertEqual(payload["error"]["code"], "not_configured")
        self.assertNotIn("Traceback", err)

    def test_unknown_command_is_user_error_without_traceback(self):
        code, _out, err = self.invoke(["not-a-command"])
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
