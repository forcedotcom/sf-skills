#!/usr/bin/env python3
"""sf_telemetry — usage-telemetry capture + O11y-PDP transmit for the salesforce-development plugin.

**Stream A ("Capturing telemetry")** — consent-gated, scrubbed, local-only event
capture: hooks append scrubbed events to a local JSONL buffer, no network on the
hot path.

**Stream B ("Transmitting telemetry")** — on session end, a detached Node flusher
reads the buffer, maps each event to a Salesforce O11y **PDP event**
(`productFeatureId` = the suite's GUS Feature Record) and uploads it through the
connected org's `/services/data/vXX/connect/proxy/ui-telemetry` endpoint, exactly
as the SF CLI's own `plugin-telemetry` uploader does (reusing the bundled
`@salesforce/telemetry` `TelemetryReporter.sendPdpEvent`). Transmit is still fully
consent-gated: `off` / `SF_DISABLE_TELEMETRY` / `DO_NOT_TRACK` discard the buffer
so there is nothing to send, and with no connected org O11y simply no-ops.

Invoked via the `sf-context` wrapper, which delegates any `telemetry*` command here:

    sf-context telemetry <on|off|status>      Consent control (backs /salesforce-development:telemetry)
    sf-context telemetry-capture <event> [outcome]
                                               Capture one event from a hook payload on stdin.
                                               event ∈ {session_start, command_invoked,
                                                        skill_dispatched, exception, mcp_tool_used}
                                               outcome (command_invoked only) ∈ {success, failure}
    sf-context telemetry-flush                 Spawn the detached Node flusher (SessionEnd hook).
    sf-context telemetry-transmit              Run the transmit synchronously (used by the flusher
                                               and by tests; prints a JSON result, never spawns).

Design guarantees (POC-level, mirroring the plan):
    * Default-ON, but a true hard-off. `off` — or the ecosystem `SF_DISABLE_TELEMETRY`
      / `DO_NOT_TRACK` signals — means nothing is captured, buffered, or written.
    * Positive allowlist. Only approved fields per event type ever reach the buffer;
      anything else (code, paths, flag *values*, raw errors) is dropped before write.
    * Identity mirrors the CLI. machine_id reuses the CLI's CLIID when present. The
      raw orgId is never ENVELOPED on a buffered record and never rides the PDP
      shape — it carries only a coarse org_bucket
      (production/sandbox/scratch/none). The UIP flexible format (O11y
      sf_a4dInstrumentation schema) event shape ALONE carries the raw
      org id (when live-resolved at transmit), disclosed in the first-run notice,
      so the analytics UIP pipeline can key on it. org_id is never persisted to the
      local cache (which stores only the coarse bucket + transmit-only username).
    * Fail-silent. Any error is swallowed — telemetry never blocks or breaks a hook.
"""
from __future__ import annotations

import json
import locale as _locale_mod
import os
import platform
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional

# --- State & buffer locations -----------------------------------------------
# Two scopes:
#   * MACHINE-WIDE (~/.sf/telemetry/): consent + the first-run-notice marker +
#     our machine-id fallback. Per W-23481895 these MUST be sticky across projects
#     and sessions — opting out once opts out everywhere, and the notice shows once
#     per machine, not once per repo. Resolved from the real user home so it is the
#     same file from any cwd.
#   * PROJECT-LOCAL (.sf/): per-project working data — the event buffer, the
#     per-session org cache, session markers, snapshots/pending jobs, and the debug
#     log. These are cwd-relative on purpose (a project's events are its own).
_STATE_DIR = Path(".sf")                                 # project-local working dir


def _machine_state_dir() -> Path:
    """Machine-wide telemetry state dir (~/.sf/telemetry), created on demand.
    Honors SF_DEV_TELEMETRY_HOME so tests can redirect it without touching the real
    user home."""
    override = os.environ.get("SF_DEV_TELEMETRY_HOME")
    if override:
        p = Path(os.path.expanduser(override))
        # A RELATIVE override must stay machine-wide (stable regardless of the
        # process CWD), so anchor it under $HOME — NOT via .resolve(), which would
        # anchor to CWD and silently make consent/notice per-directory again,
        # breaking the machine-wide hard-off AC.
        if not p.is_absolute():
            p = Path(os.path.expanduser("~")) / p
        return p
    return Path(os.path.expanduser("~")) / ".sf" / "telemetry"


def _consent_file() -> Path:
    return _machine_state_dir() / "telemetry-config.json"    # {"enabled"} — machine-wide


def _notified_file() -> Path:
    # The one-time first-run notice marker lives in its OWN file, deliberately
    # separate from the consent config. The notice fires from the SessionStart
    # detect path, which can run concurrently with a `telemetry on/off` in another
    # process; if both wrote telemetry-config.json, the notice's read-modify-write
    # could clobber (resurrect) a consent value the user just changed. Keeping the
    # marker in its own file means the notice NEVER touches consent — it only
    # creates this marker — so there is no lost-update race on `enabled`.
    return _machine_state_dir() / "telemetry-notified"       # presence == notice already shown


def _machine_id_file() -> Path:
    return _machine_state_dir() / "telemetry-machine-id"     # our fallback id — machine-wide


def _first_session_file() -> Path:
    return _machine_state_dir() / "telemetry-first-session"  # once-per-machine first-run marker


def _claim_first_run() -> bool:
    """True EXACTLY ONCE per machine — the first time any session is captured — by
    atomically creating a machine-wide marker (exclusive create as a cross-process
    mutex, the same pattern as the notice marker). False on every later session and,
    fail-open, on any marker error — so a transient failure never mislabels a later
    session as first-run (which would inflate the install/activation KPI). This is
    deliberately NOT derived from buffer existence: per-session buffers are drained on
    every SessionEnd, so "no buffer exists" is the steady state, not a first run."""
    try:
        marker = _first_session_file()
        marker.parent.mkdir(parents=True, exist_ok=True)
        with open(marker, "x"):
            pass
        return True
    except FileExistsError:
        return False
    except OSError:
        return False

# Per-session event buffers: telemetry-buffer-<sid>.jsonl (project-local). Each
# session writes its OWN file so a concurrent session's SessionEnd flush renames
# only its own inode — eliminating the shared-buffer drain/attribution race.
_BUFFER_PREFIX = "telemetry-buffer"
_ORG_CACHE = _STATE_DIR / "telemetry-org.json"           # {"org_bucket","username"} once/session; raw org_id is NEVER cached
_TRANSMIT_LOG = _STATE_DIR / "telemetry-transmit.log"    # last flusher stderr (debug only)

# --- Stream B: O11y-PDP transmit target --------------------------------------
# The suite's GUS Product Feature Record id. Every PDP event we send is stamped
# with this — it is how O11y/CAP-G attributes the event to this product feature.
# (The SF CLI's own default is aJCEE0000000mHP4AY; this is the salesforce-
# development plugin suite's own feature record.)
_PRODUCT_FEATURE_ID = "aJCEE000000SLW94AO"
# O11y project/extension name — namespaces our events in the O11y stream.
_O11Y_PROJECT = "salesforce-development"
# NOTE: we deliberately do NOT hardcode an upload endpoint. O11y uploads go
# through the CONNECTED ORG via connection.requestPost(/services/data/vXX/
# connect/proxy/ui-telemetry) — the flusher derives that URL from the org's own
# instance url so telemetry can never egress to a non-org host.

# Per-session start marker: {"start_ms": int}. Written at session_start and read
# at session_end to compute duration. One file per session_id (rather than a
# shared mutable file) so parallel sessions never race on a read/modify/write.
def _session_file(session_id: str) -> Path:
    # Sanitize the session id to a safe filename token — Claude Code passes a
    # UUID, but never trust it into a path. Keep alnum/dash only; empty -> shared.
    safe = "".join(c for c in (session_id or "") if c.isalnum() or c == "-") or "nosession"
    return _STATE_DIR / f"telemetry-session-{safe}.json"


def _session_buffer(session_id: str) -> Path:
    """Per-session scrubbed-event buffer (telemetry-buffer-<sid>.jsonl). The token
    is sanitized to one path segment exactly as _session_file does (alnum/dash;
    empty -> 'nosession'), so a hostile session id can never escape the state dir."""
    safe = "".join(c for c in (session_id or "") if c.isalnum() or c == "-") or "nosession"
    return _STATE_DIR / f"{_BUFFER_PREFIX}-{safe}.jsonl"


def _all_session_buffers() -> list:
    """Every per-session buffer file in the project state dir. Globs
    telemetry-buffer-*.jsonl only — never snapshots or session markers."""
    try:
        return sorted(_STATE_DIR.glob(f"{_BUFFER_PREFIX}-*.jsonl"))
    except OSError:
        return []


# Set by capture_event for the duration of ONE capture: the private staging file its
# event is written to. The event is committed to the shared session buffer only if
# consent did not change during the capture; otherwise the stage is discarded. None on
# the flush path (cmd_flush / _write_session_end), which writes the session buffer
# directly. One capture per hook process, so a module-level value is race-free here.
_CAPTURE_STAGE: Optional[Path] = None


# --- Positive allowlist: the ONLY per-event fields that may reach the buffer -
# Anything not listed here is dropped before an event is written. This is the
# scrubbing guarantee — enforced structurally, not by trying to strip bad fields.
_ALLOWLIST = {
    "session_start": {"is_first_run"},
    "session_end": {"duration_ms", "event_count"},
    "command_invoked": {"outcome", "binary", "category", "subcommand"},
    "skill_dispatched": {"skill", "skill_domain"},
    "agent_dispatched": {"agent_type"},
    "exception": {"error_class", "kind"},
    "mcp_tool_used": {"mcp_server", "mcp_tool", "outcome"},
}

# --- Command scope: `command.invoked` fires ONLY for the plugin's OWN configured
# commands — the first-party bins shipped in salesforce-development/scripts
# (_FIRST_PARTY_BINS below) that back the `/salesforce-development:*` slash commands.
# We deliberately do NOT record the Salesforce CLI (`sf`/`sfdx`) or any other binary:
# a general-purpose CLI command carries arbitrary args, paths, and inline secrets we
# cannot safely parse, and it isn't a command this plugin ships. Every binary that is
# not one of our own bins produces NO event at all — not a redacted "other" row —
# exactly like a non-Salesforce skill/agent/MCP server. So command.invoked records
# only our own fixed subcommand vocabulary, never a free-form parsed string.
# `_classify_command` labels every non-first-party binary "other" — that's the signal
# the capture site uses to skip it.

# First-party utilities shipped in salesforce-development/scripts, invoked by the
# /salesforce-development:* slash commands (e.g. /salesforce-development:org ->
# `sf-context status-org`). Recognized so a dev using a slash command reads as
# real activity, not anonymous "other". Each maps to a coarse category plus the
# set of subcommands that are OUR OWN fixed vocabulary — so recording the exact
# subcommand is safe (no free-form user input, paths, or secrets). A subcommand
# not on its bin's list is recorded as the binary with subcommand dropped — never
# the raw token. This is what lets us capture "which slash command" without ever
# capturing an arbitrary string. Keep each bin's set in sync with that bin's own
# dispatch (sf_context.main() / sf-deploy-gate).
_FIRST_PARTY_BINS = {
    "sf-context": {
        "category": "plugin_command",
        "subcommands": {
            "detect", "verify-org", "check-tools", "post-deploy", "post-deploy-failure",
            "skills-first-advisory", "record-skill-dispatch", "reset-dispatch-turn",
            "feedback-nudge", "record-feedback-decision", "record-update-decision",
            "status", "status-org", "status-project", "telemetry", "telemetry-capture",
            "telemetry-flush", "telemetry-transmit",
        },
    },
    "sf-deploy-gate": {
        "category": "plugin_command",
        "subcommands": {"prod-check", "destructive", "auto-deploy"},
    },
}


