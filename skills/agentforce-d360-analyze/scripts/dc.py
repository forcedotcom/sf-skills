"""Data Cloud queries for investigating-agentforce-d360.

Two responsibilities:

1. **Templates.** `load_sql(name, **params)` reads `assets/dc/*.sql` and
   substitutes `{{PLACEHOLDER}}` values. `parse(response)` turns a DC
   query response into a list of row dicts. Neither knows specific
   column names — those live in the .sql files.

2. **Transport.** `resolve_org(alias)` shells out to `sf org display`
   for the instance URL + access token. `post(sql, instance_url, token)`
   POSTs the SQL to the Data Cloud Query API and returns parsed rows.
   Errors route through `DCQueryError` with the full response body + SQL
   context so callers can surface a useful message.

Persistence lives in `storage.save`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from config import DC_API_PATH

SQL_DIR = Path(__file__).parent.parent / "assets" / "dc"


class DCQueryError(RuntimeError):
    """Data Cloud query failed. Carries full response body + SQL context."""


# ---- templates -------------------------------------------------------------

def load_sql(name: str, **params: str) -> str:
    """Read assets/dc/<name>.sql and substitute {{PARAM}} placeholders.

    Add a new query by dropping a `.sql` file into `assets/dc/` — no
    python edits needed. Callers pass whichever placeholders that
    template defines.
    """
    sql = (SQL_DIR / f"{name}.sql").read_text()
    for key, value in params.items():
        sql = sql.replace(f"{{{{{key}}}}}", value)
    return sql.strip()


def parse(response: dict | None) -> list[dict]:
    """Data Cloud response → list of row dicts. No field knowledge.

    Callers pick whatever columns they need by ssot__* name. Empty list
    means "no response" or "zero rows" — callers decide whether that's
    a partial state worth flagging.
    """
    if not response:
        return []
    return response.get("data") or []


# ---- transport -------------------------------------------------------------

_REDACTION_MARKER_FRAGMENT = "show-access-token"
"""Substring identifying the sf CLI v2 redaction placeholder. The full
literal is `"[REDACTED] Use 'sf org auth show-access-token' to view"`,
but we match on the embedded subcommand name because the surrounding
wording has shifted across sf CLI builds while the subcommand has been
stable since forcedotcom/cli#3560 landed."""


def _run_sf_json(argv: list[str], env: dict | None = None) -> dict:
    """Shell out + parse JSON. SystemExits on FileNotFoundError /
    CalledProcessError so callers get a clean message instead of a stack."""
    try:
        r = subprocess.run(
            argv, capture_output=True, text=True, check=True, env=env,
        )
    except FileNotFoundError:
        raise SystemExit("sf CLI not found on PATH — install Salesforce CLI first")
    except subprocess.CalledProcessError as e:
        raise SystemExit(
            f"{' '.join(argv[:4])}... failed:\n{e.stderr.strip() or e.stdout.strip()}"
        )
    return json.loads(r.stdout)


def resolve_org(alias: str) -> tuple[str, str]:
    """Resolve instanceUrl + accessToken for the sf org alias.

    Two-path strategy per forcedotcom/cli#3560 (effective 2026-05-27):

      1. **Primary** — `sf org display --json --verbose` for instanceUrl,
         then `sf org auth show-access-token --json --no-prompt` for the
         access token. This is the upstream long-term path; the
         `SF_TEMP_SHOW_SECRETS=true` workaround is decommissioned in
         summer 2026.
      2. **Fallback** — if `sf org auth show-access-token` is unknown
         (older sf CLI) OR returns an empty/redacted value, fall back
         to the accessToken from the org_display call which uses
         `SF_TEMP_SHOW_SECRETS=true` env var to bypass the redaction.

    `--verbose` is required on the org_display call: without it, sf CLI
    v2 omits `accessToken` from the JSON entirely (so the fallback
    path needs both `--verbose` and the env var to work).

    Raises SystemExit on CLI failure — this is the one thing every
    downstream operation depends on, so a clean early exit is friendlier
    than a stack trace.
    """
    # Step 1: org_display gives us instanceUrl always; accessToken is
    # the legacy fallback path (redacted unless SF_TEMP_SHOW_SECRETS=true).
    env = {**os.environ, "SF_TEMP_SHOW_SECRETS": "true"}
    display = _run_sf_json(
        ["sf", "org", "display", "--target-org", alias, "--json", "--verbose"],
        env=env,
    )["result"]
    instance_url = display.get("instanceUrl") or ""
    if not instance_url:
        raise SystemExit(
            f"sf org display returned no instanceUrl for alias {alias!r}"
        )

    # Step 2: prefer the dedicated command. Older sf CLI versions emit
    # "is not a sf command" with returncode 0 (warning, not error), so
    # we detect by parsing JSON shape. If the command is unknown the
    # output isn't JSON; we let the json parse error trigger the fallback.
    access_token = ""
    try:
        token_payload = _run_sf_json(
            ["sf", "org", "auth", "show-access-token",
             "--target-org", alias, "--json", "--no-prompt"],
        )
    except (SystemExit, json.JSONDecodeError):
        # Unknown command on older sf CLI → JSON parse fails OR
        # CalledProcessError → SystemExit; either way, fall through.
        pass
    else:
        token_result = token_payload.get("result") or {}
        access_token = token_result.get("accessToken") or ""

    # Fallback: if the dedicated command didn't yield a usable token,
    # try the legacy SF_TEMP_SHOW_SECRETS path via the org_display
    # payload we already have.
    if not access_token or _REDACTION_MARKER_FRAGMENT in access_token:
        legacy = display.get("accessToken") or ""
        if legacy and _REDACTION_MARKER_FRAGMENT not in legacy:
            access_token = legacy

    if not access_token or _REDACTION_MARKER_FRAGMENT in access_token:
        raise SystemExit(
            f"could not retrieve a usable access token for alias {alias!r} "
            f"via sf org auth show-access-token (primary) or sf org display "
            f"(fallback). Ensure sf CLI is logged in for this org."
        )

    return instance_url, access_token


def post(sql: str, instance_url: str, token: str, query_name: str = "") -> list[dict]:
    """POST SQL to Data Cloud Query API, return parsed rows.

    `query_name` is a human label used only for error messages — pass
    the template name (e.g. "sessions") so DCQueryError identifies
    which query failed.
    """
    req = urllib.request.Request(
        f"{instance_url}{DC_API_PATH}",
        data=json.dumps({"sql": sql}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        raise DCQueryError(
            f"query={query_name or '?'} http={e.code}\n"
            f"--- response ({len(err_body)} bytes) ---\n{err_body}\n"
            f"--- sql (first 400 chars) ---\n{sql[:400]}"
        ) from None
    return parse(body)
