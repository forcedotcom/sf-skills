"""Tests for ``resolve_bot`` — Bot + version resolution helpers + main flow.

Covers the small pure helpers (``scrub``, ``natural_key``,
``emit_error_block``) plus a happy-path ``main`` end-to-end with
``subprocess.run`` mocked.
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import resolve_bot  # type: ignore


# -----------------------------------------------------------------------------
# scrub
# -----------------------------------------------------------------------------


class ScrubTests(unittest.TestCase):

    def test_strips_dangerous_shell_chars(self):
        # ` $ " \\ \r \t \0 \n all stripped; safe chars kept verbatim.
        self.assertEqual(
            resolve_bot.scrub("hello`bad$\"" + "\n" + "world"),
            "hellobadworld",
        )

    def test_strips_carriage_return_and_tab(self):
        self.assertEqual(resolve_bot.scrub("a\tb\rc"), "abc")

    def test_returns_empty_string_for_none(self):
        self.assertEqual(resolve_bot.scrub(None), "")

    def test_coerces_non_strings(self):
        self.assertEqual(resolve_bot.scrub(42), "42")

    def test_passes_safe_chars_through(self):
        self.assertEqual(resolve_bot.scrub("Customer_Support_Agent"),
                         "Customer_Support_Agent")


# -----------------------------------------------------------------------------
# natural_key — version sorting
# -----------------------------------------------------------------------------


class NaturalKeyTests(unittest.TestCase):

    def test_sorts_v10_after_v9(self):
        keys = ["v9", "v10", "v2", "v1"]
        keys.sort(key=resolve_bot.natural_key, reverse=True)
        self.assertEqual(keys, ["v10", "v9", "v2", "v1"])

    def test_handles_none_and_empty_string(self):
        # Both should be safe (empty list)
        self.assertEqual(resolve_bot.natural_key(""), [""])
        self.assertEqual(resolve_bot.natural_key(None), [""])


# -----------------------------------------------------------------------------
# emit_error_block — terminal RESULT block + sys.exit
# -----------------------------------------------------------------------------


class EmitErrorBlockTests(unittest.TestCase):

    def test_emits_result_block_and_exits_one(self):
        old_env = dict(os.environ)
        os.environ["AGENT_API_NAME"] = "MyAgent"
        os.environ["ORG_ID_15"] = "00D000000000000"
        os.environ["ORG_ID_18"] = "00D000000000000EAA"
        os.environ.pop("ERROR_TEE", None)
        try:
            with mock.patch.object(resolve_bot.sys, "stdout") as out:
                with self.assertRaises(SystemExit) as ctx:
                    resolve_bot.emit_error_block(
                        "AGENT_NOT_FOUND", "details here", {"AVAILABLE_BOTS": "A,B"},
                    )
            self.assertEqual(ctx.exception.code, 1)
            written = "".join(c.args[0] for c in out.write.call_args_list)
            self.assertIn("STATUS=AGENT_NOT_FOUND", written)
            self.assertIn("ERROR_DETAIL=details here", written)
            self.assertIn("AGENT_API_NAME=MyAgent", written)
            self.assertIn("AVAILABLE_BOTS=A,B", written)
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_writes_error_tee_when_env_set(self):
        with TemporaryDirectory() as t:
            tee_path = Path(t) / "subdir" / "tee.txt"
            old_env = dict(os.environ)
            os.environ["ERROR_TEE"] = str(tee_path)
            os.environ["AGENT_API_NAME"] = "MyAgent"
            os.environ["ORG_ID_15"] = "x"
            os.environ["ORG_ID_18"] = "y"
            try:
                with mock.patch.object(resolve_bot.sys, "stdout"):
                    with self.assertRaises(SystemExit):
                        resolve_bot.emit_error_block("X", "y", {})
                # tee_path got the same content
                self.assertTrue(tee_path.is_file())
                self.assertIn("STATUS=X", tee_path.read_text())
            finally:
                os.environ.clear()
                os.environ.update(old_env)


# -----------------------------------------------------------------------------
# main — happy path with mocked sf data query
# -----------------------------------------------------------------------------


def _versions_payload() -> str:
    return json.dumps({
        "result": {
            "records": [
                {"DeveloperName": "v3", "Status": "Active",
                 "BotDefinitionId": "0Xx000000000ABC",
                 "BotDefinition": {"DeveloperName": "MyAgent",
                                   "MasterLabel": "My Agent"}},
                {"DeveloperName": "v2", "Status": "Inactive",
                 "BotDefinitionId": "0Xx000000000ABC",
                 "BotDefinition": {"DeveloperName": "MyAgent",
                                   "MasterLabel": "My Agent"}},
            ],
        },
    })


def _bot_def_payload() -> str:
    return json.dumps({
        "result": {
            "records": [
                {"DeveloperName": "MyAgent", "MasterLabel": "My Agent",
                 "Description": "demo", "AgentType": "Internal",
                 "Type": "AiCopilot", "AgentTemplate": "T",
                 "BotSource": "AgentforceAgentCopilot"},
            ],
        },
    })


class MainTests(unittest.TestCase):

    def _run_main(self, *, agent_version: str = "") -> tuple[int, str]:
        old_env = dict(os.environ)
        with TemporaryDirectory() as t:
            tmp = Path(t)
            os.environ["ORG_ALIAS"] = "my-org"
            os.environ["AGENT_API_NAME"] = "MyAgent"
            os.environ["WORK_DIR"] = str(tmp)
            os.environ["AGENT_VERSION"] = agent_version

            calls: list = []

            def fake_run(argv, **kw):
                # Two distinct sf data queries: BotVersion then BotDefinition
                calls.append(argv)
                if "BotVersion" in argv[-1]:
                    return SimpleNamespace(returncode=0, stdout=_versions_payload(), stderr="")
                if "BotDefinition" in argv[-1]:
                    return SimpleNamespace(returncode=0, stdout=_bot_def_payload(), stderr="")
                return SimpleNamespace(returncode=0, stdout="{}", stderr="")

            stdout_buf: list[str] = []

            try:
                with mock.patch.object(resolve_bot.subprocess, "run", side_effect=fake_run):
                    with mock.patch.object(resolve_bot.sys, "stdout") as out:
                        out.write = lambda s: stdout_buf.append(s)
                        rc = resolve_bot.main()
            finally:
                os.environ.clear()
                os.environ.update(old_env)
        return rc, "".join(stdout_buf)

    def test_main_succeeds_with_auto_pick(self):
        rc, written = self._run_main()
        self.assertEqual(rc, 0)
        # v3 is Active and lexically highest → auto-picked
        self.assertIn("AGENT_VERSION=v3", written)
        self.assertIn("VERSION_AUTO_PICKED=true", written)
        self.assertIn("BOT_FOUND=true", written)
        self.assertIn("BOT_ID=0Xx000000000ABC", written)

    def test_main_succeeds_with_explicit_version_match(self):
        rc, written = self._run_main(agent_version="v2")
        self.assertEqual(rc, 0)
        self.assertIn("AGENT_VERSION=v2", written)
        self.assertIn("VERSION_AUTO_PICKED=false", written)


if __name__ == "__main__":
    unittest.main()
