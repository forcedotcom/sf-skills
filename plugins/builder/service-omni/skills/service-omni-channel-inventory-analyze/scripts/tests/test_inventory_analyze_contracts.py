#!/usr/bin/env python3
from __future__ import annotations

import unittest

from _bootstrap import FakeSf, last_json


CHANNELS = [
    {
        "id": "0N9xx0000000001AAA",
        "label": "Case Email",
        "channelUrl": "/lightning/setup/ServiceChannelSettings/page?address=one",
        "omniChannelInstanceType": "EMAIL",
        "routingType": "QUEUE",
        "routingRequirementId": "00Gxx0000000001AAA",
        "routingRequirementLabel": "Case Queue",
        "routingRequirementUrl": "/lightning/setup/Queues/page?address=one",
        "messages": [],
    },
    {
        "id": "0M0xx0000000002AAA",
        "label": "Support Voice",
        "omniChannelInstanceType": "Voice",
        "routingType": "Flow",
        "routingRequirementLabel": "Voice Routing",
        "messages": [{"severity": "info"}],
    },
]


class InputContractTests(unittest.TestCase):
    def test_missing_org_is_rejected(self):
        with FakeSf() as fake:
            return_code, output, commands = fake.run([])
        self.assertEqual(return_code, 1, output)
        self.assertIn("Usage", output)
        self.assertEqual(commands, "")

    def test_invalid_type_is_blocked_before_api_call(self):
        with FakeSf() as fake:
            return_code, output, commands = fake.run(["org", "--type", "CarrierPigeon"])
        self.assertEqual(return_code, 1, output)
        result = last_json(output)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("Unsupported channel type", result["blocking_issue"])
        self.assertEqual(commands, "")

    def test_unauthenticated_org_is_blocked(self):
        with FakeSf() as fake:
            return_code, output, commands = fake.run(["org"], FAKE_AUTH="fail")
        self.assertEqual(return_code, 1, output)
        self.assertEqual(last_json(output)["status"], "blocked")
        self.assertEqual(commands, "")


class InventoryContractTests(unittest.TestCase):
    def test_raw_array_is_normalized_and_summarized(self):
        with FakeSf() as fake:
            return_code, output, commands = fake.run(["org"], FAKE_API_BODY=CHANNELS)
        self.assertEqual(return_code, 0, output)
        result = last_json(output)
        self.assertEqual(result["status"], "analyzed")
        self.assertEqual(result["summary"]["total_configured"], 2)
        self.assertEqual(result["summary"]["returned"], 2)
        self.assertEqual(result["summary"]["by_channel_type"], {"Email": 1, "Voice": 1})
        self.assertEqual(result["summary"]["by_routing_type"], {"Flow": 1, "Queue": 1})
        self.assertIn("--method POST", commands)
        self.assertIn(
            "/services/data/v66.0/headless/invoke",
            commands,
        )
        self.assertIn("OmniChannelInstancesController", commands)
        self.assertIn("getChannelInstances", commands)
        self.assertNotRegex(commands, r"--method (GET|PATCH|DELETE)")

    def test_direct_invocation_envelope_is_unwrapped(self):
        with FakeSf() as fake:
            return_code, output, _ = fake.run(
                ["org"],
                FAKE_API_BODY={"status_code": 200, "body": CHANNELS},
            )
        self.assertEqual(return_code, 0, output)
        result = last_json(output)
        self.assertEqual(result["status"], "analyzed")
        self.assertEqual(result["summary"]["total_configured"], 2)

    def test_type_filter_is_case_insensitive(self):
        with FakeSf() as fake:
            return_code, output, _ = fake.run(["org", "--type", "voice"], FAKE_API_BODY={"result": CHANNELS})
        self.assertEqual(return_code, 0, output)
        result = last_json(output)
        self.assertEqual(result["filter"], "Voice")
        self.assertEqual(result["summary"]["total_configured"], 2)
        self.assertEqual(result["summary"]["returned"], 1)
        self.assertEqual(result["instances"][0]["label"], "Support Voice")

    def test_empty_inventory_is_valid(self):
        with FakeSf() as fake:
            return_code, output, _ = fake.run(["org"], FAKE_API_BODY=[])
        self.assertEqual(return_code, 0, output)
        result = last_json(output)
        self.assertEqual(result["status"], "analyzed")
        self.assertEqual(result["instances"], [])
        self.assertEqual(result["summary"]["total_configured"], 0)

    def test_permission_failure_is_not_reported_as_empty(self):
        with FakeSf() as fake:
            return_code, output, _ = fake.run(
                ["org"],
                FAKE_API_STATUS="fail",
                FAKE_API_ERROR="INSUFFICIENT_ACCESS: permission denied",
            )
        self.assertEqual(return_code, 1, output)
        result = last_json(output)
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["summary"]["total_configured"])
        self.assertIn("View Setup", result["blocking_issue"])

    def test_inner_dispatch_failure_is_blocked(self):
        with FakeSf() as fake:
            return_code, output, _ = fake.run(
                ["org"],
                FAKE_API_BODY={"status_code": 403, "body": {"message": "permission denied"}},
            )
        self.assertEqual(return_code, 1, output)
        result = last_json(output)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("View Setup", result["blocking_issue"])

    def test_malformed_response_is_blocked(self):
        with FakeSf() as fake:
            return_code, output, _ = fake.run(["org"], FAKE_API_BODY={"unexpected": "shape"})
        self.assertEqual(return_code, 1, output)
        result = last_json(output)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("unsupported response shape", result["blocking_issue"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
