"""Metadata API listMetadata wrappers — for sObjects that are NOT
exposed via SOQL on Tooling or Data API (e.g. GenAiPromptTemplate).

Wraps the sf CLI `sf org list metadata` recipe. Not a REST client call —
uses subprocess via sf_cli.run_sf. Failure semantics mirror the rest:
returns [] on known-missing + surfaces unresolved reasons upstream;
raises SfCliError / AuthRequired on unknown failures.
"""
from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from rest_client import redact_error
from sf_cli import (
    AuthRequired,
    _redact_subprocess_stderr,
    _stderr_matches_auth,
    run_sf,
)


# Metadata XML default namespace — same as parse_bundle.NS. Duplicated
# (rather than imported) to keep the "no intra-skill imports" convention
# documented throughout the pipeline.
_NS = {"sf": "http://soap.sforce.com/2006/04/metadata"}


def list_prompt_template_metadata(org_alias: str) -> List[Dict[str, str]]:
    """Return every GenAiPromptTemplate metadata component in the org.

    Each row has the shape produced by `sf org list metadata --json`:
      {"id": "0hfUv...", "fullName": "AGNT_...", "type": "GenAiPromptTemplate",
       "namespacePrefix": "...", ...}

    Empty list on success with no templates. Raises SfCliError on CLI
    failure (caller decides whether to treat as fatal).
    """
    data = run_sf("list_metadata_genaiprompttemplate", ORG_ALIAS=org_alias)
    result = data.get("result")
    if not isinstance(result, list):
        return []
    return [r for r in result if isinstance(r, dict)]


def _find_text(el: ET.Element | None, path: str) -> str | None:
    if el is None:
        return None
    found = el.find(path, _NS)
    if found is None:
        return None
    return found.text