# Shell operators that separate one command from the next in a compound line.
# We split on these so `cd app && sf deploy` or `sf ... | jq` is classified by its
# MEANINGFUL binary (sf), not the leading `cd`/pipe head. Only bare operator tokens
# count — an operator embedded in a quoted arg stays part of that arg (shlex keeps
# quoted content as one token, so it never appears as a standalone separator).
_SHELL_SEPARATORS = {"&&", "||", ";", "|", "&", "|&"}


# Punctuation the shell lexer treats as operator characters. A token composed
# ENTIRELY of these is a command separator/redirection, never a binary or arg — so
# `cd app;sf org list` and `echo x|sf ...` split even WITHOUT surrounding spaces.
_OPERATOR_CHARS = "();<>|&"


def _split_segments(cmd: str) -> list:
    """Tokenize a raw shell string into command SEGMENTS (lists of arg tokens),
    split on shell operators (&&, ||, ;, |, &, redirections). No-space operators
    (`a;b`, `a|b`) split too (punctuation_chars).

    Quote-safe: uses posix=False so quote characters are PRESERVED on tokens, which
    means a QUOTED operator (`echo "&&" ...`) tokenizes as `'"&&"'` (with quotes) and
    is NOT a bare-operator token, so it never splits — only a genuinely unquoted
    operator does. (posix=True stripped the quotes, making a quoted operator
    indistinguishable from a real one and causing a mis-split.) Quotes left on other
    tokens are harmless: the binary classifier uses the basename and the command
    parser validates against the closed vocabulary, neither of which a quoted token
    can satisfy."""
    try:
        lex = shlex.shlex(cmd, posix=False, punctuation_chars=_OPERATOR_CHARS)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        # Unbalanced quotes etc. — fall back to a naive split; still safe because
        # the downstream command parse only keeps closed-vocabulary command words.
        tokens = cmd.split()
    segments, current = [], []
    for t in tokens:
        if t and all(ch in _OPERATOR_CHARS for ch in t):  # bare (unquoted) operator
            if current:
                segments.append(current)
            current = []
        else:
            current.append(t)
    if current:
        segments.append(current)
    return segments


def _segment_binary(tokens: list) -> tuple[str, str, str]:
    """Classify ONE command segment's binary (already operator-free tokens).
    Returns (binary, category, subcommand) with the same rules as the public
    classifier: env-assignment prefixes skipped, path form reduced to basename,
    first-party subcommand recorded only from its fixed allowlist; ANY binary that
    is not one of our own first-party bins is reported as ("other", "other", "")."""
    non_env = _strip_env_prefix(tokens)
    first = non_env[0] if non_env else ""
    base = first.rsplit("/", 1)[-1] if first else ""
    fp = _FIRST_PARTY_BINS.get(base)
    if fp is not None:
        nxt = non_env[1] if len(non_env) > 1 else ""
        subcommand = nxt if nxt in fp["subcommands"] else ""
        return base, fp["category"], subcommand
    return "other", "other", ""


def _classify_command(cmd: str) -> tuple[list, str, str, str]:
    """Select the meaningful command segment and classify its binary.

    Returns (segment_tokens, binary, category, subcommand). Compound commands are
    split on shell operators and the FIRST segment whose binary is one of our own
    first-party bins wins — so `cd app && sf-context status` classifies as
    `sf-context`, not the leading `cd`. If no segment is one of our bins, the first
    segment is returned classified as "other" and the capture site skips it.
    Returning the SELECTED segment's tokens (not the raw string) keeps a compound
    line's sibling commands out of any downstream handling."""
    segments = _split_segments(cmd)
    if not segments:
        return [], "other", "other", ""
    first = None
    for seg in segments:
        binary, category, subcommand = _segment_binary(seg)
        if first is None:
            first = (seg, binary, category, subcommand)
        if binary != "other":
            return seg, binary, category, subcommand
    return first


def _classify_binary(cmd: str) -> tuple[str, str, str]:
    """Back-compat wrapper: classify a raw shell string to (binary, category,
    subcommand). See _classify_command for the segment-selection semantics."""
    _seg, binary, category, subcommand = _classify_command(cmd)
    return binary, category, subcommand


# --- Consent -----------------------------------------------------------------

def _env_optout() -> bool:
    """Honor the ecosystem-standard opt-out signals — these always win."""
    return bool(os.environ.get("SF_DISABLE_TELEMETRY") or os.environ.get("DO_NOT_TRACK"))


