#!/usr/bin/env python3
from __future__ import annotations

import unittest

from _bootstrap import FakeSf, last_json


class InputContractTests(unittest.TestCase):
    def test_missing_org_is_rejected(self):
        with FakeSf() as fake:
            return_code, output, commands = fake.run([])
        self.assertEqual(return_code, 1, output)
        self.assertIn("Usage", output)
        self.assertEqual(commands, "")

    def test_invalid_routing_model_is_blocked_before_query(self):
        with FakeSf() as fake:
            return_code, output, commands = fake.run(["org", "--routing-model", "future"])
        self.assertEqual(return_code, 1, output)
        self.assertEqual(last_json(output)["status"], "blocked")
        self.assertEqual(commands, "")

    def test_invalid_maximum_is_blocked_before_query(self):
        with FakeSf() as fake:
            return_code, output, commands = fake.run(["org", "--max-psrs", "0"])
        self.assertEqual(return_code, 1, output)
        self.assertIn("1 through 1000000", last_json(output)["blocking_issue"])
        self.assertEqual(commands, "")

    def test_unauthenticated_org_is_blocked(self):
        with FakeSf() as fake:
            return_code, output, commands = fake.run(["org"], FAKE_AUTH="fail")
        self.assertEqual(return_code, 1, output)
        self.assertEqual(last_json(output)["status"], "blocked")
        self.assertEqual(commands, "")


class LimitsContractTests(unittest.TestCase):
    def test_enhanced_report_uses_live_count_and_reference_default(self):
        with FakeSf() as fake:
            return_code, output, commands = fake.run(["org"])
        self.assertEqual(return_code, 0, output)
        result = last_json(output)
        current = result["metrics"]["current_pending_service_routings"]
        hourly = result["metrics"]["pending_service_routing_rate_per_hour"]
        self.assertEqual(current["used"], 2)
        self.assertEqual(current["limit"], 300000)
        self.assertEqual(current["limit_source"], "reference_default")
        self.assertTrue(current["usage_is_approximate"])
        self.assertIsNone(hourly["used"])
        self.assertIsNone(hourly["usage_percent"])
        self.assertIn("SELECT COUNT() FROM PendingServiceRouting", commands)
        self.assertNotRegex(commands, r"\b(create|update|delete|deploy)\b")

    def test_legacy_model_selects_legacy_reference_default(self):
        with FakeSf() as fake:
            return_code, output, _ = fake.run(["org", "--routing-model", "legacy"])
        self.assertEqual(return_code, 0, output)
        result = last_json(output)
        self.assertEqual(result["routing_model"], "legacy")
        self.assertEqual(result["metrics"]["current_pending_service_routings"]["limit"], 200000)

    def test_admin_maximum_is_labeled_and_not_api_verified(self):
        with FakeSf() as fake:
            return_code, output, _ = fake.run(["org", "--max-psrs", "500000"])
        self.assertEqual(return_code, 0, output)
        metric = last_json(output)["metrics"]["current_pending_service_routings"]
        self.assertEqual(metric["limit"], 500000)
        self.assertEqual(metric["limit_source"], "admin_supplied")
        self.assertFalse(metric["limit_verified_by_api"])

    def test_aggregate_expr0_shape_is_supported(self):
        body = {"status": 0, "result": {"totalSize": 1, "records": [{"expr0": 17}]}}
        with FakeSf() as fake:
            return_code, output, _ = fake.run(["org"], FAKE_QUERY_BODY=body)
        self.assertEqual(return_code, 0, output)
        used = last_json(output)["metrics"]["current_pending_service_routings"]["used"]
        self.assertEqual(used, 17)

    def test_unavailable_object_is_blocked_not_zero(self):
        body = {"status": 1, "name": "INVALID_TYPE", "message": "sObject type is not supported"}
        with FakeSf() as fake:
            return_code, output, _ = fake.run(["org"], FAKE_QUERY_STATUS="fail", FAKE_QUERY_BODY=body)
        self.assertEqual(return_code, 1, output)
        result = last_json(output)
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["metrics"])
        self.assertIn("usage was not treated as zero", result["blocking_issue"])

    def test_malformed_success_is_blocked(self):
        with FakeSf() as fake:
            return_code, output, _ = fake.run(["org"], FAKE_QUERY_BODY={"status": 0, "result": {}})
        self.assertEqual(return_code, 1, output)
        self.assertEqual(last_json(output)["status"], "blocked")


if __name__ == "__main__":
    unittest.main(verbosity=2)
