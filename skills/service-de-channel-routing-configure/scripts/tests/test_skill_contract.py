#!/usr/bin/env python3
import unittest
from pathlib import Path


class ExistingAsaRouteTests(unittest.TestCase):
    def test_noop_revalidates_bot_user_and_active_version(self):
        skill = Path(__file__).resolve().parents[2] / "SKILL.md"
        source = skill.read_text()
        noop_contract = source.split(
            "If `SessionHandlerId` is non-null", 1
        )[1].split("For other prefixes", 1)[0]

        self.assertIn("0Xx) sf data query", noop_contract)
        self.assertIn("BotUserId", noop_contract)
        self.assertIn("WHERE Status='Active'", noop_contract)
        self.assertIn("require a non-null `BotUserId`", noop_contract)
        self.assertIn(
            '{"ok":false,"kind":"asa-target-inactive"',
            noop_contract,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