def _load_consent() -> dict:
    try:
        data = json.loads(_consent_file().read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_consent(cfg: dict) -> bool:
    # Write atomically (temp + os.replace) so a concurrent reader — the detached
    # flusher's opt-out re-check, or a parallel status read — never observes a
    # half-written/empty file (which would be parsed as default-ON and could let a
    # just-opted-out session upload). os.replace is atomic on the same filesystem.
    #
    # Returns True only if the file was durably written. A caller reporting a
    # hard-off to the user MUST check this: default is ON, so a swallowed write
    # failure would leave capture active while telling the user it is off. On
    # failure the caller can fall back to steering the user to the env opt-out.
    try:
        d = _consent_file().parent
        d.mkdir(parents=True, exist_ok=True)
        # Bump a monotonic generation on EVERY consent transition (on AND off) so an
        # in-flight capture can detect that consent changed during its window —
        # including an off->on toggle, which a current-enabled check alone would miss
        # (it would preserve a pre-opt-out event once consent flipped back on).
        import time
        out = dict(cfg)
        # Monotonic, rollback-resistant generation. A plain counter (prev+1) is a
        # read-modify-write that races across processes and can roll BACK (observed
        # 0->1->2->1) — which would let a capture's post-write generation compare as
        # "unchanged" and preserve a pre-opt-out event. Taking the max of counter+1
        # and a wall-clock nanosecond stamp — evaluated at write time, so the LAST
        # os.replace always carries the latest stamp — keeps it strictly forward even
        # when a stale writer clobbers with an old counter value.
        # _consent_generation() coerces a malformed/non-numeric persisted `gen` to 0
        # (it never raises), so a corrupted consent file can't break the transition.
        out["gen"] = max(_consent_generation() + 1, time.time_ns())
        tmp = _consent_file().with_suffix(f".tmp-{os.getpid()}")
        tmp.write_text(json.dumps(out, indent=2))
        os.replace(tmp, _consent_file())
        return True
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except (OSError, NameError):
            pass
        return False


def _is_enabled() -> bool:
    """Default-ON. Off iff explicitly disabled or an env opt-out is set."""
    if _env_optout():
        return False
    return _load_consent().get("enabled", True)


def _consent_generation() -> int:
    """Monotonic consent generation — bumped by _save_consent on every on/off
    transition; 0 in the default (no consent file) state. An in-flight capture
    records this at entry and compares it after writing to detect a transition (even
    a full off->on toggle) that lands during its window."""
    try:
        return int(_load_consent().get("gen", 0))
    except (ValueError, TypeError):
        return 0


def _consent_lock_file() -> Path:
    return _machine_state_dir() / "telemetry-consent.lock"


class _ConsentLock:
    """Machine-wide advisory lock backed by an OS file lock — fcntl.flock on POSIX,
    msvcrt.locking on Windows — held on an open descriptor. The kernel releases the
    lock automatically when the holder exits or crashes, so there is NO age-based
    "stale lock" stealing (age can't distinguish a slow-but-alive holder from a dead
    one): a live holder is always respected, a dead holder is always released. The
    lock file is persistent and never unlinked, so there is no delete/replace race.

    It serializes consent transitions (save + purge) against each other AND against a
    capture's final stage commit, so (a) the generation is written under mutual
    exclusion — strictly monotonic, no read-modify-write rollback or ABA across
    processes — and (b) a commit and an opt-out purge can never interleave.

    __enter__ BLOCKS (bounded on the MONOTONIC clock, so a backward clock step can't
    make the wait unbounded) up to `timeout` and returns True IFF the lock is HELD.
    EVERY caller honors the result and does nothing correctness-critical when it is
    False — no caller falls back to running the critical section unlocked. The capture
    stage commit is fail-CLOSED (it DROPS its staged event if it cannot take the
    lock); a consent transition (on/off) DECLINES — it does not write or purge
    unlocked, returns failure, and reports the actual state (off steers the user to
    the env opt-out, which needs no lock or writable state). False results only from
    genuine contention past `timeout` or the absence of an OS lock primitive.
    Use as `with _ConsentLock() as held: ...`."""

    def __init__(self, timeout: float = 2.0):
        self._timeout = timeout
        self._fd = None
        self._held = False
        self._kind = None  # "fcntl" | "msvcrt"

    def _make_acquirer(self):
        """Return a non-blocking try-acquire callable for this platform, or None if
        no OS lock primitive is available."""
        try:
            import fcntl

            def _acq_fcntl() -> bool:
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except OSError:
                    return False  # EAGAIN/EACCES — held by a live process

            self._kind = "fcntl"
            return _acq_fcntl
        except ImportError:
            pass
        try:
            import msvcrt

            def _acq_msvcrt() -> bool:
                try:
                    os.lseek(self._fd, 0, os.SEEK_SET)
                    msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
                    return True
                except OSError:
                    return False

            self._kind = "msvcrt"
            return _acq_msvcrt
        except ImportError:
            return None

    def __enter__(self) -> bool:
        import time
        try:
            lock = _consent_lock_file()
            lock.parent.mkdir(parents=True, exist_ok=True)
            self._fd = os.open(str(lock), os.O_CREAT | os.O_RDWR, 0o600)
        except OSError:
            self._fd = None
            return False
        acquire = self._make_acquirer()
        if acquire is None:  # no fcntl/msvcrt — cannot guarantee exclusion
            self._close_fd()
            return False
        # Bound the wait on the MONOTONIC clock: a backward wall-clock adjustment
        # (NTP step, DST, manual set) must never turn this bounded hook wait into an
        # unbounded one.
        deadline = time.monotonic() + self._timeout
        while True:
            if acquire():
                self._held = True
                return True
            if time.monotonic() >= deadline:
                self._close_fd()
                return False
            time.sleep(0.02)

    def _close_fd(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    def __exit__(self, *exc) -> bool:
        if self._fd is not None and self._held:
            try:
                if self._kind == "fcntl":
                    import fcntl
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                elif self._kind == "msvcrt":
                    import msvcrt
                    os.lseek(self._fd, 0, os.SEEK_SET)
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass  # closing the fd below releases the OS lock regardless
        self._close_fd()
        self._held = False
        return False


def _in_sf_project() -> bool:
    """True iff the current working directory is inside a Salesforce DX project —
    i.e. an ``sfdx-project.json`` exists at the cwd or any ancestor. This plugin is
    installed globally but is ABOUT Salesforce development, so telemetry is captured
    only when the user is actually working in a Salesforce project; in a plain repo
    or any non-SF directory we record nothing, even with the plugin installed and
    consent on. Walking to ancestors (not just cwd) keeps it correct when a hook
    fires from a subdirectory of the project. Fail-open to False (record nothing) on
    any filesystem error — never over-collect on uncertainty."""
    try:
        d = Path.cwd().resolve()
    except OSError:
        return False
    for path in (d, *d.parents):
        try:
            if (path / "sfdx-project.json").is_file():
                return True
        except OSError:
            continue
    return False


# --- Identity & environment envelope -----------------------------------------

def _cli_cache_dir() -> Path:
    """Mirror oclif's cacheDir for dirname 'sf' — where the CLI writes CLIID.txt."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "sf"
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "sf"
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "sf"


def _machine_id() -> str:
    """Reuse the Salesforce CLI's client id when present (so plugin usage can be
    correlated with CLI usage on the same machine); else reuse/mint our own.
    All three are random hex — no PII, not hardware-derived."""
    # 1) the CLI's CLIID (40-hex), read straight off disk — no `sf` invocation.
    try:
        cliid = (_cli_cache_dir() / "CLIID.txt").read_text().strip()
        if cliid:
            return cliid
    except OSError:
        pass
    # 2) our own previously-minted fallback (machine-wide, so the id is stable
    #    across projects — a per-project id would fragment one machine into many).
    try:
        mine = _machine_id_file().read_text().strip()
        if mine:
            return mine
    except OSError:
        pass
    # 3) mint + persist a 32-hex fallback.
    import secrets
    mid = secrets.token_hex(16)
    try:
        _machine_id_file().parent.mkdir(parents=True, exist_ok=True)
        _machine_id_file().write_text(mid)
    except OSError:
        pass
    return mid


def _suite_version() -> str:
    """Read the hosting plugin's version from its manifest (scripts/ -> ../.claude-plugin)."""
    try:
        manifest = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
        return json.loads(manifest.read_text()).get("version", "") or ""
    except (OSError, json.JSONDecodeError):
        return ""


# --- Which dispatched skills are OURS ----------------------------------------
# The `Skill` PreToolUse matcher fires for EVERY skill available in the session
# (google-workspace, gus, tabcore-dev, user-authored skills, ...). But this
# telemetry is stamped with OUR product feature record, so only skills THIS
# plugin ships may be attributed to it — recording a third-party or user skill
# would misreport unrelated usage as Salesforce-feature usage.
#
# The authoritative "ours" set is the plugin's own skills/ directory
# (scripts/ -> ../skills), read once and cached. It's self-maintaining: a new
# skill dir is recognized with no code change. Our skills are named
# "<domain>-<action>" (agentforce-*, automation-*, dx-*, platform-*); the domain
# is the leading segment. If the dir can't be read we fall back to the known
# domain vocabulary so a transient read error never silently drops ALL skill
# telemetry (fail-open to the coarse-but-correct signal).
_SF_SKILL_DOMAINS = {"agentforce", "automation", "dx", "platform"}
_SF_SKILLS_CACHE: Optional[set] = None


def _sf_skills() -> set:
    """The set of skill names this plugin ships (cached; read from ../skills)."""
    global _SF_SKILLS_CACHE
    if _SF_SKILLS_CACHE is None:
        try:
            skills_dir = Path(__file__).resolve().parent.parent / "skills"
            _SF_SKILLS_CACHE = {p.name for p in skills_dir.iterdir() if p.is_dir()}
        except OSError:
            _SF_SKILLS_CACHE = set()
    return _SF_SKILLS_CACHE


def _resolve_sf_skill(skill: str) -> tuple:
    """Resolve a dispatched skill name to (bare_name, domain).

    Tolerates a plugin-qualified dispatch (``salesforce-development:platform-
    apex-generate``) and a flat one (``platform-apex-generate``). Returns a
    domain of ``None`` when the skill is NOT one of ours — the signal the
    caller uses to skip recording it. When the skills catalog cannot be read we
    fall back to the closed DOMAIN vocabulary AND still require a hyphenated
    ``<domain>-<action>`` shape, so a bare third-party name that happens to start
    with a domain word (e.g. ``platform``) is not misattributed as ours."""
    bare = skill.split(":", 1)[1] if ":" in skill else skill
    domain = bare.split("-", 1)[0] if "-" in bare else ""
    catalog = _sf_skills()
    if catalog:
        is_ours = bare in catalog
    else:
        is_ours = ("-" in bare) and (domain in _SF_SKILL_DOMAINS)
    return (bare, domain if is_ours else None)


# --- Which dispatched subagents are OURS -------------------------------------
# The `Task|Agent` matcher fires for EVERY subagent dispatch in the session:
# built-ins (general-purpose, code-review, Explore, Plan, ...), other plugins'
# agents, and USER-AUTHORED custom agents whose type strings are arbitrary and can
# carry PII. Like skills, only agents THIS plugin ships may be recorded verbatim;
# anything else collapses to "other". Authoritative set = the plugin's own agents/
# directory (self-maintaining), with a small built-in fallback vocabulary for when
# the dir can't be read.
_SF_AGENTS_FALLBACK = frozenset({
    "adlc-author", "adlc-engineer", "adlc-orchestrator", "adlc-qa",
    "architecture-review", "salesforce-dev",
})
_SF_AGENTS_CACHE: Optional[set] = None


def _sf_agents() -> set:
    """The set of agent types this plugin ships (cached; read from ../agents)."""
    global _SF_AGENTS_CACHE
    if _SF_AGENTS_CACHE is None:
        try:
            agents_dir = Path(__file__).resolve().parent.parent / "agents"
            _SF_AGENTS_CACHE = {p.stem for p in agents_dir.iterdir()
                                if p.is_file() and p.suffix == ".md"}
        except OSError:
            _SF_AGENTS_CACHE = set()
    return _SF_AGENTS_CACHE or set(_SF_AGENTS_FALLBACK)


def _resolve_sf_agent(agent_type: str) -> str:
    """Return the agent type IFF it is one this plugin ships, else "other".

    Tolerates a plugin-qualified dispatch (``salesforce-development:adlc-qa``).
    A built-in, third-party, or user-authored agent type is never recorded
    verbatim — the arbitrary string can carry PII — so it collapses to "other"."""
    if not agent_type:
        return ""
    bare = agent_type.split(":", 1)[1] if ":" in agent_type else agent_type
    return bare if bare in _sf_agents() else "other"


# The MCP servers this plugin SHIPS (see .mcp.json). Any OTHER server — a user- or
# third-party-configured one — has an ARBITRARY name that can carry PII (e.g.
# `mcp__customer-alice@example.com__query`), so we never record an unrecognized
# server or its tool verbatim.
_MCP_SERVERS = frozenset({
    "salesforce-api-context",
    "salesforce-lsp",
    "salesforce-metadata-experts",
})


def _classify_mcp(tool_name: str) -> tuple:
    """From a ``mcp__<server>__<tool>`` name, return (mcp_server, mcp_tool) using a
    CLOSED server vocabulary. Our own servers keep their normalized name and tool
    (the tool is our server's own fixed API surface, not user input); ANY unknown or
    third-party server — whose name is arbitrary user input — collapses to
    ("other", "other") so an arbitrary/PII server or tool name can never reach the
    buffer. Handles Claude Code namespacing our servers as
    ``plugin_<plugin>_<server>`` as well as the bare ``<server>`` form."""
    if not tool_name.startswith("mcp__"):
        return "", ""
    parts = tool_name.split("__")
    raw_server = parts[1] if len(parts) > 1 else ""
    raw_tool = parts[2] if len(parts) > 2 else ""
    if not raw_server:
        return "", ""
    # Match ONLY the exact bare name or the exact Claude Code plugin-namespaced
    # forms this plugin actually ships under — NOT an arbitrary "_<known>" suffix.
    # A loose endswith() would classify a THIRD-PARTY server whose name merely ends
    # in one of ours (e.g. `customer-alice_salesforce-lsp`) as ours and then record
    # its tool name (`alice@example.com`) — a PII leak. The only namespaced shapes
    # Claude Code produces for our own servers are `plugin_salesforce-development_<s>`
    # (observed) and `salesforce-development_<s>`; anything else is not ours.
    for known in _MCP_SERVERS:
        if raw_server in (known,
                          f"plugin_{_O11Y_PROJECT}_{known}",
                          f"{_O11Y_PROJECT}_{known}"):
            return known, raw_tool          # ours: safe to record the tool
    return "other", "other"                 # unknown/third-party: non-identifying


def _is_ci() -> bool:
    return bool(
        os.environ.get("CI")
        or os.environ.get("CONTINUOUS_INTEGRATION")
        or os.environ.get("BUILD_NUMBER")
        or os.environ.get("GITHUB_ACTIONS")
    )


def _agent_harness() -> str:
    """Which agent harness is executing the plugin, as a CLOSED enum:
    claude-code | cursor | codex | copilot-cli | opencode | other.

    Detected from the harness's own environment variables at CAPTURE time (the hook
    subprocess reliably has them). Precedence matters: a Claude Code hook can run
    inside another editor's integrated terminal (so both markers are present), but the
    process that actually spawned this script is Claude Code — so CLAUDE_CODE_* wins.
    Returns a fixed token only (never a raw env value), so no PII can leak; anything
    unrecognized is "other", which is itself the signal that a new harness is running
    the plugin. NOTE: today capture only fires from Claude Code hooks, so this reads
    "claude-code" in practice; the other values are for when the plugin runs under
    those harnesses' own hook/plugin systems."""
    env = os.environ
    # Claude Code (and Claude Desktop, same engine — env cannot separate them).
    # CLAUDE_CODE_CHILD_SESSION is set ONLY by Claude Code itself (not IDE-integrated
    # terminals), so it is the most precise "Claude Code spawned this" signal.
    if env.get("CLAUDE_CODE_CHILD_SESSION") == "1" or env.get("CLAUDECODE") == "1":
        return "claude-code"
    if env.get("CURSOR_AGENT"):
        return "cursor"
    if env.get("CODEX_HOME"):
        return "codex"
    if env.get("COPILOT_HOME") or env.get("COPILOT_GITHUB_TOKEN"):
        return "copilot-cli"
    if any(k.startswith("OPENCODE_") for k in env):
        return "opencode"
    return "other"


def _locale() -> str:
    try:
        return _locale_mod.getlocale()[0] or os.environ.get("LANG", "").split(".")[0] or ""
    except Exception:
        return ""


def _classify_org_bucket(result: dict) -> str:
    """Coarse org classification (scratch / sandbox / production / none) for the
    telemetry envelope + PDP context.

    The org instance HOST is the authoritative signal and is checked first, because
    `sf org display --json` does not reliably include isScratch/isSandbox — a scratch
    org therefore fell through to "production" (observed on
    `*.scratch.my.salesforce.com`). Scratch orgs live on `*.scratch.my.salesforce.com`
    and sandboxes on `*.sandbox.my.salesforce.com` (older shapes: a `--<name>` suffix
    or `csN` pod), so the host disambiguates what the JSON flags miss. The explicit
    flags are honored as a fallback, then org_id presence, else "none"."""
    result = result if isinstance(result, dict) else {}
    host = (result.get("instanceUrl") or "").lower()
    if ".scratch.my.salesforce.com" in host:
        return "scratch"
    # Modern sandbox: *.sandbox.my.salesforce.com. Legacy sandbox pods: csNN(.salesforce.com).
    if ".sandbox.my.salesforce.com" in host or re.search(r"//cs[0-9]+\.", host):
        return "sandbox"
    if result.get("isScratch"):
        return "scratch"
    if result.get("isSandbox"):
        return "sandbox"
    if result.get("id"):
        return "production"
    return "none"


# cmd.exe RE-PARSES the command line it is handed, so these characters keep shell
# meaning inside a batch-shim invocation even though we pass an argv array. On the
# `.cmd`/`.bat` shim path we REFUSE them (fail closed → None) rather than attempt a
# notoriously error-prone cmd.exe quoter — exactly as sf_context.build_command does.
# These two tuples MUST stay in sync with sf_context._CMD_ARG_METACHARACTERS /
# _CMD_PATH_METACHARACTERS (duplicated, not imported, because sf_context imports
# THIS module — importing back would be circular). Args are fully controlled here
# (fixed subcommands/flags), so they get the wider set incl. `(`/`)`/`!`; the
# system-provided shim PATH legitimately contains `(`/`)` (e.g. "Program Files
# (x86)") so its guard omits those but still rejects the chars cmd.exe reparses
# even inside quotes (`%`, `!`), the quote-breaker (`"`), and the chaining set.
_CMD_ARG_METACHARACTERS = ("&", "|", "<", ">", "^", "%", '"', "!", "(", ")", "\n", "\r")
_CMD_PATH_METACHARACTERS = ("&", "|", "<", ">", "^", "%", '"', "!", "\n", "\r")


def _sf_command(args: list) -> Optional[list]:
    """Build an argv to invoke `sf` that works on Windows too. On Windows `sf` is a
    batch shim (`sf.cmd`), which subprocess cannot exec directly by bare name — it
    must be resolved (shutil.which honors PATHEXT so `sf` finds `sf.cmd`) and, for a
    .cmd/.bat, launched via [COMSPEC, /c, resolved, *args]. This mirrors
    sf_context.build_command; it is duplicated here (not imported) because
    sf_context imports THIS module, so importing back would be circular.

    On the batch-shim path, passing an argv array preserves argv boundaries but is
    NOT sufficient for injection safety, because cmd.exe re-parses the serialized
    command line — so we FAIL CLOSED (return None) if the resolved shim PATH holds a
    reparse-dangerous char or any ARG holds a cmd metacharacter, exactly like
    build_command. Returns None when `sf` cannot be resolved (or is refused), so the
    caller degrades to the "none" org rather than raising FileNotFoundError and
    silently skipping the O11y leg on Windows (W-23466799 / WIN-026)."""
    import shutil
    resolved = shutil.which("sf")
    if not resolved:
        return None
    if os.name == "nt" and os.path.splitext(resolved)[1].lower() in (".cmd", ".bat"):
        # Reuse build_command's guard: refuse cmd.exe metacharacters rather than quote.
        if any(ch in resolved for ch in _CMD_PATH_METACHARACTERS) or any(
            any(ch in str(a) for ch in _CMD_ARG_METACHARACTERS) for a in args
        ):
            return None
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        return [comspec, "/c", resolved, *args]
    return [resolved, *args]


def _resolve_org_context() -> dict:
    """Best-effort orgId + bucket + username via `sf org display --json`. Called
    ONCE at flush time (session end) — never on the SessionStart hot path, so the
    startup hook stays local-first and single-process. The result is cached under
    .sf/ so a later flush can fall back to it if a subsequent `sf` call fails.
    Null-safe when no org is connected (returns the empty "none" envelope)."""
    cmd = _sf_command(["org", "display", "--json"])
    if cmd is None:
        return {"org_id": "", "org_bucket": "none", "username": ""}
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=10,
        )
        result = (json.loads(proc.stdout) or {}).get("result", {}) if proc.stdout else {}
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, ValueError):
        result = {}
    bucket = _classify_org_bucket(result)
    # Username is captured for transmit only (the O11y reporter builds the org
    # connection from it via `Org.create({aliasOrUsername})`). It is NOT part of
    # the event envelope and is never sent as telemetry. We surface it (and the raw
    # org id) to the caller so transmit can open the connection and stamp the org id
    # onto the UIP shape — but we do NOT persist the raw org id to the on-disk cache
    # (at-rest minimization): the cache exists only to answer "is an org connected?"
    # on a later flush that can't reach `sf`, and the coarse bucket already does
    # that. So the cache stores only the coarse bucket plus the transmit-only
    # username — dropped on `telemetry off` and after a successful send (see _purge /
    # cmd_send). Because org id is never cached, the cache-fallback transmit path
    # emits NO org id (only the live-resolved path carries it).
    username = result.get("username") or ""
    ctx = {"org_bucket": bucket, "username": username}
    # Cache it so a later flush that can't reach `sf` can still reuse the bucket.
    if username or bucket != "none":
        try:
            _ORG_CACHE.parent.mkdir(parents=True, exist_ok=True)
            _ORG_CACHE.write_text(json.dumps(ctx))
        except OSError:
            pass
    # org_id is returned live for the transmit liveness check AND for the UIP shape;
    # it is never cached and never enveloped on a buffered record.
    return {"org_id": result.get("id") or "", **ctx}


