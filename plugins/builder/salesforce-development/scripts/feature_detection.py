#!/usr/bin/env python3
"""On-demand, normalized Salesforce org-feature detection with a safe user cache.

The detector intentionally uses only the Python standard library. It never runs
at SessionStart, and it never persists raw CLI responses, org identifiers, org
aliases, package rows, usernames, URLs, or credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import namedtuple
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

SCHEMA_VERSION = "1.0"
CACHE_SCHEMA_VERSION = "2.0"
MAPPING_RELATIVE = Path("catalog/feature-domains.json")
FEATURE_ORDER = ("data360", "omnistudio", "devops-center")
PRESENT_TTL_SECONDS = 30 * 60
UNKNOWN_TTL_SECONDS = 5 * 60
COMMAND_TIMEOUT_SECONDS = 30
PACKAGE_QUERY = (
    "SELECT Id, SubscriberPackage.Name, SubscriberPackage.NamespacePrefix "
    "FROM InstalledSubscriberPackage ORDER BY SubscriberPackage.Name LIMIT 100"
)

CommandResult = namedtuple("CommandResult", ["ok", "stdout", "returncode", "reason"])

_DATA_UNKNOWN = (
    "Core REST reachability could not be established; authentication, permission, "
    "endpoint, command, timeout, or response failures are unknown rather than absence."
)
_DATA_EMPTY = (
    "Endpoint reachable but no accessible data spaces; readiness not established."
)
_OMNI_NAME_MATCH = (
    "Conservative package-name signal present; package identity, publisher, version, and "
    "legacy status are not verified. Vlocity-prefixed matches are name-only evidence."
)
_DEVOPS_NAME_MATCH = (
    "Conservative package-name signal present; package identity, publisher, version, and "
    "legacy status are not verified."
)
_OMNI_NOT_DETECTED = (
    "No conservative OmniStudio/Vlocity package-name match in the bounded LIMIT 100 "
    "inventory; standard or package-less runtime surfaces are not covered, so this is "
    "not authoritative absence."
)
_DEVOPS_NOT_DETECTED = (
    "No conservative DevOps Center package-name match in the bounded LIMIT 100 inventory; "
    "the next-generation product is not covered, so this is not authoritative absence."
)
_PACKAGE_UNAVAILABLE = (
    "Installed package inventory could not be validated; permission, schema, command, "
    "timeout, or response failures are unknown rather than absence."
)

# Single source of truth for a feature row's limitation prose, keyed on the
# (feature, evidence-kind) pair. `_feature` is the ONLY place that attaches a
# limitation, and both the live probes and the cache-hit reconstruction
# (_cache_rows_to_output) build their rows through `_feature` — so a cache-hit can
# never carry different, or missing, limitation text than a fresh --refresh would
# for identical evidence. A reachable-with-data data360 (and any unlisted pair)
# maps to no limitation.
_LIMITATION_BY_EVIDENCE = {
    ("data360", "core-rest-reachable-empty"): _DATA_EMPTY,
    ("data360", "core-rest-unavailable"): _DATA_UNKNOWN,
    ("omnistudio", "package-name-match"): _OMNI_NAME_MATCH,
    ("omnistudio", "package-name-not-detected"): _OMNI_NOT_DETECTED,
    ("omnistudio", "package-inventory-unavailable"): _PACKAGE_UNAVAILABLE,
    ("devops-center", "package-name-match"): _DEVOPS_NAME_MATCH,
    ("devops-center", "package-name-not-detected"): _DEVOPS_NOT_DETECTED,
    ("devops-center", "package-inventory-unavailable"): _PACKAGE_UNAVAILABLE,
}


def _limitation(name: str, kind: str) -> Optional[str]:
    """The limitation prose for a (feature, evidence-kind) pair, or None."""
    return _LIMITATION_BY_EVIDENCE.get((name, kind))


_OMNI_PACKAGE_NAMES = {
    "omnistudio",
    "vlocity",
    "vlocity communications",
    "vlocity energy",
    "vlocity energy and utilities",
    "vlocity enterprise product catalog",
    "vlocity government",
    "vlocity health",
    "vlocity insurance",
    "vlocity media",
    "vlocity media and entertainment",
    "vlocity public sector",
}
_DEVOPS_PACKAGE_NAMES = {"devops center", "salesforce devops center"}


class FeatureDetectionError(ValueError):
    """A bounded, safe error that contains no org-specific values."""


def load_feature_domains(plugin_root: Path) -> dict[str, str]:
    """Load the static mapping policy, which is deliberately not cached as evidence."""
    path = plugin_root / MAPPING_RELATIVE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FeatureDetectionError("feature/domain mapping is unavailable") from exc
    expected = {"data360": "data360", "devops-center": "dx", "omnistudio": "omnistudio"}
    if data.get("schemaVersion") != SCHEMA_VERSION or data.get("features") != expected:
        raise FeatureDetectionError("feature/domain mapping has an unsupported schema")
    return dict(data["features"])


def default_cache_root(home: Optional[Path] = None) -> Path:
    """Return an OS/XDG cache path outside Salesforce CLI state directories."""
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        base = Path(xdg).expanduser()
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (home or Path.home()) / "AppData/Local")
    elif sys.platform == "darwin":
        base = (home or Path.home()) / "Library/Caches"
    else:
        base = (home or Path.home()) / ".cache"
    return base / "sf-context" / "discovery-features"


def _subprocess_runner(argv: list[str], timeout: Optional[int] = None) -> CommandResult:
    """Fallback runner for direct module use; sf-context supplies its central runner."""
    executable = shutil.which(argv[0])
    if not executable:
        return CommandResult(False, "", None, "unresolved")
    command = [executable, *argv[1:]]
    if os.name == "nt" and executable.lower().endswith((".cmd", ".bat")):
        # Fixed detector args and validated aliases are passed as argv, never a shell string.
        unsafe = "&|<>^%!\"\n\r"
        if any(any(char in token for char in unsafe) for token in command):
            return CommandResult(False, "", None, "unresolved")
        command = [os.environ.get("COMSPEC", "cmd.exe"), "/c", *command]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout or COMMAND_TIMEOUT_SECONDS,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(False, "", None, "timeout")
    except (FileNotFoundError, OSError):
        return CommandResult(False, "", None, "error")
    if completed.returncode != 0:
        return CommandResult(False, "", completed.returncode, "nonzero")
    return CommandResult(True, completed.stdout, 0, "")


def _json_object(result: CommandResult) -> Optional[dict]:
    if not result.ok:
        return None
    try:
        parsed = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _result_object(result: CommandResult) -> Optional[dict]:
    parsed = _json_object(result)
    if parsed is None:
        return None
    nested = parsed.get("result")
    return nested if isinstance(nested, dict) else parsed


def _parse_args(args: list[str]) -> tuple[Optional[str], bool, bool]:
    target: Optional[str] = None
    refresh = False
    json_mode = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--target-org" and target is None and index + 1 < len(args):
            target = args[index + 1]
            if not target or target.startswith("-"):
                raise FeatureDetectionError("invalid target-org option")
            index += 2
        elif arg == "--refresh" and not refresh:
            refresh = True
            index += 1
        elif arg == "--json" and not json_mode:
            json_mode = True
            index += 1
        else:
            raise FeatureDetectionError("unsupported or repeated feature option")
    return target, refresh, json_mode


def _configured_target(runner: Callable) -> str:
    result = runner(["sf", "config", "get", "target-org", "--json"], timeout=COMMAND_TIMEOUT_SECONDS)
    data = _json_object(result)
    rows = data.get("result") if data else None
    if not isinstance(rows, list):
        raise FeatureDetectionError("no usable configured target-org")
    for row in rows:
        if isinstance(row, dict) and row.get("name") == "target-org":
            value = row.get("value")
            if isinstance(value, str) and value:
                return value
    raise FeatureDetectionError("no usable configured target-org")


def _org_context(target: str, runner: Callable) -> tuple[str, str]:
    result = runner(
        ["sf", "org", "display", "--target-org", target, "--json"],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    data = _result_object(result)
    if data is None:
        raise FeatureDetectionError("org display did not return usable identity and API data")
    api = data.get("apiVersion")
    org_id = data.get("id") or data.get("orgId")
    instance = data.get("instanceUrl")
    principal = data.get("username")
    host = urlparse(instance).hostname if isinstance(instance, str) else None
    if not isinstance(api, str) or not re.fullmatch(r"\d+\.\d+", api):
        raise FeatureDetectionError("org display did not return a valid API version")
    if (not isinstance(org_id, str) or not org_id or not host
            or not isinstance(principal, str) or not principal.strip()):
        raise FeatureDetectionError("org display did not return usable stable identity")
    hash_input = f"{org_id}\0{host.lower()}\0{principal.strip().casefold()}"
    identity = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return api, identity


def _feature(name: str, domain: str, status: str, kind: str, count: int) -> dict:
    row = {
        "feature": name,
        "domain": domain,
        "status": status,
        "evidence": {"kind": kind, "matchedCount": count},
    }
    # The limitation is derived from (feature, evidence-kind) here — the one place
    # rows are built — so probe and cache-hit rows can't carry divergent text.
    limitation = _limitation(name, kind)
    if limitation:
        row["limitation"] = limitation
    return row


def _probe_data360(target: str, api: str, domain: str, runner: Callable) -> dict:
    result = runner(
        ["sf", "api", "request", "rest", f"/services/data/v{api}/ssot/data-spaces", "-o", target],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    data = _json_object(result)
    if data is not None and isinstance(data.get("result"), dict):
        data = data["result"]
    spaces = data.get("dataSpaces") if data else None
    if isinstance(spaces, list) and spaces:
        return _feature("data360", domain, "present", "core-rest-reachable", len(spaces))
    if isinstance(spaces, list):
        return _feature("data360", domain, "unknown", "core-rest-reachable-empty", 0)
    return _feature("data360", domain, "unknown", "core-rest-unavailable", 0)


def _unknown_package_features(domains: dict[str, str]) -> list[dict]:
    return [
        _feature("omnistudio", domains["omnistudio"], "unknown", "package-inventory-unavailable", 0),
        _feature("devops-center", domains["devops-center"], "unknown", "package-inventory-unavailable", 0),
    ]


def _probe_packages(target: str, domains: dict[str, str], runner: Callable) -> list[dict]:
    described = runner(
        ["sf", "sobject", "describe", "-s", "InstalledSubscriberPackage",
         "--use-tooling-api", "-o", target, "--json"],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    shape = _result_object(described)
    fields = shape.get("fields") if shape else None
    relationship_ok = isinstance(fields, list) and any(
        isinstance(field, dict)
        and field.get("name") == "SubscriberPackageId"
        and field.get("relationshipName") == "SubscriberPackage"
        for field in fields
    )
    if shape is None or shape.get("queryable") is not True or not relationship_ok:
        return _unknown_package_features(domains)

    queried = runner(
        ["sf", "data", "query", "--use-tooling-api", "--query", PACKAGE_QUERY,
         "--target-org", target, "--json"],
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    data = _result_object(queried)
    records = data.get("records") if data else None
    if not isinstance(records, list):
        return _unknown_package_features(domains)

    omni_count = 0
    devops_count = 0
    for record in records:
        package = record.get("SubscriberPackage") if isinstance(record, dict) else None
        name = package.get("Name") if isinstance(package, dict) else None
        if not isinstance(name, str):
            continue
        normalized = " ".join(name.casefold().split())
        if normalized in _OMNI_PACKAGE_NAMES:
            omni_count += 1
        if normalized in _DEVOPS_PACKAGE_NAMES:
            devops_count += 1

    omni = (
        _feature("omnistudio", domains["omnistudio"], "present", "package-name-match", omni_count)
        if omni_count
        else _feature("omnistudio", domains["omnistudio"], "unknown", "package-name-not-detected", 0)
    )
    devops = (
        _feature("devops-center", domains["devops-center"], "present", "package-name-match", devops_count)
        if devops_count
        else _feature("devops-center", domains["devops-center"], "unknown", "package-name-not-detected", 0)
    )
    return [omni, devops]


def _safe_cache_features(value) -> Optional[list[dict]]:
    if not isinstance(value, list) or len(value) != len(FEATURE_ORDER):
        return None
    by_name = {}
    allowed_outcomes = {
        "data360": {
            ("present", "core-rest-reachable"),
            ("unknown", "core-rest-reachable-empty"),
            ("unknown", "core-rest-unavailable"),
        },
        "omnistudio": {
            ("present", "package-name-match"),
            ("unknown", "package-name-not-detected"),
            ("unknown", "package-inventory-unavailable"),
        },
        "devops-center": {
            ("present", "package-name-match"),
            ("unknown", "package-name-not-detected"),
            ("unknown", "package-inventory-unavailable"),
        },
    }
    for row in value:
        if not isinstance(row, dict) or set(row) != {"feature", "status", "evidence"}:
            return None
        name, status, evidence = row.get("feature"), row.get("status"), row.get("evidence")
        if name not in FEATURE_ORDER or name in by_name:
            return None
        if not isinstance(evidence, dict) or set(evidence) != {"kind", "matchedCount"}:
            return None
        kind, count = evidence.get("kind"), evidence.get("matchedCount")
        if ((status, kind) not in allowed_outcomes[name]
                or not isinstance(count, int) or isinstance(count, bool) or count < 0):
            return None
        if (status == "present") != (count > 0):
            return None
        by_name[name] = {"feature": name, "status": status,
                         "evidence": {"kind": kind, "matchedCount": count}}
    if set(by_name) != set(FEATURE_ORDER):
        return None
    return [by_name[name] for name in FEATURE_ORDER]


def _cache_rows_to_output(cached: list[dict], domains: dict[str, str]) -> list[dict]:
    # `_feature` re-derives the limitation from (feature, evidence-kind) via the
    # single _LIMITATION_BY_EVIDENCE map, so a cache-hit row is identical to the
    # fresh probe row for the same evidence — no independent re-derivation to drift.
    return [
        _feature(row["feature"], domains[row["feature"]], row["status"],
                 row["evidence"]["kind"], row["evidence"]["matchedCount"])
        for row in cached
    ]


def _cache_path(cache_root: Path, identity_hash: str) -> Path:
    return cache_root / f"{identity_hash}.json"


def _read_cache(path: Path, api: str, now: float) -> Optional[list[dict]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or set(data) != {
        "schemaVersion", "createdAtEpoch", "ttlSeconds", "apiVersion", "features"
    }:
        return None
    if data.get("schemaVersion") != CACHE_SCHEMA_VERSION or data.get("apiVersion") != api:
        return None
    created, ttl = data.get("createdAtEpoch"), data.get("ttlSeconds")
    if not isinstance(created, (int, float)) or ttl not in {PRESENT_TTL_SECONDS, UNKNOWN_TTL_SECONDS}:
        return None
    if now < created or now - created >= ttl:
        return None
    return _safe_cache_features(data.get("features"))


def _write_cache(path: Path, api: str, rows: list[dict], now: float) -> None:
    safe = [
        {"feature": row["feature"], "status": row["status"], "evidence": dict(row["evidence"])}
        for row in rows
    ]
    ttl = PRESENT_TTL_SECONDS if all(row["status"] == "present" for row in safe) else UNKNOWN_TTL_SECONDS
    body = {
        "schemaVersion": CACHE_SCHEMA_VERSION,
        "createdAtEpoch": now,
        "ttlSeconds": ttl,
        "apiVersion": api,
        "features": safe,
    }
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n"
    temporary = path.parent / f".{path.stem}.{os.getpid()}.tmp"
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            path.parent.chmod(0o700)
        except OSError:
            pass
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except OSError:
        try:
            temporary.unlink()
        except OSError:
            pass
        # Detection remains useful if a user cache is temporarily unwritable.


def _elapsed(start: float, end: float) -> int:
    return max(0, round((end - start) * 1000))


def _print_human(data: dict) -> None:
    print("Salesforce org-feature detection (on-demand)")
    print(f"Cache: {data['cacheState']} | API: {data['apiVersion']} | total: {data['elapsedMs']['total']} ms")
    present = [row for row in data["features"] if row["status"] == "present"]
    unknown = [row for row in data["features"] if row["status"] != "present"]
    print("\nPresent domains")
    if not present:
        print("- (none detected)")
    for row in present:
        limitation = f" — {row['limitation']}" if row.get("limitation") else ""
        print(f"- {row['domain']} ({row['feature']}): present via {row['evidence']['kind']}"
              f"{limitation}")
    print("\nUnknown / limitations")
    if not unknown:
        print("- (none)")
    for row in unknown:
        print(f"- {row['domain']} ({row['feature']}): unknown — {row['limitation']}")


def _emit_error(message: str, json_mode: bool) -> int:
    if json_mode:
        print(json.dumps({"schemaVersion": SCHEMA_VERSION, "mode": "features", "error": message},
                         separators=(",", ":")))
    else:
        print(f"Feature detection error: {message}", file=sys.stderr)
        print("Use: sf-context discovery features [--target-org <alias>] [--refresh] [--json]",
              file=sys.stderr)
    return 2


def run_features(
    args: list[str],
    *,
    plugin_root: Path,
    runner: Optional[Callable] = None,
    cache_root: Optional[Path] = None,
    monotonic: Callable[[], float] = time.monotonic,
    wall_clock: Callable[[], float] = time.time,
) -> int:
    """Run the bounded feature detector and print human or compact JSON output."""
    json_hint = "--json" in args
    try:
        target, refresh, json_mode = _parse_args(args)
        domains = load_feature_domains(plugin_root)
        runner = runner or _subprocess_runner
        target = target or _configured_target(runner)
        total_start = monotonic()
        api, identity_hash = _org_context(target, runner)
        root = cache_root or default_cache_root()
        cache_path = _cache_path(root, identity_hash)
        now = wall_clock()

        if not refresh:
            cached = _read_cache(cache_path, api, now)
            if cached is not None:
                rows = _cache_rows_to_output(cached, domains)
                total_end = monotonic()
                output = {
                    "schemaVersion": SCHEMA_VERSION,
                    "mode": "features",
                    "cacheState": "cache-hit",
                    "apiVersion": api,
                    "featureDomains": domains,
                    "features": rows,
                    "elapsedMs": {"data360": 0, "packageInventory": 0,
                                  "total": _elapsed(total_start, total_end)},
                }
                if json_mode:
                    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
                else:
                    _print_human(output)
                return 0

        data_start = monotonic()
        data_row = _probe_data360(target, api, domains["data360"], runner)
        data_end = monotonic()
        package_start = monotonic()
        package_rows = _probe_packages(target, domains, runner)
        package_end = monotonic()
        rows = [data_row, *package_rows]
        _write_cache(cache_path, api, rows, now)
        total_end = monotonic()
        output = {
            "schemaVersion": SCHEMA_VERSION,
            "mode": "features",
            "cacheState": "refresh",
            "apiVersion": api,
            "featureDomains": domains,
            "features": rows,
            "elapsedMs": {
                "data360": _elapsed(data_start, data_end),
                "packageInventory": _elapsed(package_start, package_end),
                "total": _elapsed(total_start, total_end),
            },
        }
        if json_mode:
            print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
        else:
            _print_human(output)
        return 0
    except FeatureDetectionError as exc:
        return _emit_error(str(exc), json_hint)
