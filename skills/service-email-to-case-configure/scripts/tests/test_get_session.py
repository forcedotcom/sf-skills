"""Tests for get_session's access-token acquisition and _usable_access_token.

The FakeOrg-based suites patch get_session wholesale, so they never exercise the
token-selection logic. This module covers it directly:

  * _usable_access_token — accept a live `<orgId>!<secret>` token, reject the
    `[REDACTED ...]` marker recent CLIs emit, and reject None/empty/non-string.
  * get_session — prefer `sf org auth show-access-token`; on a redacted or
    missing primary token, fall back to a `--verbose` `sf org display`; hard-fail
    when neither yields a usable token.

All `sf` invocations are mocked at the sf_json / sf_json_optional layer — no
live org required.
"""
from __future__ import annotations

import unittest
from unittest import mock

from . import _bootstrap

apply_mod = _bootstrap.load_apply()

# A value shaped like a live Salesforce session token: <orgId>!<secret>.
REAL_TOKEN = "00D000000000001AAA!AQ" + "x" * 90
# The marker recent CLIs return from `sf org display` in place of the token.
REDACTED = "[REDACTED] Use 'sf org auth show-access-token' to view the token"

DISPLAY = {
    "instanceUrl": "https://example.my.salesforce.com",
    "username": "auth@example.com",
    "apiVersion": "68.0",
}


def _dispatch(show_at, verbose):
    """Build an sf_json_optional stand-in that returns ``show_at`` for the
    show-access-token call and ``verbose`` for the `--verbose` display call."""
    def _impl(args):
        if "show-access-token" in args:
            return show_at
        if "--verbose" in args:
            return verbose
        return None
    return _impl


class UsableAccessToken(unittest.TestCase):
    """_usable_access_token: live token has '!' and is not the redaction marker."""

    def test_real_token(self):
        self.assertTrue(apply_mod._usable_access_token(REAL_TOKEN))

    def test_redaction_marker_rejected(self):
        self.assertFalse(apply_mod._usable_access_token(REDACTED))

    def test_none_rejected(self):
        self.assertFalse(apply_mod._usable_access_token(None))

    def test_empty_rejected(self):
        self.assertFalse(apply_mod._usable_access_token(""))

    def test_token_without_separator_rejected(self):
        self.assertFalse(apply_mod._usable_access_token("noseparator" + "x" * 40))

    def test_non_string_rejected(self):
        self.assertFalse(apply_mod._usable_access_token(12345))


class GetSessionTokenAcquisition(unittest.TestCase):
    """get_session: primary show-access-token, verbose fallback, hard-fail."""

    def setUp(self):
        # get_session derives API_VERSION from the org unless forced; keep the
        # derivation path deterministic regardless of test ordering.
        apply_mod._API_VERSION_EXPLICIT = False

    def _run(self, show_at, verbose):
        opt = mock.MagicMock(side_effect=_dispatch(show_at, verbose))
        with mock.patch.object(apply_mod, "sf_json", return_value=dict(DISPLAY)), \
                mock.patch.object(apply_mod, "sf_json_optional", opt):
            result = apply_mod.get_session("myorg")
        return result, opt

    @staticmethod
    def _verbose_calls(opt):
        return [c for c in opt.call_args_list if "--verbose" in c.args[0]]

    def test_primary_path_uses_show_access_token(self):
        (token, md_url, inst, user), opt = self._run(
            show_at={"accessToken": REAL_TOKEN},
            verbose={"accessToken": "should-not-be-used!"})
        self.assertEqual(token, REAL_TOKEN)
        self.assertEqual(inst, DISPLAY["instanceUrl"])
        self.assertEqual(user, DISPLAY["username"])
        self.assertEqual(
            md_url, f"{DISPLAY['instanceUrl']}/services/Soap/m/68.0")
        # Happy path must not issue the verbose fallback display.
        self.assertEqual(self._verbose_calls(opt), [])

    def test_primary_path_accepts_bare_string_result(self):
        # Defensive: if a CLI version returns the token as a bare string in
        # `result` (not an {accessToken} object), get_session must still use it.
        (token, *_), opt = self._run(
            show_at=REAL_TOKEN,
            verbose={"accessToken": "should-not-be-used!"})
        self.assertEqual(token, REAL_TOKEN)
        self.assertEqual(self._verbose_calls(opt), [])

    def test_redacted_primary_falls_back_to_verbose_display(self):
        (token, *_), opt = self._run(
            show_at={"accessToken": REDACTED},
            verbose={"accessToken": REAL_TOKEN})
        self.assertEqual(token, REAL_TOKEN)
        self.assertEqual(len(self._verbose_calls(opt)), 1)

    def test_missing_subcommand_falls_back_to_verbose_display(self):
        (token, *_), opt = self._run(
            show_at=None, verbose={"accessToken": REAL_TOKEN})
        self.assertEqual(token, REAL_TOKEN)
        self.assertEqual(len(self._verbose_calls(opt)), 1)

    def test_redacted_everywhere_exits(self):
        with self.assertRaises(SystemExit):
            self._run(show_at={"accessToken": REDACTED},
                      verbose={"accessToken": REDACTED})

    def test_no_token_anywhere_exits(self):
        with self.assertRaises(SystemExit):
            self._run(show_at=None, verbose=None)


if __name__ == "__main__":
    unittest.main()
