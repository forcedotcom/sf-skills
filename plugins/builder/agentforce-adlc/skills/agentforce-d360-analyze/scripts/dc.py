"""Data Cloud queries for investigating-agentforce-d360.

Two responsibilities:

1. **Templates.** `load_sql(name, **params)` reads `assets/dc/*.sql` and
   substitutes `{{PLACEHOLDER}}` values. `parse(response)` turns a DC
   query response into a list of row dicts. Neither knows specific
   column names — those live in the .sql files.

2. **Transport.** `resolve_org(alias)` shells out to `sf org display`
   for the instance URL and `sf org auth show-access-token` for the
   access token. `post(sql, instance_url, token)`
   POSTs the SQL to the Data Cloud Query API and returns parsed rows.
   Errors route through `DCQueryError` with the full response body + SQL
   context so callers can surface a useful message.
   `default_target_org()` reads the sf CLI default target org for entry
   points invoked without `--org`. Both it and `resolve_org` run the
   `show-access-token` capability preflight as their first sf call, so on
   either path a too-old CLI fails with the upgrade message first.

Persistence lives in `storage.save`.
"""
from __future__ import annotations

import json
import re
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


# Token-redaction patterns, vendored from agentforce-architecture-analyze's
# rest_client (this skill is self-contained and must not import across
# skills). sf CLI failure output can echo the access token — e.g. a
# `show-access-token --json` run that exits non-zero with the payload on
# stdout — so every stderr/stdout string is scrubbed before it reaches a
# SystemExit message. Deliberately permissive: over-redact, never leak.
_AUTH_HEADER_RE = re.compile(r"(Authorization\s*:\s*Bearer\s+)\S+", re.IGNORECASE)  # @rule-suppress starter-sec-002 — re.compile, not exec/eval
_BEARER_RE = re.compile(r"(\bBearer\s+)[^\s\"']+", re.IGNORECASE)  # @rule-suppress starter-sec-002 — re.compile, not exec/eval
_ACCESS_TOKEN_QS_RE = re.compile(r"(access[_]?token\s*=\s*)[^&\s\"']+", re.IGNORECASE)  # @rule-suppress starter-sec-002 — re.compile, not exec/eval
_ACCESS_TOKEN_JSON_RE = re.compile(r"(\"access[_]?token\"\s*:\s*\")[^\"]*", re.IGNORECASE)  # @rule-suppress starter-sec-002 — re.compile, not exec/eval


def _redact_text(text: str | None) -> str:
    """Scrub bearer tokens and accessToken values from sf CLI output."""
    if not text:
        return ""
    text = _AUTH_HEADER_RE.sub(r"\1<redacted>", text)
    text = _BEARER_RE.sub(r"\1<redacted>", text)
    text = _ACCESS_TOKEN_QS_RE.sub(r"\1<redacted>", text)
    text = _ACCESS_TOKEN_JSON_RE.sub(r"\1<redacted>", text)
    return text