def _org_context() -> dict:
    """Read the per-session org cache; empty envelope when unresolved. The
    `username` is transmit-only (never enveloped) — see _resolve_org_context."""
    try:
        data = json.loads(_ORG_CACHE.read_text())
        if isinstance(data, dict):
            # org_id is intentionally absent from the cache (see _resolve_org_context);
            # report it empty so callers relying on the coarse bucket still work.
            return {
                "org_id": "",
                "org_bucket": data.get("org_bucket", "none"),
                "username": data.get("username", ""),
            }
    except (OSError, json.JSONDecodeError):
        pass
    return {"org_id": "", "org_bucket": "none", "username": ""}


def _os_name() -> str:
    return {"darwin": "darwin", "win32": "windows"}.get(sys.platform, "linux")


def _model(payload: dict) -> str:
    """Best-effort model id from the hook payload — "" when absent.

    LIMITATION: Claude Code only includes `model` in the SessionStart hook payload;
    no other hook (PreToolUse/PostToolUse/etc.) receives it, and there is no env var
    or side channel that reflects the live model. So we can only know the model the
    session STARTED with, captured here at session_start; it is NOT backfilled onto
    later events (that would report an empty model as a real one), and it does NOT
    reflect a mid-session `/model` switch. Model-attributed telemetry is therefore
    accurate as "session-start model", not "model at the moment of each event"."""
    return (payload.get("model") or payload.get("model_id")
            or payload.get("modelId") or "") if isinstance(payload, dict) else ""


def _envelope(payload: dict) -> dict:
    """Host / identity / org context attached to every event — the CLI's model."""
    version = _suite_version()
    env = {
        "machine_id": _machine_id(),
        "session_id": payload.get("session_id") or payload.get("sessionId") or "",
        "os": _os_name(),
        "arch": platform.machine(),
        "os_version": platform.release(),
        "locale": _locale(),
        "plugin_name": "salesforce-development",
        # plugin_version and suite_version are the same manifest version here —
        # the plan lists both (plugin_version is the CLI-parallel field name,
        # suite_version the suite-wide alias); emit both for schema parity.
        "plugin_version": version,
        "suite_version": version,
        "ci": _is_ci(),
        "model": _model(payload),
        # Which agent harness is running the plugin (closed enum). Carried on the
        # buffered record so the detached transmit can attach it — but emitted ONLY on
        # the UIP shape (see _to_a4d_event); the PDP shape does not carry it.
        "harness": _agent_harness(),
    }
    org = _org_context()
    # ONLY the coarse org_bucket is ENVELOPED on the buffered record. The raw org_id
    # is deliberately never placed here (nor on the PDP shape, which stays
    # coarse-bucket-only). The UIP shape alone carries the raw org id, and it is
    # stamped at TRANSMIT time from the live resolve (see _build_transmit_payload) —
    # never read from this envelope, and never persisted to the cache. `username` is
    # likewise transmit-only.
    env["org_bucket"] = org.get("org_bucket", "none")
    return env


# --- Buffer write ------------------------------------------------------------

def _now_ms() -> int:
    """Epoch-ms timestamp (PDP's required shape). time.time() is allowed here —
    this is a live hook, not a replayable workflow script."""
    import time
    return int(time.time() * 1000)


def _write_event(event_type: str, fields: dict, payload: dict) -> None:
    """Scrub `fields` to the allowlist, attach the envelope, append one JSONL line."""
    allowed = _ALLOWLIST.get(event_type, set())
    scrubbed = {k: v for k, v in fields.items() if k in allowed}
    record = {
        "event": event_type,
        "timestamp": _now_ms(),
        **_envelope(payload),
        "payload": scrubbed,
    }
    try:
        # When capture_event is staging (the common capture path), write to the
        # capture's PRIVATE temp file, not the shared session buffer — so a stale
        # capture (consent toggled mid-capture) can discard ONLY its own event
        # without touching another capture's valid, re-enabled events. The flush path
        # (no stage set) writes the session buffer directly.
        dest = _CAPTURE_STAGE if _CAPTURE_STAGE is not None \
            else _session_buffer(record.get("session_id") or "")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass


def _write_session_end(payload: dict) -> None:
    """Compute + append the session_end event: duration from the per-session start
    marker (0 if absent) and event_count = this session's own buffered lines. Then
    remove the marker. Shared by the session_end capture path and cmd_flush so the
    end event is written by a SINGLE writer regardless of which hook fires it —
    avoiding a read/unlink race between a parallel session_end capture and flush."""
    sid = payload.get("session_id") or payload.get("sessionId") or ""
    duration_ms = 0
    sf = _session_file(sid)
    try:
        start = json.loads(sf.read_text()).get("start_ms")
        if isinstance(start, (int, float)):
            duration_ms = max(0, _now_ms() - int(start))
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    # This session's buffer holds only this session's records, so event_count is
    # simply its non-blank lines.
    event_count = 0
    try:
        with _session_buffer(sid).open(encoding="utf-8") as fh:
            event_count = sum(1 for line in fh if line.strip())
    except OSError:
        pass
    _write_event("session_end", {"duration_ms": duration_ms, "event_count": event_count}, payload)
    # Clean up the marker — the session is over.
    try:
        sf.unlink(missing_ok=True)
    except OSError:
        pass


# --- Hook payload parsing ----------------------------------------------------

def _read_payload() -> dict:
    """Read the hook's JSON payload from stdin; {} on empty/garbled/TTY."""
    try:
        if sys.stdin.isatty():
            return {}
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def _strip_env_prefix(tokens: list) -> list:
    """Drop leading `VAR=value` env-assignments (and their values) so the real
    binary/command is classified, never the assigned value."""
    return [t for t in tokens
            if not ("=" in t and not t.startswith("-")
                    and t.split("=", 1)[0].isidentifier())]


# --- Capture entry point -----------------------------------------------------