def _parse_prompt_template_xml(xml_bytes: bytes) -> Dict[str, Any] | None:
    """Parse a single .genAiPromptTemplate XML file into a body dict.

    Returns None on parse failure so the caller can log + skip. The
    returned dict carries developerName/masterLabel/activeVersionIdentifier/
    content/inputs — absent optional fields become None or empty lists.

    Version selection: if multiple <templateVersions> elements exist,
    prefer the one whose `versionIdentifier` matches the template-level
    `activeVersionIdentifier`; otherwise fall back to the first version.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None

    developer_name = _find_text(root, "sf:developerName")
    master_label = _find_text(root, "sf:masterLabel")
    active_version = _find_text(root, "sf:activeVersionIdentifier")

    versions = root.findall("sf:templateVersions", _NS)
    picked: ET.Element | None = None
    if versions:
        if active_version:
            for v in versions:
                vid = _find_text(v, "sf:versionIdentifier")
                if vid and vid == active_version:
                    picked = v
                    break
        if picked is None:
            picked = versions[0]

    content = _find_text(picked, "sf:content") if picked is not None else None

    inputs: List[Dict[str, str]] = []
    if picked is not None:
        for inp in picked.findall("sf:inputs", _NS):
            name = _find_text(inp, "sf:apiName") or _find_text(inp, "sf:name")
            data_type = _find_text(inp, "sf:dataType")
            if name is None and data_type is None:
                continue
            entry: Dict[str, str] = {}
            if name is not None:
                entry["name"] = name
            if data_type is not None:
                entry["dataType"] = data_type
            inputs.append(entry)

    return {
        "developerName": developer_name,
        "masterLabel": master_label,
        "activeVersionIdentifier": active_version,
        "content": content,
        "inputs": inputs,
    }


# Timeout for `sf project retrieve start` — matches the prior YAML recipe's
# `timeout_seconds: 300`. Kept as a module constant (rather than a literal
# at the call site) so future adjustments have a single home.
_RETRIEVE_TIMEOUT_SECONDS = 300

# stderr patterns that mean "the CLI ran but there is no authenticated org
# for this alias" — reraised as AuthRequired. Mirrors the prior recipe's
# `auth_required_stderr_patterns` field.
_RETRIEVE_AUTH_PATTERNS = ("NoOrgAuthenticationError", "AuthInfoError")


def _run_retrieve(argv: List[str], timeout: int) -> "subprocess.CompletedProcess[str]":
    """Thin wrapper over `subprocess.run` for the retrieve-start call.

    Exists so tests can mock the subprocess boundary without also mocking
    the argv-construction logic — see `RetrievePromptTemplatesTests`.
    """
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def retrieve_prompt_templates(
    org_alias: str,
    template_names: List[str],
    work_dir: Path,
) -> Dict[str, Dict[str, Any]]:
    """Retrieve GenAiPromptTemplate bodies via `sf project retrieve start`.

    The sf plugin's `--metadata` flag is REPEATED once per requested
    template (`--metadata GenAiPromptTemplate:A --metadata
    GenAiPromptTemplate:B ...`). A comma-joined value is NOT a valid list;
    the CLI treats the whole comma-joined string as a single malformed
    member name, silently skips it, and the resulting zip contains only
    `package.xml` (observed 2026-05-05 against my-org-alias). Hence we
    bypass the YAML recipe loader here — `run_sf` substitutes
    `{{METADATA_SPEC}}` single-shot and has no list-expansion primitive.

    The resulting `unpackaged.zip` carries one `.genAiPromptTemplate` XML
    file per template under `unpackaged/genAiPromptTemplates/`.

    Returns a dict keyed by `developerName`. Templates the retrieve
    didn't produce a file for are OMITTED (caller handles missing by
    leaving them in `_pending_fetches`).

    Failure modes:
      - Empty `template_names` → short-circuits with `{}` and no sf call.
      - `AuthRequired` (stderr matches auth patterns) → re-raised.
      - `SfCliError` (any other non-zero exit, timeout, etc) → swallowed;
        returns `{}`. Caller logs the retrieval-failure reason at the
        call site.
      - Zip missing or malformed → returns `{}`.
      - XML parse failure on a specific file → that file is skipped; the
        other templates in the same zip still parse and return.
    """
    if not template_names:
        return {}

    retrieve_dir = work_dir / "prompt_template_retrieve"
    retrieve_dir.mkdir(parents=True, exist_ok=True)
    # Nuke stale files from a prior invocation so we don't trust an old
    # unpackaged.zip if this run's sf call fails before writing one.
    for path in retrieve_dir.iterdir():
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            _rm_tree(path)

    argv: List[str] = [
        "sf",
        "project",
        "retrieve",
        "start",
        "--target-org",
        org_alias,
        "--target-metadata-dir",
        str(retrieve_dir),
        "--json",
    ]
    for name in template_names:
        argv.extend(["--metadata", f"GenAiPromptTemplate:{name}"])

    try:
        cp = _run_retrieve(argv, _RETRIEVE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as e:
        # timeout exceptions may carry stderr; route through
        # redact_error before surfacing — then swallow as non-fatal, same
        # contract the old run_sf-based path had for SfCliError.
        _ = redact_error(e)
        return {}
    except (OSError, subprocess.SubprocessError) as e:
        _ = redact_error(e)
        return {}

    if cp.returncode != 0:
        # Classify: auth failure re-raises, everything else is non-fatal.
        if _stderr_matches_auth(cp.stderr, _RETRIEVE_AUTH_PATTERNS):
            safe_stderr = _redact_subprocess_stderr(cp.stderr)
            raise AuthRequired(safe_stderr or "auth required")
        return {}

    zip_path = retrieve_dir / "unpackaged.zip"
    if not zip_path.exists():
        return {}

    results: Dict[str, Dict[str, Any]] = {}
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                name = info.filename
                if not name.endswith(".genAiPromptTemplate"):
                    continue
                if "genAiPromptTemplates/" not in name:
                    continue
                try:
                    xml_bytes = zf.read(info)
                except (KeyError, zipfile.BadZipFile):
                    continue
                body = _parse_prompt_template_xml(xml_bytes)
                if not body:
                    continue
                dev_name = body.get("developerName")
                if not dev_name:
                    # Fall back to the file stem if the XML somehow lacks
                    # a <developerName> element — keeps the caller's
                    # lookup working.
                    stem = Path(name).stem
                    if stem:
                        body["developerName"] = stem
                        dev_name = stem
                if dev_name:
                    results[dev_name] = body
    except zipfile.BadZipFile:
        return {}

    return results


def _rm_tree(path: Path) -> None:
    """Recursively delete a directory tree. stdlib-only, no shutil import
    at module top to keep the import surface minimal."""
    for child in path.iterdir():
        if child.is_dir():
            _rm_tree(child)
        else:
            child.unlink()
    path.rmdir()
