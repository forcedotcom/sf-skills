"""sf CLI recipe loader — reads assets/cli/*.yaml, runs argv via subprocess.

Security: YAML recipes are loaded via yaml.safe_load only; yaml.load is banned.
PyYAML's `yaml.load` deserializes arbitrary Python objects (including
constructor-injected code in some tags) and must never run on attacker-reachable
YAML. The recipes live inside this repo and are author-controlled, but we
still use `safe_load` as defence in depth — a compromised dist/ or a botched
copy-paste can't escalate to code execution.

the `_SAFE_LOADER` module-level binding is THE loader used everywhere
in this module; tests assert its identity against `yaml.safe_load`.

every stringification of a subprocess.CalledProcessError or related
exception is routed through `rest_client.redact_error` so stderr containing
an access token (rare but observed on some `sf` failure paths) cannot leak
into logs or RESULT blocks.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict

import yaml

from config import CLI_DIR
# hoisted `redact_text` to module-top alongside
# `redact_error`. Previously `_redact_subprocess_stderr` performed a lazy
# import of the module-private `_redact_text` on every call, which (a)
# tied this module to a name that could be renamed silently and (b) meant
# an ImportError from rest_client would surface only at redaction time —
# possibly in a frame whose locals held the raw, un-redacted stderr.
# Hoisting is safe: rest_client does not import sf_cli (no cycle).
from rest_client import redact_error, redact_text

# the ONE allowed loader for this module. Test asserts identity.
# NEVER change this to yaml.load (which can construct arbitrary Python
# objects via tag hooks).
_SAFE_LOADER = yaml.safe_load


class AuthRequired(RuntimeError):
    """sf CLI returned a known auth-failure pattern.

    Carries a redacted stderr snippet — any bearer token in stderr is scrubbed
    via redact_error before reaching this message.
    """


class SfCliError(RuntimeError):
    """sf CLI returned non-zero exit or JSON status != 0.

    Message is redacted  before construction.
    """


_show_access_token_capability_ok = False
"""Set once the preflight succeeds; the check then never reruns in this
process (401-triggered creds refreshes skip it). Failures are NOT cached,
so a fixed PATH/upgrade is picked up on the next call."""

_SHOW_ACCESS_TOKEN_HELP_SIGNATURE_RE = re.compile(
    r"\$\s*sf\s+org\s+auth\s+show-access-token\b"
)
"""USAGE-line form that real ``--help`` output always contains
(``$ sf org auth show-access-token -o <value> ...``). The bare command name
is not enough: unknown-command notices echo it too
(``Command org:auth:show-access-token not found``,
``show-access-token is not a sf command``). A zero-exit probe whose output
lacks the USAGE form is treated as a failed check."""

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def assert_show_access_token_capability() -> None:
    """Fail fast when the installed sf CLI lacks ``sf org auth show-access-token``.

    That command is the only supported runtime token-retrieval path
    (forcedotcom/cli#3560). Probing ``--help`` is cheap, needs no org auth,
    and gives the operator an actionable upgrade message instead of a
    confusing downstream auth failure. A successful probe is cached for
    the process lifetime.

    Exit status alone is not trusted: a CLI build that answers an unknown
    command with exit 0 (e.g. printing top-level help or a "not found"
    notice) would otherwise pass. The probe therefore also requires the
    command's USAGE line (``$ sf org auth show-access-token``) in the
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
        raise SfCliError(
            "sf CLI not found on PATH — install Salesforce CLI first"
        ) from exc
    except subprocess.CalledProcessError as exc:
        safe_detail = _redact_subprocess_stderr(exc.stderr or exc.stdout or "")
        raise SfCliError(
            "sf CLI is missing required command 'sf org auth show-access-token'. "
            "Upgrade/reinstall Salesforce CLI to a version that provides this "
            f"command. Preflight detail: {safe_detail or 'unknown error'}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SfCliError(
            f"sf CLI capability preflight timed out: {redact_error(exc)}"
        ) from exc
    help_text = _ANSI_ESCAPE_RE.sub(
        "", f"{proc.stdout or ''}\n{proc.stderr or ''}",
    )
    if not _SHOW_ACCESS_TOKEN_HELP_SIGNATURE_RE.search(help_text):
        # Zero exit without the command's help signature — the CLI did not
        # recognise the command. Fail (uncached) like a non-zero exit.
        # Redact before truncating so a token can never be split past the regex.
        safe_detail = _redact_subprocess_stderr(help_text.strip())[:500]
        raise SfCliError(
            "sf CLI is missing required command 'sf org auth show-access-token'. "
            "Upgrade/reinstall Salesforce CLI to a version that provides this "
            "command. Preflight detail: "
            f"{safe_detail or 'help output lacked the command signature'}"
        )
    _show_access_token_capability_ok = True


def _load_recipe(name: str) -> Dict[str, Any]:
    """Read and parse a CLI recipe file with yaml.safe_load.

    _SAFE_LOADER is bound to yaml.safe_load at module top; using it
    here (instead of `yaml.safe_load` directly) makes the identity testable
    and gives a single point to review if the loader ever changes.
    """
    path = CLI_DIR / f"{name}.yaml"
    with path.open("r", encoding="utf-8") as fh:
        recipe = _SAFE_LOADER(fh)
    if not isinstance(recipe, dict):
        raise SfCliError(
            f"recipe {name!r} did not parse to a mapping (got {type(recipe).__name__})"
        )
    return recipe


def _sub(arg: str, params: Dict[str, str]) -> str:
    """Substitute {{KEY}} placeholders in a single argv element.

    Input validation: `params` values are expected to be already-validated
    strings (SKILL.md phase 1 runs fs_guard on every user-supplied input).
    We do not revalidate here because argv substitution is shell-escape-safe
    by construction — subprocess.run with a list argv never invokes a shell.
    """
    out = arg
    for key, value in params.items():
        out = out.replace(f"{{{{{key}}}}}", value)
    return out


def _parse_stdout_json(stdout: str) -> Dict[str, Any]:
    """Parse sf CLI's --json stdout.

    sf CLI emits `{"status": 0, "result": {...}}` on success; malformed
    stdout (e.g. when the CLI crashes before JSON serialization) raises
    SfCliError with a redacted message.
    """
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        # stdout could in theory contain a token on some crash paths;
        # redact before surfacing.
        raise SfCliError(
            f"sf CLI stdout is not JSON: {redact_error(e)}"
        ) from None


_AUTH_LINE_PREFIX_RE = re.compile(r"^(?:Error|Warning):\s")  # @rule-suppress starter-sec-002 — re.compile, not python compile()


def _stderr_matches_auth(stderr: str, patterns) -> bool:
    """Check if any auth-failure pattern appears on an Error:/Warning: line.

    previously a substring scan across the entire stderr, which
    false-positived on Node ESM warnings ("Warning: @gthoppae/sf-cli-
    plugin-data360 is a linked ESM module") if they happened to echo an
    auth pattern substring. Now we only match on lines starting with
    `Error:` or `Warning:` followed by whitespace. This keeps every
    true-positive we care about (real sf auth errors always surface as
    `Error: NoOrgAuthenticationError ...`) while pruning the noise.

    Matching rules:
      * Line starts with `Error:<ws>` or `Warning:<ws>` (anchored at
        start-of-line, so embedded-in-prose mentions don't match).
      * Pattern is a substring of the REST of that line (after the
        prefix). We strip only the prefix — we do not re-scope to word
        boundaries, since sf auth tokens like `NoOrgAuthenticationError`
        are always well-formed identifiers without adjacent alphanum.
      * Empty stderr / empty patterns → no match.
    """
    if not stderr or not patterns:
        return False
    for line in stderr.splitlines():
        m = _AUTH_LINE_PREFIX_RE.match(line)
        if not m:
            continue
        tail = line[m.end():]
        if any(p in tail for p in patterns):
            return True
    return False


def run_sf(name: str, **params: str) -> Dict[str, Any]:
    """Execute a recipe-defined sf CLI command and return parsed stdout.

    Steps:
      1. Load recipe (yaml.safe_load).
      2. Enforce required_params.
      3. Substitute {{KEY}} into argv.
      4. subprocess.run with list argv (no shell, no bash -c).
      5. Parse stdout JSON; check `status == 0`.
      6. On failure: classify as AuthRequired (stderr pattern match) or
         SfCliError; every message is redacted via redact_error .

    Exception semantics:
      * AuthRequired — user needs to `sf org login`
      * SfCliError   — anything else (timeout, non-zero exit, JSON parse,
        status != 0)

    NEVER uses shell=True. NEVER calls log.exception(). NEVER echoes raw
    stderr without redaction .
    """
    recipe = _load_recipe(name)

    required = set(recipe.get("required_params") or [])
    missing = required - params.keys()
    if missing:
        raise SfCliError(f"missing required params for {name!r}: {sorted(missing)}")

    argv_template = recipe.get("argv") or []
    if not isinstance(argv_template, list):
        raise SfCliError(f"recipe {name!r} argv must be a list")

    argv = [_sub(str(e), params) for e in argv_template]
    timeout = int(recipe.get("timeout_seconds", 60))
    auth_patterns = recipe.get("auth_required_stderr_patterns") or []

    try:
        cp = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        # timeout exceptions carry stderr via e.stderr — redact.
        raise SfCliError(
            f"sf CLI {name!r} timed out after {timeout}s: {redact_error(e)}"
        ) from None
    except (OSError, subprocess.SubprocessError) as e:
        # any subprocess-layer error gets redacted.
        raise SfCliError(
            f"sf CLI {name!r} invocation failed: {redact_error(e)}"
        ) from None

    # Even on nonzero exit sf CLI usually still emits JSON on stdout; try
    # to parse before deciding failure mode.
    try:
        data = _parse_stdout_json(cp.stdout) if cp.stdout else {}
    except SfCliError:
        data = {}

    status_field = data.get("status", 0) if isinstance(data, dict) else 1
    if cp.returncode != 0 or status_field != 0:
        # stderr could contain a token on some failure paths; redact
        # the ENTIRE string before deciding how to classify or what to show.
        safe_stderr = _redact_subprocess_stderr(cp.stderr)
        if _stderr_matches_auth(cp.stderr, auth_patterns):
            raise AuthRequired(safe_stderr or "auth required")
        # Include exit code + JSON status in the message (both are
        # numeric/well-known, no token risk) plus the redacted stderr tail.
        raise SfCliError(
            f"sf CLI {name!r} failed "
            f"(exit={cp.returncode}, json_status={status_field}): {safe_stderr}"
        )

    return data


def _redact_subprocess_stderr(stderr: str) -> str:
    """run stderr text through the rest_client redaction regexes.

    stderr may contain `Authorization: Bearer ...` or `accessToken=...` if
    the sf CLI echoes a failing request; scrub before surfacing.

    calls the public `redact_text` (imported at module
    top). Previously imported the module-private `_redact_text` lazily on
    every call — a rename could have silently broken redaction, and an
    ImportError would have propagated through `run_sf` with the raw stderr
    still live in the traceback's frame locals.
    """
    return redact_text(stderr or "")