def _run_sf_json(argv: list[str]) -> dict:
    """Shell out + parse JSON. SystemExits on FileNotFoundError /
    CalledProcessError so callers get a clean message instead of a stack.
    Failure output is redacted before it is surfaced."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise SystemExit("sf CLI not found on PATH — install Salesforce CLI first")
    except subprocess.CalledProcessError as e:
        detail = _redact_text((e.stderr or "").strip() or (e.stdout or "").strip())
        raise SystemExit(f"{' '.join(argv[:4])}... failed:\n{detail}") from None
    return json.loads(r.stdout)


_show_access_token_capability_ok = False
"""Set once the preflight succeeds; the check then never reruns in this
process. Failures are NOT cached, so a fixed PATH/upgrade is picked up on
the next call."""

_SHOW_ACCESS_TOKEN_HELP_SIGNATURE_RE = re.compile(
    r"\$\s*sf\s+org\s+auth\s+show-access-token\b"
)
"""USAGE-line form that real `--help` output always contains
(`$ sf org auth show-access-token -o <value> ...`). The bare command name is
not enough: unknown-command notices echo it too
(`Command org:auth:show-access-token not found`,
`show-access-token is not a sf command`). A zero-exit probe whose output
lacks the USAGE form is treated as a failed check."""

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def _assert_show_access_token_capability() -> None:
    """Fail fast if the installed sf CLI lacks `sf org auth show-access-token`.

    That command is the only supported token-retrieval path
    (forcedotcom/cli#3560). Probing `--help` needs no org auth and turns a
    confusing downstream failure into an actionable upgrade message.
    `default_target_org` and `resolve_org` each call this first, ahead of
    every other sf call they make. A successful probe is cached for the
    process lifetime, so the second call costs nothing.

    Exit status alone is not trusted: a CLI build that answers an unknown
    command with exit 0 (e.g. printing top-level help or a "not found"
    notice) would otherwise pass. The probe therefore also requires the
    command's USAGE line (`$ sf org auth show-access-token`) in the
    ANSI-stripped stdout+stderr; if it is absent the check fails and is not
    cached.
    """
    global _show_access_token_capability_ok
    if _show_access_token_capability_ok:
        return
    try:
        proc = subprocess.run(
            ["sf", "org", "auth", "show-access-token", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "sf CLI not found on PATH — install Salesforce CLI first"
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (
            _redact_text((exc.stderr or "").strip() or (exc.stdout or "").strip())
            or "unknown error"
        )
        raise SystemExit(
            "sf CLI is missing required command "
            "'sf org auth show-access-token'. Upgrade/reinstall Salesforce CLI "
            "to a build that provides this command, then retry.\n"
            f"Preflight detail: {detail}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            "sf CLI capability preflight for 'sf org auth show-access-token' "
            "timed out after 30s"
        ) from exc
    help_text = _ANSI_ESCAPE_RE.sub(
        "", f"{proc.stdout or ''}\n{proc.stderr or ''}",
    )
    if not _SHOW_ACCESS_TOKEN_HELP_SIGNATURE_RE.search(help_text):
        # Zero exit without the command's help signature — the CLI did not
        # recognise the command. Fail (uncached) like a non-zero exit.
        # Redact before truncating so a token can never be split past the regex.
        detail = (
            _redact_text(help_text.strip())[:500]
            or "help output lacked the command signature"
        )
        raise SystemExit(
            "sf CLI is missing required command "
            "'sf org auth show-access-token'. Upgrade/reinstall Salesforce CLI "
            "to a build that provides this command, then retry.\n"
            f"Preflight detail: {detail}"
        )
    _show_access_token_capability_ok = True


NO_DEFAULT_ORG_MSG = (
    "no --org given and no default target org set — run "
    "`sf config set target-org <alias>` or pass --org <alias>"
)


def default_target_org() -> str:
    """Return the sf CLI default target org alias/username.

    Used by entry points when ``--org`` is omitted ("my org" means the CLI
    default). Reads ``.result[0].value`` from
    ``sf config get target-org --json``. Raises SystemExit with a clear,
    redacted message when the CLI is missing, fails, times out, returns
    non-JSON, or has no default set.

    The show-access-token capability preflight runs first, before
    ``sf config get``. A CLI too old to fetch a token then fails with the
    upgrade/reinstall message, not a misleading "no default org" message.
    The preflight is cached per process, so the later ``resolve_org`` call
    does not probe again.
    """
    _assert_show_access_token_capability()
    argv = ["sf", "config", "get", "target-org", "--json"]
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=30, check=True,
        )
    except FileNotFoundError:
        raise SystemExit(
            "sf CLI not found on PATH — install Salesforce CLI first"
        ) from None
    except subprocess.CalledProcessError as exc:
        detail = (
            _redact_text((exc.stderr or "").strip() or (exc.stdout or "").strip())
            or "unknown error"
        )
        raise SystemExit(
            f"{NO_DEFAULT_ORG_MSG}\n`sf config get target-org` failed: {detail}"
        ) from None
    except subprocess.TimeoutExpired:
        raise SystemExit(
            f"{NO_DEFAULT_ORG_MSG}\n`sf config get target-org` timed out after 30s"
        ) from None
    try:
        payload = json.loads(proc.stdout or "")
    except json.JSONDecodeError:
        raise SystemExit(
            f"{NO_DEFAULT_ORG_MSG}\n`sf config get target-org --json` returned "
            f"non-JSON output: {_redact_text(proc.stdout.strip())[:200]}"
        ) from None
    result = payload.get("result") if isinstance(payload, dict) else None
    first = result[0] if isinstance(result, list) and result else {}
    value = first.get("value") if isinstance(first, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(NO_DEFAULT_ORG_MSG)
    return value.strip()


def resolve_org(alias: str) -> tuple[str, str]:
    """Resolve instanceUrl + accessToken for the sf org alias.

    Token retrieval is fail-fast (forcedotcom/cli#3560): the access token
    comes ONLY from `sf org auth show-access-token --json --no-prompt`.
    `sf org display --json --verbose` is used for non-secret metadata
    (instanceUrl); any `accessToken` it carries is ignored.

    Raises SystemExit on CLI failure — this is the one thing every
    downstream operation depends on, so a clean early exit is friendlier
    than a stack trace.
    """
    # Step 1: capability preflight first, so a missing sf binary or missing
    # command yields the actionable preflight error (cached once it passes).
    _assert_show_access_token_capability()

    # Step 2: org_display for instanceUrl (non-secret metadata only).
    display = _run_sf_json(
        ["sf", "org", "display", "--target-org", alias, "--json", "--verbose"],
    )["result"]
    instance_url = display.get("instanceUrl") or ""
    if not instance_url:
        raise SystemExit(
            f"sf org display returned no instanceUrl for alias {alias!r}"
        )

    # Step 3: dedicated command is the only token source.
    try:
        token_payload = _run_sf_json(
            ["sf", "org", "auth", "show-access-token",
             "--target-org", alias, "--json", "--no-prompt"],
        )
    except (SystemExit, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"could not retrieve access token for alias {alias!r} via "
            "sf org auth show-access-token; ensure the org is authenticated "
            f"(sf org login web --alias {alias}).\nDetail: {exc}"
        ) from exc

    token_result = token_payload.get("result") or {}
    access_token = token_result.get("accessToken") or ""

    if not access_token or _REDACTION_MARKER_FRAGMENT in access_token:
        raise SystemExit(
            f"could not retrieve a usable access token for alias {alias!r} "
            "via sf org auth show-access-token. Ensure sf CLI is logged in "
            "for this org and the command returned a real token."
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
