"""Tests for ``main._resolve_creds`` — the two-path access-token retrieval
introduced for forcedotcom/cli#3560 (sf CLI v2 redaction, effective
2026-05-27).

Path 1 (primary): ``sf org auth show-access-token --json --no-prompt``
                  via the ``show_access_token`` recipe.
Path 2 (fallback): ``sf org display`` payload with
                   ``SF_TEMP_SHOW_SECRETS=true`` env var.

We mock ``run_sf`` (not subprocess) since these tests target the
orchestration logic in ``main.py``, not the recipe loader. The recipe
loader and subprocess env injection have their own coverage in
``test_sf_cli.py``.
"""
from __future__ import annotations

import unittest
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import main  # type: ignore
from sf_cli import AuthRequired, SfCliError  # type: ignore


REDACTED_TOKEN = "[REDACTED] Use 'sf org auth show-access-token' to view"


def _display_payload(*, instance_url="https://example.salesforce.com",
                     access_token="TOKEN_FROM_DISPLAY"):
    return {"result": {
        "instanceUrl": instance_url,
        "accessToken": access_token,
    }}


def _show_token_payload(*, access_token="TOKEN_FROM_SHOW"):
    return {"result": {"accessToken": access_token}}


class ResolveCredsTests(unittest.TestCase):
    """Cover every branch of the two-path retrieval."""

    def _route(self, *, primary_payload=None, primary_exc=None,
               display_payload=None):
        """Build a ``run_sf`` side-effect that dispatches by recipe name."""
        display = display_payload or _display_payload()
        primary = primary_payload or _show_token_payload()

        def fake_run_sf(name, **params):
            if name == "org_display":
                return display
            if name == "show_access_token":
                if primary_exc is not None:
                    raise primary_exc
                return primary
            raise AssertionError(f"unexpected recipe: {name}")

        return fake_run_sf

    def test_primary_path_returns_show_token(self):
        """Happy path — dedicated command returns a clean token."""
        with mock.patch.object(main, "run_sf", side_effect=self._route()):
            url, token = main._resolve_creds("my-org")
        self.assertEqual(url, "https://example.salesforce.com")
        self.assertEqual(token, "TOKEN_FROM_SHOW")

    def test_primary_unknown_falls_back_to_display(self):
        """Older sf CLI without the dedicated command surfaces SfCliError;
        we fall back to the display payload's accessToken."""
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                primary_exc=SfCliError("sf CLI 'show_access_token' failed"),
            ),
        ):
            url, token = main._resolve_creds("my-org")
        self.assertEqual(url, "https://example.salesforce.com")
        self.assertEqual(token, "TOKEN_FROM_DISPLAY")

    def test_primary_returns_redacted_token_falls_back(self):
        """Edge case: dedicated command runs cleanly but returns the
        placeholder string. Treat as failure and use the display fallback."""
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                primary_payload=_show_token_payload(access_token=REDACTED_TOKEN),
            ),
        ):
            _, token = main._resolve_creds("my-org")
        self.assertEqual(token, "TOKEN_FROM_DISPLAY")

    def test_primary_returns_empty_token_falls_back(self):
        """Empty string from the dedicated command also triggers fallback."""
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                primary_payload=_show_token_payload(access_token=""),
            ),
        ):
            _, token = main._resolve_creds("my-org")
        self.assertEqual(token, "TOKEN_FROM_DISPLAY")

    def test_both_paths_redacted_raises_authrequired(self):
        """If both paths come back redacted/empty, surface AuthRequired
        rather than handing the placeholder to downstream Tooling/REST
        callers (which would 401 with INVALID_AUTH_HEADER)."""
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                primary_payload=_show_token_payload(access_token=REDACTED_TOKEN),
                display_payload=_display_payload(access_token=REDACTED_TOKEN),
            ),
        ):
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
        self.assertIn("could not retrieve a usable access token", str(ctx.exception))

    def test_missing_instance_url_raises_authrequired(self):
        """display returning empty instanceUrl is a hard failure — no
        amount of token-juggling helps if we can't talk to the org."""
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                display_payload=_display_payload(instance_url=""),
            ),
        ):
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
        self.assertIn("instanceUrl", str(ctx.exception))

    def test_primary_path_recipe_name_is_show_access_token(self):
        """Tripwire — the primary call MUST go through the
        ``show_access_token`` recipe. Without it the patch silently
        regresses to the env-var-only path on sf CLI versions that
        already shipped the dedicated command."""
        recipes_called: list[str] = []

        def fake_run_sf(name, **params):
            recipes_called.append(name)
            if name == "org_display":
                return _display_payload()
            if name == "show_access_token":
                return _show_token_payload()
            raise AssertionError(f"unexpected recipe: {name}")

        with mock.patch.object(main, "run_sf", side_effect=fake_run_sf):
            main._resolve_creds("my-org")

        self.assertIn("show_access_token", recipes_called)
        # And the alias was passed through:
        # (We don't capture params here, but the recipe loader enforces
        # required_params at run_sf time — see test_sf_cli.py.)


if __name__ == "__main__":
    unittest.main()