def capture_event(event: str, outcome: str, payload: dict) -> None:
    """Capture one event from an already-parsed hook payload — print-free.

    Consent-gated (silent no-op when off) and fail-silent throughout: a capture
    error must never surface or break a caller. Writes to the local buffer only;
    it never touches stdout, so an in-process caller (e.g. the post-bash
    dispatcher) can invoke it without disturbing that caller's own hook output."""
    # Read consent ONCE so the enabled gate and the generation baseline are captured
    # atomically: an `off` (or off->on toggle) that lands during this capture then
    # shows up as a changed generation in the post-write compensating check below.
    if _env_optout():
        return
    cfg0 = _load_consent()
    if not cfg0.get("enabled", True):
        return
    # Parse the generation defensively: a malformed (non-numeric) persisted `gen` —
    # a hand-edited or corrupted consent file — must fail-safe to 0, NOT raise. This
    # runs BEFORE the fail-silent try/finally below, so an unguarded int() here would
    # propagate out of capture_event and could break the hook it is wired into.
    try:
        gen0 = int(cfg0.get("gen", 0)) if isinstance(cfg0, dict) else 0
    except (ValueError, TypeError):
        gen0 = 0
    # Scope to Salesforce work: the plugin is installed globally, but we capture
    # ONLY when the user is inside a Salesforce DX project. In any non-SF directory
    # we record nothing at all — so a user's unrelated activity in a plain repo is
    # never collected. (This is the single capture chokepoint; every event type is
    # gated here.)
    if not _in_sf_project():
        return
    # DISCLOSURE-BEFORE-CAPTURE invariant: never buffer ANY event — session_start
    # included — until the user has been shown the one-time telemetry notice. This is
    # ordered to hold even for session_start: cmd_capture attempts the notice FIRST
    # (first_run_notice_lines() atomically creates the machine-wide marker, or sees
    # detect's), THEN calls this. So by the time session_start reaches here the marker
    # exists — UNLESS disclosure failed (e.g. the marker file could not be created),
    # in which case we must NOT buffer session_start either, so nothing can later be
    # flushed without the user having been disclosed to. On every subsequent session
    # the marker already exists, so session_start captures normally. In CI there is no
    # human to notify, so the CI capture path is not gated on disclosure. Fail-safe:
    # if the marker is unreadable we treat the notice as NOT shown and drop the event.
    if not _is_ci() and not _notice_shown():
        return

    if not isinstance(payload, dict):
        payload = {}
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    sid = payload.get("session_id") or payload.get("sessionId") or ""

    # Stage this capture's event to a PRIVATE temp; commit it to the shared session
    # buffer only if consent is unchanged at the end of the capture (see finally). A
    # stale capture thus discards only its own staged event — never another capture's.
    global _CAPTURE_STAGE
    # Per-capture stage file, created EXCLUSIVELY (O_EXCL) under a random token — NOT
    # PID-only. PIDs are reused and a single process can have overlapping captures, so
    # a random token plus exclusive creation guarantees each capture owns a distinct,
    # freshly created stage that no other capture can read, commit, or clobber. On the
    # astronomically unlikely token collision, retry with a fresh token. If we cannot
    # exclusively create a private stage (all retries collide, or an OSError), DROP the
    # capture (fail-closed) rather than let _write_event fall back to a shared,
    # append-mode file we don't exclusively own.
    import secrets
    stage = None
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        for _ in range(5):
            cand = _STATE_DIR / f"telemetry-stage-{os.getpid()}-{secrets.token_hex(8)}.jsonl"
            try:
                os.close(os.open(str(cand), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
                stage = cand
                break
            except FileExistsError:
                continue
    except OSError:
        stage = None
    if stage is None:
        return  # no private, exclusive stage -> drop the capture (fail-closed)
    _CAPTURE_STAGE = stage
    try:
        if event == "session_start":
            # The SessionStart matcher is "*", so Claude Code RE-FIRES this hook on
            # resume and after every compaction — not just on a genuine new session.
            # Recording those would write duplicate session_start rows (inflating the
            # session/adoption counts) AND re-stamp start_ms to now, so session_end
            # would then measure duration_ms from the last re-stamp — a long, compacted
            # session reporting a tiny duration. Treat a re-fire as a no-op (cmd_detect
            # special-cases the same source), capturing only a true new session.
            source = (payload.get("source") or payload.get("Source") or "").lower()
            if source in ("compact", "resume"):
                return
            # Org is deliberately NOT resolved here. SessionStart is local-first
            # and single-process (develop's UX invariant) — spawning `sf org
            # display` on the startup hook would reintroduce exactly the parallel
            # subprocess that refactor removed. Org context (org_bucket for the
            # transmitted events, username to open the upload connection) is
            # resolved ONCE at session end by cmd_flush, a detached process where
            # the wait has no UX cost. org_id is never transmitted, so leaving it
            # empty in the local envelope costs no backend accuracy.
            #
            # is_first_run marks the FIRST captured session on this machine, EVER —
            # the install/activation proxy the adoption KPI keys on. It is a durable,
            # machine-wide, once-only signal (an exclusive-create marker, a cross-
            # process mutex), NOT buffer existence: per-session buffers are drained on
            # every SessionEnd, so deriving it from "no buffer exists" reported
            # first_run on nearly every session (the steady state), inflating installs.
            is_first = _claim_first_run()
            _write_event("session_start", {"is_first_run": is_first}, payload)
            # Stamp the session start so session_end can compute duration. Written
            # per-session-id to avoid racing a parallel session's marker.
            try:
                sid = payload.get("session_id") or payload.get("sessionId") or ""
                sf = _session_file(sid)
                sf.parent.mkdir(parents=True, exist_ok=True)
                sf.write_text(json.dumps({"start_ms": _now_ms()}))
            except OSError:
                pass
            return

        if event == "session_end":
            _write_session_end(payload)
            return

        if event == "command_invoked":
            cmd = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
            _segment, binary, category, subcommand = _classify_command(cmd)
            if binary in _FIRST_PARTY_BINS:
                # First-party plugin utility (a /salesforce-development:* slash
                # command, e.g. sf-context / sf-deploy-gate). Record the allowlisted
                # subcommand — our own fixed vocabulary, so it's safe and meaningful
                # (which of the plugin's own commands the dev used).
                _write_event("command_invoked", {
                    "binary": binary,
                    "category": category,
                    "subcommand": subcommand,
                    "outcome": outcome or "success",
                }, payload)
            # Any other binary — including sf/sfdx and every general-purpose CLI — is
            # skipped ENTIRELY, no event, exactly like a non-Salesforce
            # skill/agent/MCP server above. We record ONLY the plugin's own configured
            # commands; an arbitrary shell command (sf included) carries paths,
            # hostnames, and inline secrets we can't safely parse, so rather than
            # record a stubbed binary:"other" row we record nothing at all.
            return

        if event == "skill_dispatched":
            skill = ""
            if isinstance(tool_input, dict):
                skill = tool_input.get("skill") or tool_input.get("skill_name") or tool_input.get("name") or ""
            # The Skill matcher fires for EVERY session skill; record only OURS,
            # since the event is attributed to our product feature record. A
            # domain of None means "not a Salesforce skill" -> skip silently.
            bare, domain = _resolve_sf_skill(skill)
            if domain is None:
                return
            _write_event("skill_dispatched", {"skill": bare, "skill_domain": domain}, payload)
            return

        if event == "agent_dispatched":
            # A subagent (Task/Agent tool) was launched. The matcher fires for EVERY
            # agent — built-ins, other plugins', and USER-AUTHORED custom agents whose
            # type strings are arbitrary and can carry PII. This telemetry is attributed
            # to OUR product feature, so we record only agents THIS plugin ships; any
            # built-in / third-party / custom agent is skipped ENTIRELY — no event —
            # exactly like a non-Salesforce skill. The free-form task prompt/description
            # is never read. _resolve_sf_agent returns "other" for anything not ours.
            raw_type = ""
            if isinstance(tool_input, dict):
                raw_type = (tool_input.get("subagent_type") or tool_input.get("subagentType")
                            or tool_input.get("agent_type") or "")
            agent_type = _resolve_sf_agent(raw_type)
            if agent_type in ("", "other"):
                return  # not one of our agents -> record nothing
            _write_event("agent_dispatched", {"agent_type": agent_type}, payload)
            return

        if event == "mcp_tool_used":
            # tool_name like: mcp__<server>__<tool>. The matcher fires for EVERY MCP,
            # but this telemetry is attributed to OUR product feature, so we record
            # only tool use from a server THIS plugin ships. A third-party / user MCP
            # server (arbitrary name, possibly PII) is skipped ENTIRELY — no event —
            # exactly like a non-Salesforce skill. _classify_mcp returns "other" for
            # anything not ours.
            server, mcp_tool = _classify_mcp(tool_name)
            if server in ("", "other"):
                return  # not one of our MCP servers -> record nothing
            _write_event("mcp_tool_used", {
                "mcp_server": server,
                "mcp_tool": mcp_tool,
                "outcome": outcome or "success",
            }, payload)
            return

        if event == "exception":
            # StopFailure payload carries an `error_type` (rate_limit, overloaded, …).
            error_class = payload.get("error_type") or payload.get("errorType") or "unknown"
            # `kind` distinguishes an API-error turn from a plugin-hook failure.
            # It arrives as the capture arg (argv[3], read into `outcome`); the
            # StopFailure hook passes "api_error", a hook wrapper would pass "hook".
            kind = outcome if outcome in ("api_error", "hook") else "api_error"
            _write_event("exception", {"error_class": error_class, "kind": kind}, payload)
            return

    except Exception:
        pass  # fail-silent — never break a hook on a telemetry error
    finally:
        _CAPTURE_STAGE = None
        # Commit this capture's staged event to the shared session buffer ONLY if
        # consent did not change during the capture — still on AND the same generation
        # (so no `off`, nor an off->on toggle, landed after our gate). Otherwise drop
        # the staged event. Either way remove the private stage. Crucially this only
        # ever touches THIS capture's own stage, never another capture's committed
        # events, so a stale capture cannot delete valid, re-enabled events (only
        # `off`'s own purge clears the shared buffer).
        #
        # The re-check + append run UNDER the machine-wide consent lock so they are
        # atomic against a concurrent `off` (save + purge). With the lock, an opt-out
        # either (a) completes fully before this commit — then the generation has moved
        # past gen0 and we do not commit; or (b) runs fully after — then its purge
        # clears the buffer INCLUDING this just-committed event (correct hard-off). It
        # can never interleave halfway. Because the generation is monotonic (also
        # written under this lock), a full off->on toggle leaves gen > gen0, so a
        # pre-opt-out event is never resurrected by an ABA on the generation.
        try:
            staged = stage.exists() and stage.stat().st_size > 0
            if staged:
                # Fail-CLOSED: only commit while the lock is genuinely HELD. If it
                # cannot be acquired (contention past timeout, or no OS lock
                # primitive) we DROP the staged event rather than append it unlocked
                # — an unlocked commit could interleave with an opt-out's purge and
                # resurrect a pre-opt-out event, exactly the race this guards.
                with _ConsentLock() as held:
                    if held and _is_enabled() and _consent_generation() == gen0:
                        buf = _session_buffer(sid)
                        buf.parent.mkdir(parents=True, exist_ok=True)
                        with buf.open("a", encoding="utf-8") as out, \
                                stage.open(encoding="utf-8") as src:
                            out.write(src.read())
            stage.unlink(missing_ok=True)
        except OSError:
            try:
                stage.unlink(missing_ok=True)
            except OSError:
                pass
    return


def cmd_capture(argv: list[str]) -> int:
    """`telemetry-capture <event> [outcome]` — capture one event from stdin.

    Thin stdin/stdout wrapper over `capture_event`: reads the hook payload, records
    the event, and always prints a benign `{"continue": true}` so it composes with
    other hooks on the same event. Used for the events wired as standalone plugin
    hooks (session_start, skill_dispatched, agent_dispatched, mcp_tool_used,
    command_invoked failure, exception). The successful-Bash `command_invoked` path
    is instead captured in-process by the post-bash dispatcher, which calls
    `capture_event` directly so the PostToolUse Bash block stays a single, race-free
    hook.

    DISCLOSURE: the `session_start` hook is ALSO the universal first-run-notice
    trigger. It fires in EVERY ui_mode (full/compact/plain/off) and from any project
    subdirectory — unlike cmd_detect's banner, which only renders in full mode from
    the project root. So this is where we guarantee the notice is shown to EVERY
    user before any non-session event is captured (capture_event enforces the
    matching gate). We call the SAME atomic fire-once first_run_notice_lines(): its
    exclusive-create marker is a cross-process mutex, so whichever of {detect,
    this hook} runs first shows the notice and the other sees it already shown —
    the notice appears exactly once. In full mode from the root, detect usually wins
    and renders the prettier woven band; otherwise this emits a plain systemMessage
    so the disclosure still reaches the user."""
    event = argv[2] if len(argv) > 2 else ""
    outcome = argv[3] if len(argv) > 3 else ""
    payload = _read_payload()
    output = {"continue": True}
    if event == "session_start":
        # DISCLOSURE BEFORE CAPTURE — attempt disclosure FIRST, then capture only if
        # it succeeded. first_run_notice_lines() atomically creates the machine-wide
        # marker (or sees detect already created it); capture_event then gates
        # session_start on that marker existing (see its disclosure gate). So if the
        # marker could not be created (disk error), session_start is NOT buffered and
        # nothing can later be flushed without the user having been disclosed to.
        # Fire-once: returns lines (None on repeat / opt-out / CI / not-first-run);
        # when we win the race, surface them as a SessionStart systemMessage so
        # compact/plain/off and subdirectory starts — where detect draws no banner —
        # still disclose.
        try:
            lines = first_run_notice_lines()
            if lines:
                output["systemMessage"] = _render_notice_systemmessage(lines)
        except Exception:
            pass  # fail-silent — a notice error must never break the hook
    capture_event(event, outcome, payload)
    print(json.dumps(output))
    return 0


# --- Consent command (backs /salesforce-development:telemetry) ----------------

# The notice's TEXT only — no rules, no box. cmd_detect renders these lines as a
# rule-delimited band woven INTO the SessionStart banner (below the logo lockup,
# above the org guidance), so the seams and the shared 64-col rule come from the
# banner renderer, not from here. Telemetry stays fail-silent and never imports
# that renderer; it owns only the words and the fire-once gate. Lines are ≤ 64
# cols; the em-dash is single-width.
_FIRST_RUN_NOTICE_LINES = (
    "Salesforce Development Plugin - Telemetry Usage",
    "",
    "This plugin collects the following usage data to help us",
    "improve it: your operating system, the plugin version, the",
    "coarse org type (scratch, sandbox, or production), the",
    "connected org ID, a persistent machine ID, and the agent",
    "or editor running the plugin. It also collects the",
    "commands, skills, subagents, and MCP tools that ran,",
    "whether each succeeded or failed, and coarse",
    "error categories. The plugin never collects source code,",
    "org contents, file paths, credentials, or org names.",
    "",
    "To disable telemetry, run this command:",
    "  /salesforce-development:telemetry off",
    "",
    "Alternatively, set one of these environment variables to",
    '"true": SF_DISABLE_TELEMETRY or DO_NOT_TRACK.',
)


def first_run_notice_lines() -> Optional[list]:
    """Return the one-time telemetry notice as plain content lines (no rules) on
    the FIRST run ON THIS MACHINE, else None — and mark it shown so it never
    repeats. The `notified` marker is machine-wide (see _consent_file), so the
    notice shows exactly once per machine, NOT once per project. cmd_detect renders
    these as a band woven into the detect banner, so this hands back the words, not
    a framed string; the rules come from the banner.

    Honors the same gates as capture: silent when opted out (env or consent) and
    in CI. Fail-silent — any error just suppresses the notice, never raises.
    Calling this marks the notice shown, so call it exactly once per detect."""
    try:
        if _env_optout() or _is_ci():
            return None
        marker = _notified_file()
        if marker.exists():
            return None
        # Record the notice as shown by creating its OWN marker file — never by
        # writing telemetry-config.json. This is what makes the notice race-safe
        # against a concurrent `telemetry on/off`: the notice touches only this
        # marker, so it can never clobber (resurrect) the user's consent value.
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive create so two concurrent first sessions can't both "win" and
            # show the notice twice — the first creates it, the rest see FileExists.
            with open(marker, "x"):
                pass
        except FileExistsError:
            return None  # another process just showed it — don't repeat
        return list(_FIRST_RUN_NOTICE_LINES)
    except Exception:
        return None


def _notice_shown() -> bool:
    """True once the machine-wide first-run notice has been shown (or an explicit
    on/off made the notice moot). This is the disclosure precondition for capture:
    we NEVER buffer an event before the user has been shown the notice. Fail-open to
    False (no marker readable == treat as not-yet-disclosed == do not capture)."""
    try:
        return _notified_file().exists()
    except OSError:
        return False


def _render_notice_systemmessage(lines: list) -> str:
    """Render the plain notice lines as a self-contained systemMessage for the UI
    modes / entry paths that do NOT draw the full SessionStart banner (compact,
    plain, off, or a start from a project SUBDIRECTORY, where detect renders no
    banner). This is telemetry's OWN minimal framing — it deliberately does not
    import sf_context's band renderer (telemetry stays dependency-free and
    fail-silent). The full-banner path still weaves the same lines in prettier."""
    rule = "─" * 64
    return "\n".join([rule, *lines, rule])


def _mark_notified() -> None:
    """Create the notice marker if absent (idempotent). Called on an explicit
    `telemetry on/off` so the first-run notice never fires after the user has
    already made a choice. Never writes the consent file — see _notified_file."""
    try:
        marker = _notified_file()
        marker.parent.mkdir(parents=True, exist_ok=True)
        if not marker.exists():
            with open(marker, "x"):
                pass
    except (OSError, FileExistsError):
        pass


def cmd_consent(argv: list[str]) -> int:
    """`telemetry <on|off|status>` — human-readable consent control. Prints text
    (not hook JSON) because the slash command echoes output to the user."""
    action = (argv[2] if len(argv) > 2 else "status").lower()

    if action == "on":
        _mark_notified()  # an explicit choice means the first-run notice is moot
        # Serialize the transition (and its generation bump) under the machine-wide
        # consent lock so it can't interleave with a capture's stage commit or another
        # transition — keeping the generation strictly monotonic across processes. The
        # save runs ONLY while the lock is HELD: an unlocked write races other
        # transitions and locked captures, and the generation fallback alone cannot
        # rule out the rollback/ABA cases. A long timeout means it acquires in practice
        # (the kernel frees a dead holder); if it genuinely can't, we do NOT write
        # unlocked — we report it (telemetry defaults to ON, so nothing changes).
        with _ConsentLock(timeout=10.0) as held:
            on_saved = _save_consent({"enabled": True}) if held else False
        if not on_saved:
            # Report the ACTUAL effective state — don't claim "on" when the setting
            # wasn't saved and telemetry is currently off (consent-off or env opt-out).
            if _is_enabled():
                print("⚠️  Could not persist the setting (the telemetry state is busy "
                      "or unwritable).\n"
                      "   Telemetry is currently ON, but your choice was not saved and "
                      "may not\n   persist. Try again in a moment.")
            elif _env_optout():
                print("⚠️  Could not turn telemetry ON: it is OFF via "
                      "SF_DISABLE_TELEMETRY / DO_NOT_TRACK.\n"
                      "   Unset that environment variable to enable telemetry.")
            else:
                print("⚠️  Could not turn telemetry ON (the telemetry state is busy or "
                      "unwritable).\n"
                      "   It remains OFF because the change was not saved. Try again "
                      "in a moment.")
            return 1
        print("✅ Telemetry is now ON. Usage data helps improve the plugin.\n"
              "   Turn it off any time with: /salesforce-development:telemetry off")
        return 0

    if action == "off":
        _mark_notified()  # an explicit choice means the first-run notice is moot
        # Persist the hard-off FIRST and verify it landed. Telemetry is default-ON,
        # so if the write fails we must NOT tell the user it is off — that would be a
        # false guarantee while capture keeps running. Report the failure and steer
        # them to the env opt-out, which needs no writable state. Hold the machine-wide
        # consent lock across BOTH the save and the purge so a concurrent capture's
        # stage commit cannot interleave between them (persist-off then purge is one
        # atomic critical section; the commit re-checks consent under the same lock).
        # The save + purge run ONLY while the lock is HELD: an unlocked opt-out races
        # other transitions and locked captures and can be defeated by the rollback/ABA
        # cases the generation fallback alone cannot rule out. A long timeout means it
        # acquires in practice (the kernel frees a dead holder); if it genuinely can't,
        # we do NOT write/purge unlocked — we tell the user it is STILL ON and steer
        # them to the env opt-out, which needs no lock or writable state.
        with _ConsentLock(timeout=10.0) as held:
            off_saved = _save_consent({"enabled": False}) if held else False
            if off_saved:
                # Hard-off hygiene: drop this project's buffers/stages AND any in-flight
                # snapshots/pending jobs, so nothing already staged still uploads.
                # (Snapshots in OTHER projects can't be reached from here, but the
                # detached sender re-checks the now-machine-wide consent before sending
                # — see cmd_send — so they are stopped at send time regardless.)
                _purge_local_telemetry_state()
        if not off_saved:
            # The hard-off contract is BOTH durable consent=off AND local cleanup
            # (purge). Neither ran (no lock, or the write failed), so we must NOT
            # report success (rc 0) even when telemetry is momentarily off by another
            # mechanism: a local buffer may remain on disk, and a default/ON persistent
            # consent could later reactivate telemetry and expose those old events. The
            # message reflects the ACTUAL current state (P2), but the return is ALWAYS
            # nonzero because the opt-out/cleanup did not complete.
            if _env_optout():
                print("⚠️  Telemetry is currently OFF via SF_DISABLE_TELEMETRY / "
                      "DO_NOT_TRACK, but the\n   PERSISTENT opt-out could not be saved "
                      "and local buffered events could not be\n   purged (the telemetry "
                      "state is busy or unwritable). Removing that variable\n   could "
                      "reactivate telemetry and expose old events — run `off` again in "
                      "a moment\n   to persist the opt-out and purge.")
            elif not _is_enabled():
                print("⚠️  Telemetry consent is OFF, but local buffered events could "
                      "not be purged\n   (the telemetry state is busy or unwritable). "
                      "Run `off` again in a moment to\n   complete the cleanup, or set "
                      "SF_DISABLE_TELEMETRY=true to stop capture meanwhile.")
            else:
                print("⚠️  Telemetry is STILL ON — could not persist the opt-out or "
                      "purge local state\n   (the telemetry state is busy or "
                      "unwritable).\n"
                      "   Set the environment variable SF_DISABLE_TELEMETRY=true (or "
                      "DO_NOT_TRACK=true) to\n   stop capture immediately, then run "
                      "`off` again to persist the opt-out and purge.")
            return 1
        print("🛑 Telemetry is now OFF. Nothing is captured, buffered, or sent.\n"
              "   Any locally buffered or in-flight events have been discarded.")
        return 0

    # status
    env_off = _env_optout()
    enabled = _is_enabled()
    buffered = 0
    try:
        for _b in _all_session_buffers():
            with _b.open() as _fh:
                buffered += sum(1 for _ in _fh)
    except OSError:
        pass
    lines = [
        "Salesforce Development Plugin — telemetry status",
        f"  State:            {'ON' if enabled else 'OFF'}"
        + ("  (forced off by SF_DISABLE_TELEMETRY / DO_NOT_TRACK)" if env_off else ""),
        f"  Machine id:       {_machine_id()}",
        f"  Buffered events:  {buffered}  ({_STATE_DIR}/{_BUFFER_PREFIX}-*.jsonl)",
        "  Toggle:           /salesforce-development:telemetry on | off",
    ]
    print("\n".join(lines))
    return 0


# --- Stream B: O11y-PDP transmit --------------------------------------------
# Hooks never talk to the network. On session end we project the local buffer to
# O11y PDP events and hand them to a DETACHED Node flusher (the only runtime with
# an App-Insights/O11y transport) that uploads through the connected org, exactly
# like the SF CLI's own detached uploader. The Python side owns the mapping (so it
# is unit-testable offline); the Node side is a thin transmitter.

def _to_pdp_event(record: dict, org_bucket: Optional[str] = None) -> Optional[dict]:
    """Project one buffered {envelope..., payload} record onto an O11y PDP event.

    A PDP event carries only {eventName, productFeatureId, componentId,
    eventVolume, contextName, contextValue} (see @salesforce/telemetry `PdpEvent`),
    so this is a deliberately lossy mapping: the richest per-event dimension goes to
    `componentId` (O11y's distinct-count metric), a numeric to `eventVolume` (the
    sum metric), and a flexible key/value to `contextName`/`contextValue`. Full
    fidelity always stays in the local buffer. eventName follows PDP's
    `<object>.<action>` convention (lowerCamelCase object, one-word past-tense
    action). Returns None for an unknown/garbled record so it is skipped, not sent.

    `org_bucket` (optional) overrides the coarse org classification used by the
    session_start/agent_dispatched events. Startup no longer resolves the org (to
    keep SessionStart local-first), so the buffered records carry "none"; cmd_flush
    resolves it ONCE at session end and passes it here so the transmitted events
    still carry the accurate bucket."""
    if not isinstance(record, dict):
        return None
    event = record.get("event") or ""
    p = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    org_bucket = org_bucket or record.get("org_bucket") or "none"
    base = {"productFeatureId": _PRODUCT_FEATURE_ID}

    if event == "session_start":
        # componentId keeps the model as its distinct-count dimension (the original
        # design — preserved for backward-compat with any query built on it). We ALSO
        # surface the model in the context tuple so it is queryable there and on the
        # UIP side (see _to_a4d_event), giving a consistent model dimension without
        # dropping the established componentId meaning.
        return {**base, "eventName": "session.started",
                "componentId": record.get("model") or "session",
                "contextName": "os::org_bucket::model",
                "contextValue": f"{record.get('os', '')}::{org_bucket}::{record.get('model') or ''}"}
    if event == "session_end":
        vol = p.get("event_count")
        return {**base, "eventName": "session.ended", "componentId": "session",
                "eventVolume": vol if isinstance(vol, (int, float)) else 0,
                "contextName": "duration_ms", "contextValue": str(p.get("duration_ms", 0))}
    if event == "command_invoked":
        # Only the plugin's own bins are captured now, so componentId is
        # binary(.subcommand) — e.g. `sf-context.status-org` — never a parsed CLI path.
        comp = p.get("binary") or "command"
        if p.get("subcommand"):
            comp = f"{comp}.{p['subcommand']}"
        return {**base, "eventName": "command.invoked", "componentId": comp,
                "contextName": "outcome::category",
                "contextValue": f"{p.get('outcome', '')}::{p.get('category', '')}"}
    if event == "skill_dispatched":
        # The bare skill name (platform-apex-generate) already embeds its domain,
        # so it stands alone as the componentId; skill_domain is the grouping dim.
        domain, skill = p.get("skill_domain") or "", p.get("skill") or ""
        return {**base, "eventName": "skill.dispatched",
                "componentId": skill or "skill",
                "contextName": "skill_domain", "contextValue": domain}
    if event == "agent_dispatched":
        return {**base, "eventName": "agent.dispatched",
                "componentId": p.get("agent_type") or "agent",
                "contextName": "org_bucket", "contextValue": org_bucket}
    if event == "exception":
        return {**base, "eventName": "exception.raised",
                "componentId": p.get("error_class") or "unknown",
                "contextName": "kind", "contextValue": p.get("kind") or ""}
    if event == "mcp_tool_used":
        server, tool = p.get("mcp_server") or "", p.get("mcp_tool") or ""
        return {**base, "eventName": "mcpTool.used",
                "componentId": (f"{server}.{tool}" if server else tool) or "mcp",
                "contextName": "outcome", "contextValue": p.get("outcome") or ""}
    return None


def _to_a4d_event(record: dict, org_bucket: Optional[str] = None,
                  org_id: str = "") -> Optional[dict]:
    """Project one buffered record onto a UIP event: an eventName plus a flat
    `attributes` map that the Node flusher passes to the SAME O11y reporter's
    `sendTelemetryEvent(eventName, attributes)`, which JSON-serializes the map into
    the UIP `message` field (o11y schema `sf_a4dInstrumentation`) and delivers
    through the same org proxy as the PDP events.

    UIP is a SCHEMA/event shape, not a new sink — it rides the existing O11y
    transport alongside the fixed PdpEvent shape. Adopting the flexible UIP shape
    (per the Aug 3 analytics review) lets the UIP Hive -> Tableau pipeline consume
    named attributes that PDP's fixed 6-field quadruple cannot carry.

    Like the PDP projection, this is DERIVED from _to_pdp_event so the UIP and PDP
    shapes can never diverge on the core dimensions, and it carries the same common
    envelope subset. Returns None for an unknown/garbled record so it is skipped.

    `org_id` — the raw connected-org id. Threaded here ONLY (never into PDP or App
    Insights, which stay coarse `org_bucket`-only) so the analytics team's
    account/segment/region joins can key on it; the UIP pipeline treats org id as a
    required drop-key. It is populated only when `sf org display` resolves live at
    transmit time and is added ONLY when non-empty, so the cache-fallback path emits
    no org id. The sole caller (_build_transmit_payload) passes the live-resolved
    org_id, so a live-resolved transmit DOES egress the raw org id on the UIP shape;
    only the cache-fallback path (org_id unresolved) omits it. This is disclosed in
    the first-run notice."""
    pdp = _to_pdp_event(record, org_bucket=org_bucket)
    if pdp is None:
        return None
    rec = record if isinstance(record, dict) else {}
    p = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
    attributes = {
        "componentId": pdp.get("componentId", ""),
        "contextName": pdp.get("contextName", ""),
        "contextValue": pdp.get("contextValue", ""),
        # session_Id: camelCase to match the Skills dataset column the board reads
        # (JSON_EXTRACT_SCALAR(msg, '$.properties.session_Id')).
        "session_Id": str(rec.get("session_id", "")),
        "os": str(rec.get("os", "")),
        "arch": str(rec.get("arch", "")),
        "os_version": str(rec.get("os_version", "")),
        "locale": str(rec.get("locale", "")),
        "plugin_name": str(rec.get("plugin_name", "")),
        "plugin_version": str(rec.get("plugin_version", "")),
        "org_bucket": org_bucket or rec.get("org_bucket") or "none",
        "model": str(rec.get("model", "")),
        "ci": "true" if rec.get("ci") else "false",
        "machine_id": str(rec.get("machine_id", "")),
        # harness: which agent harness ran the plugin (claude-code / cursor / codex /
        # copilot-cli / opencode / other). UIP-ONLY for now — deliberately not added
        # to the PDP shape (_to_pdp_event stays unchanged). Read downstream as
        # $.properties.harness.
        "harness": str(rec.get("harness", "")),
        # --- UIP dataset-alignment keys (Skills dashboard contract) ----------
        # These align our UIP attribute bag with the EXACT column names the shared
        # Skills dashboard (UIP Hive -> Tableau) extracts from $.properties, so a
        # team/product usage board can consume our rows directly — the dashboard
        # query reads $.properties.skillName / skillSource / modelId / session_Id
        # (camelCase), so we emit that casing verbatim. They carry NO new data off
        # the machine: skillSource is a constant, modelId/user_Id are aliases of
        # values already sent, and skillName is already in the PDP componentId.
        # UIP-only, exactly like org_id — never added to PDP.
        #
        # skillSource: constant discriminator so a board can isolate OUR rows
        # from every other producer of the same shared skill catalog.
        "skillSource": "salesforce-development",
        # modelId: alias of `model` under the column name the board groups on
        # ("Skill Calls by Model" reads modelId). Same value, no new data.
        "modelId": str(rec.get("model", "")),
        # user_Id: the board counts active users via dcount(user_Id). AFV maps
        # its pseudonymous, machine-scoped token into this key (deliberately NOT the
        # org/CLI user email — that would be PII). Our machine_id is the direct
        # analog, so aliasing it here makes MAU/DAU count us the SAME way AFV
        # counts itself, with no new/PII data — it is already what we transmit.
        "user_Id": str(rec.get("machine_id", "")),
    }
    # skillName: the per-skill dimension the board's Top-Skills charts key on
    # (JSON_EXTRACT_SCALAR(msg, '$.properties.skillName')). Only skill.dispatched
    # carries a real skill name (payload.skill); other event types are not skills,
    # so set it ONLY there rather than polluting the skillName column with
    # command/agent/mcp/exception identifiers (those stay sliceable via
    # componentId/contextName/contextValue).
    if rec.get("event") == "skill_dispatched" and p.get("skill"):
        attributes["skillName"] = str(p.get("skill"))
    # Raw org id rides UIP ONLY, and ONLY when live-resolved (non-empty) — never
    # enveloped on the buffered record, never on PDP events.
    if org_id:
        attributes["org_id"] = str(org_id)
    if "eventVolume" in pdp and isinstance(pdp["eventVolume"], (int, float)):
        attributes["eventVolume"] = pdp["eventVolume"]
    return {"eventName": pdp["eventName"], "attributes": attributes}


def _cli_node_modules() -> str:
    """Locate the installed SF CLI's node_modules — it bundles @salesforce/telemetry,
    @salesforce/core, and the o11y deps the flusher needs. Walk up from the resolved
    `sf` binary, checking a `node_modules` at each level AND a `client/node_modules`
    sibling. "" when not found (transmit then no-ops).

    The `client/node_modules` probe matters on Windows: the SF CLI installer (oclif
    tarball) puts the launcher shim in `...\\sf\\bin\\sf.cmd` but the actual libraries
    under a SIBLING `...\\sf\\client\\node_modules\\@salesforce\\telemetry` — which is
    NOT an ancestor of `bin`, so a plain walk-up never finds it and both sinks are
    silently skipped (verified on a Windows VM: cliNodeModules resolved to "" and no
    events transmitted). macOS/Linux installs are reachable by the walk-up alone, so
    the sibling probe is a superset that fixes Windows without changing POSIX."""
    import shutil
    sf = shutil.which("sf")
    if not sf:
        return ""
    d = os.path.dirname(os.path.realpath(sf))
    for _ in range(8):
        # Direct node_modules at this level (POSIX/global installs, monorepos).
        direct = os.path.join(d, "node_modules")
        if os.path.isdir(os.path.join(direct, "@salesforce", "telemetry")):
            return direct
        # `client/node_modules` sibling (Windows/macOS oclif tarball install layout,
        # where `bin/` and `client/` are siblings under the CLI root).
        client = os.path.join(d, "client", "node_modules")
        if os.path.isdir(os.path.join(client, "@salesforce", "telemetry")):
            return client
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return ""


def _build_transmit_payload(buffer_path: Optional[Path] = None) -> dict:
    """Read the local buffer and project it to a transmit job the Node flusher can
    send: the PDP events + the O11y target + the org username used to build the
    connection. The username is transmit-only (used to open the org connection),
    never itself sent as telemetry. Fail-silent — empty events list on any error.

    `buffer_path` selects which JSONL buffer to read (defaults to the live _BUFFER).
    cmd_send passes the renamed snapshot it is draining, so the live buffer is free
    to accumulate a new session's events concurrently.

    Org context is resolved HERE (once) rather than at session_start, so SessionStart
    stays local-first / single-process. This resolve makes a synchronous `sf` call,
    so it runs in the DETACHED sender process (cmd_send) — never in the SessionEnd
    hook — and therefore carries no interactive UX cost. The resolved org_bucket is
    stamped onto the transmitted events; the username opens the upload connection.
    Falls back to any cached context on failure."""
    # cmd_send passes the single renamed snapshot it is draining; cmd_transmit
    # (inspection, buffer_path=None) aggregates every per-session buffer.
    buffers = [buffer_path] if buffer_path is not None else _all_session_buffers()
    org = _resolve_org_context()
    if not org.get("username") and not org.get("org_id"):
        # `sf org display` didn't resolve (e.g. sf absent) — fall back to a cache
        # written by an earlier flush, so a transient miss doesn't lose the bucket.
        org = _org_context()
    org_bucket = org.get("org_bucket") or "none"
    # Raw org id rides UIP ONLY (never PDP, never the buffer/cache). It is populated
    # only when `sf org display` resolved live above — empty on the cache-fallback
    # path (the cache deliberately never persists the org id), so a cache-only
    # transmit emits no org id.
    org_id = org.get("org_id") or ""
    events = []       # O11y PDP-shape events (org proxy -> Huron)
    a4d_events = []   # O11y UIP-shape events (SAME org proxy -> UIP Hive -> Tableau)
    for bp in buffers:
        try:
            with bp.open(encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    pdp = _to_pdp_event(rec, org_bucket=org_bucket)
                    if pdp is not None:
                        events.append(pdp)
                    # UIP rides the SAME O11y transport as PDP; it is a second event
                    # SHAPE, not a new sink. It ALONE carries the raw org id (when
                    # live-resolved) so the analytics team's account/segment/region
                    # joins can key on it — the UIP pipeline treats org id as a
                    # required drop-key. Disclosed in the first-run notice.
                    a4d = _to_a4d_event(rec, org_bucket=org_bucket, org_id=org_id)
                    if a4d is not None:
                        a4d_events.append(a4d)
        except OSError:
            continue
    return {
        "productFeatureId": _PRODUCT_FEATURE_ID,
        "project": _O11Y_PROJECT,
        "username": org.get("username", ""),
        "machineId": _machine_id(),
        "cliNodeModules": _cli_node_modules(),
        "events": events,
        # UIP-shape events for the SAME O11y transport (org proxy). The flusher emits
        # these on the reporter it already built for PDP via `sendTelemetryEvent`, so
        # this is NOT a new sink — just a second event shape on the O11y leg, feeding
        # the UIP Hive -> Tableau pipeline that consumes UIP's flexible attributes.
        "a4dEvents": a4d_events,
        # Absolute path to the machine-wide consent file so the detached Node
        # flusher can re-check opt-out at the last moment — closing the window
        # where `telemetry off` lands after this job was queued, incl. for a job
        # queued by another project (whose pending file `off` cannot reach).
        "consentFile": str(_consent_file()),
    }


def _flusher_js() -> Path:
    return Path(__file__).resolve().parent / "telemetry-flush.js"


def _spawn_flusher(pending: Path) -> bool:
    """Spawn the detached Node flusher on `pending`. Returns True if launched.
    Detached so it outlives the caller and never blocks it on the network."""
    import shutil
    node = shutil.which("node")
    flusher = _flusher_js()
    if not node or not flusher.exists():
        return False
    try:
        log = open(_TRANSMIT_LOG, "ab")  # noqa: SIM115 — handed to the child
    except OSError:
        log = subprocess.DEVNULL
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": log}
    if os.name == "nt":
        # DETACHED_PROCESS | CREATE_NO_WINDOW — survive the parent exiting.
        kwargs["creationflags"] = 0x00000008 | 0x08000000
    else:
        kwargs["start_new_session"] = True  # new session leader; no SIGHUP on parent exit
    try:
        subprocess.Popen([node, str(flusher), str(pending)], **kwargs)
        return True
    except OSError:
        return False


def _spawn_sender(snapshot: Path) -> bool:
    """Spawn the DETACHED Python sender (`telemetry-send`) on a buffer `snapshot`.

    This is what keeps the SessionEnd HOOK non-blocking: the hook does only cheap
    local work (write session_end, rename the buffer to `snapshot`, spawn this) and
    returns in milliseconds. ALL the slow work — the synchronous `sf org display`
    org-context resolve and the org-bucket classification — happens HERE, in a
    process detached from the hook, so it can never delay the user's session. Run in
    the SAME interpreter (sys.executable) on this module so no reimplementation of
    the tested scrub/classify/shape logic leaks into another language."""
    try:
        log = open(_TRANSMIT_LOG, "ab")  # noqa: SIM115 — handed to the child
    except OSError:
        log = subprocess.DEVNULL
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": log}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x08000000
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "telemetry-send", str(snapshot)],
            **kwargs,
        )
        return True
    except OSError:
        return False


def _purge_local_telemetry_state() -> None:
    """Delete this project's live buffer plus any in-flight snapshot/pending files,
    so a `telemetry off` leaves nothing staged to upload. Fail-silent."""
    try:
        for b in _all_session_buffers():
            b.unlink(missing_ok=True)
        # Legacy compatibility: earlier builds of this feature used a single shared
        # buffer (telemetry-buffer.jsonl, no session suffix), which the per-session
        # glob above does NOT match. A hard-off promises to discard ALL locally
        # buffered events, so explicitly unlink the legacy file too — otherwise a
        # project carried over from a pre-per-session build would keep its buffered
        # telemetry after the user was told it was discarded.
        (_STATE_DIR / f"{_BUFFER_PREFIX}.jsonl").unlink(missing_ok=True)
    except OSError:
        pass
    # Also drop the org cache: it holds the transmit-only username, which must not
    # survive an opt-out. (org_id is no longer cached — see _resolve_org_context.)
    try:
        _ORG_CACHE.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        for p in _STATE_DIR.glob("telemetry-snapshot-*.jsonl"):
            p.unlink(missing_ok=True)
        for p in _STATE_DIR.glob("telemetry-pending-*.json"):
            p.unlink(missing_ok=True)
        for p in _STATE_DIR.glob("telemetry-stage-*.jsonl"):
            p.unlink(missing_ok=True)
    except OSError:
        pass


def _buffer_has_events() -> bool:
    """True iff ANY per-session buffer holds at least one non-blank line."""
    for b in _all_session_buffers():
        try:
            with b.open(encoding="utf-8") as fh:
                if any(line.strip() for line in fh):
                    return True
        except OSError:
            continue
    return False


def _session_has_events(session_id: str) -> bool:
    """True iff THIS session's own buffer holds at least one non-blank line. Per-
    session buffers mean the SessionEnd hook inspects and drains only its own file,
    so a concurrent session is never observed, drained, or misattributed."""
    try:
        with _session_buffer(session_id).open(encoding="utf-8") as fh:
            return any(line.strip() for line in fh)
    except OSError:
        return False


def cmd_flush(argv: list[str]) -> int:
    """`telemetry-flush` — SessionEnd hook. Hand the buffer off for async transmit.

    NON-BLOCKING BY CONSTRUCTION: this hook does ONLY cheap, local, network-free
    work — it must never delay the user's session close. It appends session_end,
    atomically renames the buffer to a private snapshot (so a new session starts
    clean), and spawns a DETACHED Python sender that does the slow `sf` org resolve
    and the actual upload. The hook itself makes NO `sf` call and touches NO network.
    Consent-gated and fail-silent; always prints {"continue": true} so it composes
    with any other SessionEnd hook.

    A session with no captured activity is skipped wholesale (no session_end, no
    spawn) — there is nothing worth an upload."""
    def _done() -> int:
        print(json.dumps({"continue": True}))
        return 0
    if not _is_enabled():
        return _done()
    # DISCLOSURE GATE (belt-and-braces): never transmit without the user having been
    # shown the notice. Capture is already gated on the marker, so a buffer should
    # never exist pre-disclosure — but a buffer left by an older build, or a marker
    # removed between capture and flush, must not slip through. In CI there is no
    # human to notify, so the CI path is unchanged.
    if not _is_ci() and not _notice_shown():
        return _done()
    try:
        payload = _read_payload()
        sid = payload.get("session_id") or payload.get("sessionId") or ""
        buf = _session_buffer(sid)
        # Flush only when THIS session captured something.
        if not _session_has_events(sid):
            return _done()
        # This hook is the SOLE SessionEnd writer: emit session_end here (rather
        # than as a parallel capture hook) so the end event is written by one
        # process — no race with the rename below.
        _write_session_end(payload)
        # Atomically hand THIS session's OWN buffer to the sender by renaming it to a
        # private snapshot. Because it is a per-session file, this rename touches no
        # other session's records — no partition, no restore, no cross-session race:
        # a concurrent session's SessionEnd renames a DIFFERENT inode.
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        snapshot = _STATE_DIR / f"telemetry-snapshot-{os.getpid()}.jsonl"
        try:
            os.replace(buf, snapshot)
        except OSError:
            return _done()  # can't snapshot — leave the buffer for the next flush
        # If the detached sender fails to launch, the snapshot would otherwise sit on
        # disk indefinitely. It holds only scrubbed, bucket-only records (no username
        # — that is resolved later, by the sender), but a stranded file is still
        # unbounded local cruft, so drop it on a failed spawn.
        if not _spawn_sender(snapshot):
            try:
                snapshot.unlink(missing_ok=True)
            except OSError:
                pass
    except Exception:
        pass
    return _done()


def cmd_send(argv: list[str]) -> int:
    """`telemetry-send <snapshot>` — the DETACHED sender (never a hook).

    Builds the transmit job from the buffer `snapshot` (this is where the slow
    synchronous `sf org display` resolve happens — off the hook's critical path),
    writes a private pending file, spawns the Node uploader on it, and deletes the
    snapshot. Fail-silent; the pending file is deleted by the Node flusher itself.

    RE-CHECKS CONSENT: this runs detached, AFTER the SessionEnd hook returned, so
    the user may have run `telemetry off` (or set SF_DISABLE_TELEMETRY /
    DO_NOT_TRACK) in the interval between the hook spawning us and us sending. We
    re-read the machine-wide consent HERE and, if now disabled, drop the snapshot
    and send nothing — so opt-out reliably stops an in-flight upload."""
    snapshot = Path(argv[2]) if len(argv) > 2 else None
    if snapshot is None or not snapshot.exists():
        return 0
    # Opt-out that landed after the hook spawned us must still win: discard and stop.
    if not _is_enabled():
        try:
            snapshot.unlink(missing_ok=True)
        except OSError:
            pass
        return 0
    try:
        payload = _build_transmit_payload(buffer_path=snapshot)
        if payload["events"] or payload.get("a4dEvents"):
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            pending = _STATE_DIR / f"telemetry-pending-{os.getpid()}.json"
            pending.write_text(json.dumps(payload))
            # The pending job carries the transmit-only USERNAME (to open the org
            # connection). If the Node flusher fails to launch it normally deletes the
            # file when done — but a failed launch never runs, so the username would
            # be stranded on disk indefinitely. Delete it ourselves on spawn failure.
            if not _spawn_flusher(pending):  # Node uploader; deletes pending when done
                try:
                    pending.unlink(missing_ok=True)
                except OSError:
                    pass
    except Exception:
        pass
    finally:
        try:
            snapshot.unlink(missing_ok=True)
        except OSError:
            pass
        # The org cache exists only to carry the transmit-only username (and a
        # coarse-bucket fallback) from resolve time to here. Now that the job is
        # queued, drop it so the username is not retained on disk between sessions;
        # the next session re-resolves the org fresh. (org_id is never cached.)
        try:
            _ORG_CACHE.unlink(missing_ok=True)
        except OSError:
            pass
    return 0


def cmd_transmit(argv: list[str]) -> int:
    """`telemetry-transmit` — print the transmit job as JSON WITHOUT sending or
    spawning. Used by tests and for manual inspection ("what would be sent?").
    Consent-gated: prints an empty job when disabled."""
    if not _is_enabled():
        print(json.dumps({"enabled": False, "events": []}))
        return 0
    print(json.dumps({"enabled": True, **_build_transmit_payload()}))
    return 0


# --- Dispatch (called by sf_context.main for any telemetry* command) ---------

def dispatch(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "telemetry-flush":
        return cmd_flush(argv)
    if cmd == "telemetry-send":
        return cmd_send(argv)
    if cmd == "telemetry-transmit":
        return cmd_transmit(argv)
    if cmd == "telemetry":
        return cmd_consent(argv)
    if cmd == "telemetry-capture":
        return cmd_capture(argv)
    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    sys.exit(dispatch(sys.argv))
