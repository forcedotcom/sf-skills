#!/usr/bin/env python3
"""Parse PUBLIC scratch-org config-values into features.json + settings-map.json.

Runtime (customer) path: lib_scratch_def.load_runtime_catalog fetches, parses
into in-memory maps, and never writes the skill directory. This module's
--seed / --out / --merge CLIs are test-only for fixture files in temp dirs.

--seed reads an offline markdown feed. --fetch downloads the PUBLIC docs
markdown page, converts it to the enricher feed, then merges into existing
JSON in --out. A thin live parse refuses to write. Broken inline JSON
examples are skipped as one count warning (not a hard fail).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

SOURCE_MD_URL = (
    "https://developer.salesforce.com/docs/platform/sfdx-dev/guide/"
    "sfdx-dev-scratch-orgs-def-file-config-values.md"
)

# Title-case product phrases in PUBLIC blurbs ("Revenue Cloud", "Experience Cloud").
_TITLE_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
_FEATURE_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_SETTING_PATH_RE = re.compile(
    r"^[A-Za-z][A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z][A-Za-z0-9]*)*$"
)

BULLET_FEATURE_RE = re.compile(
    r"^\*\s+\*\*(?P<name>[A-Za-z][A-Za-z0-9_]*)(?::\s*(?:&lt;value&gt;|<value>| &lt;value&gt;))?\*\*"
)
QUANTITY_RANGE_RE = re.compile(
    r"(?:Indicate a value (?:from|between)|Supported Quantities)\s*"
    r"(?P<a>[\d,]+)\s*[–\-]\s*(?P<b>[\d,]+)",
    re.IGNORECASE,
)
MULTIPLIER_RE = re.compile(r"[Mm]ultiplier(?:\s+is)?[:\s]+(?P<m>\d+)")
EDITION_RE = re.compile(
    r"(?:Available|Not available) in[^.]*Edition[^.]*\.",
    re.IGNORECASE,
)
# "must also include communitiesSettings > enableNetworksEnabled"
REQUIRED_SETTING_RE = re.compile(
    r"must also include\s+([A-Za-z][A-Za-z0-9_]*)\s*>\s*([A-Za-z][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
# "must also include the CustomerDataPlatform feature"
REQUIRED_FEATURE_RE = re.compile(
    r"must also include the\s+([A-Za-z][A-Za-z0-9_]*)\s+feature",
    re.IGNORECASE,
)
# PUBLIC markdown uses ```nolang (and rarely ```json) for scratch-def examples.
JSON_FENCE_RE = re.compile(
    r"```(?:json|nolang)\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)
# Live docs put each feature under ## Name (### in HTML-converted feeds).
_FEATURE_HEADING_RE = re.compile(
    r"^#{2,3}\s+"
    r"(?P<name>[A-Za-z][A-Za-z0-9_]*)"
    r"(?P<q>"
    r"\\:VALUE"
    r"|:VALUE"
    r"|:\s*VALUE"
    r"|:\s*(?:&lt;value&gt;|<value>)"
    r")?"
    r"\s*$"
)

# Public docs markdown: - **[Name](#anchor)** / - **[Name\:VALUE](#anchor)**
_DOCS_FEATURE_BULLET_RE = re.compile(
    r"^-\s+\*\*\["
    r"(?P<name>[A-Za-z][A-Za-z0-9_]*)"
    r"(?:\s*\([^)]*\))?"
    r"(?P<q>\\:VALUE|:VALUE|: VALUE)?"
    r"\]\([^)]*\)\*\*\s*$",
    re.MULTILINE,
)
THIN_ABS_COUNT = 250
THIN_RATIO = 0.9


def _clean_name(raw: str) -> tuple[str, bool]:
    """Return (canonical_name, quantified). Strip :<value> suffix."""
    name = html.unescape(raw.strip())
    quantified = False
    if ":" in name:
        base, _, _rest = name.partition(":")
        quantified = True
        name = base.strip()
    return name, quantified


def camel_words(name: str) -> str:
    """CoreCpq → 'core cpq'; B2BCommerce → 'b2b commerce'."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    return " ".join(spaced.lower().split())


def title_phrases(description: str) -> list[str]:
    """Product phrases copied from PUBLIC prose, not a hand token list."""
    return [m.group(0).lower() for m in _TITLE_PHRASE_RE.finditer(description or "")]


def derived_synonyms(name: str, description: str) -> list[str]:
    """Catalog-derived lookup phrases. Grows/shrinks with whatever PUBLIC lists."""
    syn: list[str] = []
    seen = {name.lower()}

    def add(raw: str) -> None:
        phrase = " ".join(raw.lower().split())
        if len(phrase) < 4 or phrase in seen:
            return
        seen.add(phrase)
        syn.append(phrase)

    add(camel_words(name))
    add(name.replace("_", " "))
    for phrase in title_phrases(description):
        add(phrase)
    return syn


def _phrases_for_entry(name: str, entry: dict[str, Any]) -> list[str]:
    phrases = [name, camel_words(name)]
    phrases.extend(entry.get("synonyms") or [])
    phrases.extend(title_phrases(str(entry.get("description") or "")))
    out: list[str] = []
    seen: set[str] = set()
    for raw in phrases:
        phrase = " ".join(str(raw).lower().split())
        if len(phrase) < 4 or phrase in seen:
            continue
        seen.add(phrase)
        out.append(phrase)
    return out


def phrase_match_features(raw: str, features_doc: dict) -> list[str]:
    """Feature names tied at the longest matching phrase length (sorted).

    Exact catalog name / listed synonym resolve earlier in map_feature_token.
    This only covers description-derived Title-Case phrases. A length tie must
    not silently pick the first dict insertion — callers drop + warn.
    """
    hay = " ".join((raw or "").lower().split())
    if len(hay) < 4:
        return []
    best_len = 0
    winners: set[str] = set()
    for name, entry in (features_doc.get("features") or {}).items():
        if not isinstance(entry, dict):
            continue
        for phrase in _phrases_for_entry(name, entry):
            if phrase == hay or phrase in hay:
                if len(phrase) > best_len:
                    best_len = len(phrase)
                    winners = {name}
                elif len(phrase) == best_len:
                    winners.add(name)
    return sorted(winners)


def longest_phrase_match(raw: str, features_doc: dict) -> str | None:
    """Map a user phrase onto today's catalog (longest contained phrase wins).

    Returns None when no match or when multiple features tie at the best length.
    """
    winners = phrase_match_features(raw, features_doc)
    return winners[0] if len(winners) == 1 else None


def _parse_int(s: str) -> int:
    return int(s.replace(",", ""))


def _first_paragraph(block: str) -> str:
    lines = []
    for line in block.splitlines():
        s = line.strip()
        if not s:
            if lines:
                break
            continue
        if (
            s.startswith("###")
            or s.startswith("```")
            or s.startswith("* ")
            or s.startswith("- ")
        ):
            if lines:
                break
            continue
        # strip leading list markers from more-info bullets
        if s.startswith("* "):
            s = s[2:].strip()
        lines.append(s)
        if len(" ".join(lines)) > 400:
            break
    text = " ".join(lines)
    # keep a few sentences
    parts = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(parts[:3]).strip()


def _extract_quantity(block: str) -> dict[str, int] | None:
    m = QUANTITY_RANGE_RE.search(block)
    if not m:
        return None
    q = {"min": _parse_int(m.group("a")), "max": _parse_int(m.group("b")), "multiplier": 1}
    mm = MULTIPLIER_RE.search(block)
    if mm:
        q["multiplier"] = int(mm.group("m"))
    return q


def _extract_edition_notes(block: str) -> str | None:
    matches = EDITION_RE.findall(block)
    if not matches:
        return None
    return " ".join(m.strip() for m in matches)


def lower_camel_settings_key(key: str) -> str:
    """Scratch-def settings use lower camelCase; Metadata API uses UpperCamel.

    PUBLIC docs sometimes paste Metadata API names (IndustriesSettings). Force
    the category's first letter lower so emit matches create-time expectations.
    """
    if not key or not isinstance(key, str):
        return key
    if key[0].isupper():
        return key[0].lower() + key[1:]
    return key


def normalize_settings_path(path: str) -> str:
    """Lower-camel the settings *category* (first path segment) only."""
    if not path or "." not in path:
        return lower_camel_settings_key(path)
    cat, rest = path.split(".", 1)
    return f"{lower_camel_settings_key(cat)}.{rest}"


def _extract_required_from_prose(block: str) -> list[dict[str, Any]]:
    out = []
    for m in REQUIRED_SETTING_RE.finditer(block):
        category, field = m.group(1), m.group(2)
        path = normalize_settings_path(f"{category}.{field}")
        out.append(
            {
                "path": path,
                "type": "boolean",
                "example": True,
                "source": "public-docs prose",
            }
        )
    return out


def _extract_depends_on_features(block: str) -> list[str]:
    return [m.group(1) for m in REQUIRED_FEATURE_RE.finditer(block)]


def parse_markdown(text: str) -> tuple[dict[str, dict], dict[str, dict], list[str]]:
    """Return (features, by_feature_settings, warnings)."""
    warnings: list[str] = []
    features: dict[str, dict] = {}
    by_feature: dict[str, dict] = defaultdict(lambda: {"required": [], "common": []})

    # --- ## / ### feature sections (richer than the TOC bullets) ---
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        hm = _FEATURE_HEADING_RE.match(lines[i])
        if not hm or hm.group("name") in _CHROME_HEADINGS:
            i += 1
            continue
        name = hm.group("name")
        quantified = bool(hm.group("q"))

        # Keep ### More Information / Supported Quantities inside this feature.
        j = i + 1
        while j < len(lines) and not _FEATURE_HEADING_RE.match(lines[j]):
            j += 1
        block = "\n".join(lines[i + 1 : j])
        desc = _first_paragraph(block) or name
        quantity = _extract_quantity(block) if quantified else None
        edition = _extract_edition_notes(block)
        entry = {
            "name": name,
            "description": desc,
            "quantified": quantified,
            "editionNotes": edition,
            "synonyms": [],
            "settingsCoverage": "unknown",
            "exampleCount": 0,
        }
        deps = _extract_depends_on_features(block)
        if deps:
            entry["dependsOnFeatures"] = deps
        if quantity:
            entry["quantity"] = quantity
        # Prefer first/richer entry; merge if bullet already seeded a thinner one
        if name not in features or len(desc) > len(features[name].get("description", "")):
            prev = features.get(name, {})
            if prev.get("synonyms") and not entry["synonyms"]:
                entry["synonyms"] = prev["synonyms"]
            if prev.get("dependsOnFeatures") and not entry.get("dependsOnFeatures"):
                entry["dependsOnFeatures"] = prev["dependsOnFeatures"]
            if prev.get("editionNotes") and not entry.get("editionNotes"):
                entry["editionNotes"] = prev["editionNotes"]
            if prev.get("quantity") and "quantity" not in entry:
                entry["quantity"] = prev["quantity"]
            if prev.get("quantified"):
                entry["quantified"] = True
            features[name] = entry
        else:
            if deps and not features[name].get("dependsOnFeatures"):
                features[name]["dependsOnFeatures"] = deps
        if edition and not features[name].get("editionNotes"):
            features[name]["editionNotes"] = edition
        if quantity and "quantity" not in features[name]:
            features[name]["quantity"] = quantity
        if quantified:
            features[name]["quantified"] = True
        for req in _extract_required_from_prose(block):
            _add_setting(by_feature[name]["required"], req)
        i = j

    # --- bullet list fallback (fills gaps) ---
    for idx, line in enumerate(lines):
        bm = BULLET_FEATURE_RE.match(line)
        if not bm:
            continue
        raw = bm.group("name")
        quantified = "value" in line.lower()
        name = raw
        # gather following prose until blank or next bullet
        desc_lines = []
        k = idx + 1
        while k < len(lines):
            s = lines[k].strip()
            if not s or s.startswith("* **") or s.startswith("##") or s.startswith("```"):
                break
            desc_lines.append(s)
            k += 1
        desc = " ".join(desc_lines)[:500] or name
        quantity = _extract_quantity(desc) if quantified else None
        edition = _extract_edition_notes(desc)
        if name not in features:
            entry = {
                "name": name,
                "description": desc,
                "quantified": quantified,
                "editionNotes": edition,
                "synonyms": [],
                "settingsCoverage": "unknown",
                "exampleCount": 0,
            }
            if quantity:
                entry["quantity"] = quantity
            features[name] = entry
        else:
            if quantified and not features[name].get("quantified"):
                features[name]["quantified"] = True
            if quantity and "quantity" not in features[name]:
                features[name]["quantity"] = quantity
            if edition and not features[name].get("editionNotes"):
                features[name]["editionNotes"] = edition
            if len(desc) > len(features[name].get("description", "")):
                features[name]["description"] = desc
        for req in _extract_required_from_prose(desc):
            _add_setting(by_feature[name]["required"], req)

    # --- JSON examples ---
    broken_json = 0
    for fm in JSON_FENCE_RE.finditer(text):
        raw_json = fm.group(1).strip()
        # PUBLIC examples sometimes use curly quotes.
        cleaned = (
            raw_json.replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("“", '"')
            .replace("”", '"')
        )
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError:
            broken_json += 1
            continue
        if not isinstance(obj, dict):
            continue
        feat_list = obj.get("features") or []
        settings = obj.get("settings") or {}
        if not isinstance(feat_list, list):
            continue
        bases_in_example: list[str] = []
        for f in feat_list:
            if not isinstance(f, str):
                continue
            base = f.split(":", 1)[0]
            bases_in_example.append(base)
            if base in features:
                features[base]["exampleCount"] = features[base].get("exampleCount", 0) + 1
        # Fold settings only onto features that own the category — do not
        # attribute every settings path in a multi-feature example to every
        # feature (that bloated Communities.common with Revenue Cloud paths).
        if isinstance(settings, dict):
            for path, val in _flatten_settings(settings):
                owners = _settings_path_owners(path, bases_in_example, by_feature)
                if not owners and len(bases_in_example) == 1:
                    owners = [bases_in_example[0]]
                item = {
                    "path": path,
                    "type": _json_type(val),
                    "example": val,
                    "source": "public-docs example",
                }
                for base in owners:
                    req_paths = {r["path"] for r in by_feature[base]["required"]}
                    if path in req_paths:
                        continue
                    _add_setting(by_feature[base]["common"], item)

    if broken_json:
        warnings.append(f"skip broken JSON example: {broken_json}")

    # mark settingsCoverage
    for name, feat in features.items():
        if by_feature[name]["required"] or by_feature[name]["common"]:
            feat["settingsCoverage"] = "known"
        else:
            feat["settingsCoverage"] = "unknown"
        feat["synonyms"] = derived_synonyms(name, str(feat.get("description") or ""))

    # drop empty by_feature entries
    by_feature_out = {
        k: v for k, v in by_feature.items() if v["required"] or v["common"]
    }
    return features, by_feature_out, warnings


def _feature_setting_categories(entry: dict) -> set[str]:
    """Settings categories already attached to a feature (prose required + examples)."""
    cats: set[str] = set()
    for bucket in ("required", "common"):
        for item in entry.get(bucket) or []:
            path = item.get("path") if isinstance(item, dict) else None
            if not path:
                continue
            cats.add(normalize_settings_path(str(path)).split(".", 1)[0])
    return cats


def _settings_path_owners(
    path: str, bases_in_example: list[str], by_feature: dict
) -> list[str]:
    """Attribute a settings path using the catalog, not a frozen owner table.

    Prefer features in this example that already own the category via required
    prose. Else match category stem against feature names present in the example.
    """
    category = normalize_settings_path(path).split(".", 1)[0]
    owned = [
        b
        for b in bases_in_example
        if category in _feature_setting_categories(by_feature.get(b) or {})
    ]
    if owned:
        return owned
    cat_core = re.sub(r"Settings$", "", category, flags=re.IGNORECASE).lower()
    return [b for b in bases_in_example if cat_core and cat_core in b.lower()]


def _add_setting(bucket: list[dict], item: dict) -> None:
    item = dict(item)
    item["path"] = normalize_settings_path(str(item.get("path") or ""))
    if any(x["path"] == item["path"] for x in bucket):
        return
    bucket.append(item)


def _flatten_settings(obj: dict, prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    for k, v in obj.items():
        key = lower_camel_settings_key(k) if not prefix else k
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(v, dict):
            out.extend(_flatten_settings(v, path))
        else:
            out.append((normalize_settings_path(path) if not prefix else path, v))
    return out


def _json_type(v: Any) -> str:
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int) and not isinstance(v, bool):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return "string"


_CHROME_HEADINGS = frozenset({"Subject", "Description"})


def looks_like_docs_markdown(text: str) -> bool:
    return bool(_DOCS_FEATURE_BULLET_RE.search(text))


def docs_markdown_to_feed(text: str) -> str:
    """Turn PUBLIC docs markdown (- **[Name](#a)**) into the enricher bullet feed."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = _DOCS_FEATURE_BULLET_RE.match(lines[i].rstrip())
        if not m:
            out.append(lines[i])
            i += 1
            continue
        name = m.group("name")
        if name in _CHROME_HEADINGS:
            i += 1
            continue
        quantified = bool(m.group("q"))
        bullet = f"* **{name}:&lt;value&gt;**" if quantified else f"* **{name}**"
        out.append(bullet)
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        desc_parts: list[str] = []
        while i < len(lines):
            raw = lines[i]
            if _DOCS_FEATURE_BULLET_RE.match(raw.rstrip()) or raw.startswith("##"):
                break
            if not raw.strip():
                i += 1
                if i < len(lines) and _DOCS_FEATURE_BULLET_RE.match(lines[i].rstrip()):
                    break
                continue
            desc_parts.append(raw.strip())
            i += 1
        if desc_parts:
            out.append(" ".join(desc_parts))
        out.append("")
    return "\n".join(out)


def feed_from_text(text: str) -> str:
    """Normalize PUBLIC docs markdown into the enricher feed."""
    if looks_like_docs_markdown(text):
        return docs_markdown_to_feed(text)
    return text


def fetch_url(url: str) -> tuple[str, str]:
    """GET url; raise RuntimeError on network/HTTP failure (no bare traceback)."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "dx-scratch-def-configure-scraper/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            effective = resp.geturl() or url
    except Exception as e:  # noqa: BLE001 — surface as RuntimeError for callers
        raise RuntimeError(f"network fetch failed for {url}: {e}") from e
    return raw, effective


def fetch_live_feed() -> tuple[str, str]:
    """Fetch PUBLIC docs markdown only. Raises RuntimeError on failure."""
    try:
        raw, url = fetch_url(SOURCE_MD_URL)
    except Exception as e:  # noqa: BLE001 — surface as RuntimeError
        raise RuntimeError(f"PUBLIC catalog fetch failed (markdown: {e})") from e
    if not looks_like_docs_markdown(raw):
        raise RuntimeError(
            "PUBLIC catalog fetch failed (markdown URL did not look like the "
            "feature catalog)"
        )
    print(f"Fetched markdown catalog {url}", file=sys.stderr)
    return docs_markdown_to_feed(raw), url


def live_parse_too_thin(live_count: int, existing_count: int | None) -> bool:
    if live_count < THIN_ABS_COUNT:
        return True
    if existing_count is not None and live_count < existing_count * THIN_RATIO:
        return True
    return False


def _union_settings(a: list | None, b: list | None) -> list[dict]:
    out: list[dict] = []
    for item in list(a or []) + list(b or []):
        if not isinstance(item, dict) or not item.get("path"):
            continue
        _add_setting(out, item)
    return out


def _merge_feature_entry(existing: dict, live: dict) -> dict:
    out = dict(existing)
    live_desc = str(live.get("description") or "")
    exist_desc = str(existing.get("description") or "")
    if len(live_desc) > len(exist_desc):
        out["description"] = live_desc
    if live.get("quantified") or existing.get("quantified"):
        out["quantified"] = True
    if live.get("quantity") and not out.get("quantity"):
        out["quantity"] = live["quantity"]
    live_ed = live.get("editionNotes")
    exist_ed = out.get("editionNotes")
    if live_ed and (not exist_ed or len(str(live_ed)) > len(str(exist_ed))):
        out["editionNotes"] = live_ed
    syn: list[str] = []
    for s in list(existing.get("synonyms") or []) + list(live.get("synonyms") or []):
        if s not in syn:
            syn.append(s)
    out["synonyms"] = syn
    deps: list[str] = []
    for d in list(existing.get("dependsOnFeatures") or []) + list(
        live.get("dependsOnFeatures") or []
    ):
        if d not in deps:
            deps.append(d)
    if deps:
        out["dependsOnFeatures"] = deps
    out["exampleCount"] = max(
        int(existing.get("exampleCount") or 0), int(live.get("exampleCount") or 0)
    )
    return out


def merge_catalogs(
    existing_features: dict[str, dict],
    existing_by: dict[str, dict],
    live_features: dict[str, dict],
    live_by: dict[str, dict],
) -> tuple[dict[str, dict], dict[str, dict]]:
    merged_f: dict[str, dict] = {}
    for name in set(existing_features) | set(live_features):
        a = existing_features.get(name)
        b = live_features.get(name)
        if a and b:
            merged_f[name] = _merge_feature_entry(a, b)
        else:
            merged_f[name] = dict(a or b or {})
    merged_by: dict[str, dict] = {}
    for name in set(existing_by) | set(live_by):
        ea = existing_by.get(name) or {}
        lb = live_by.get(name) or {}
        entry = {
            "required": _union_settings(ea.get("required"), lb.get("required")),
            "common": _union_settings(ea.get("common"), lb.get("common")),
        }
        req_paths = {x["path"] for x in entry["required"]}
        entry["common"] = [c for c in entry["common"] if c.get("path") not in req_paths]
        if entry["required"] or entry["common"]:
            merged_by[name] = entry
    for name, feat in merged_f.items():
        if merged_by.get(name, {}).get("required") or merged_by.get(name, {}).get("common"):
            feat["settingsCoverage"] = "known"
        elif "settingsCoverage" not in feat:
            feat["settingsCoverage"] = "unknown"
    return merged_f, merged_by


def load_existing_catalog(out_dir: Path) -> tuple[dict[str, dict], dict[str, dict], int] | None:
    path = out_dir / "features.json"
    if not path.is_file():
        return None
    features_doc = json.loads(path.read_text(encoding="utf-8"))
    settings_path = out_dir / "settings-map.json"
    settings_doc = (
        json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
    )
    feats = features_doc.get("features") or {}
    by_feature = settings_doc.get("byFeature") or {}
    count = int(features_doc.get("featureCount") or len(feats))
    return feats, by_feature, count


def sanity_check(features: dict[str, dict], by_feature: dict[str, dict]) -> str | None:
    """Shape of the parse only — never pin today's PUBLIC token names."""
    if not features:
        return "parse produced no features"
    bad_names = [n for n in features if not _FEATURE_NAME_RE.match(n)]
    if bad_names:
        return f"illegal feature names: {bad_names[:5]}"
    for _feat, buckets in by_feature.items():
        for bucket in ("required", "common"):
            for item in buckets.get(bucket) or []:
                if not isinstance(item, dict):
                    return f"settings item is not an object under {_feat}"
                path = str(item.get("path") or "")
                if path and not _SETTING_PATH_RE.match(path):
                    return f"illegal settings path {path!r} under {_feat}"
    return None


def emit(
    features: dict[str, dict],
    by_feature: dict[str, dict],
    out_dir: Path,
    version: str,
    fetched_at: str | None = None,
    source_url: str | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = {
        "fetchedAt": fetched_at or date.today().isoformat(),
        "sourceUrl": source_url or SOURCE_MD_URL,
        "version": version,
    }
    features_doc = {
        **stamp,
        "featureCount": len(features),
        "features": dict(sorted(features.items(), key=lambda kv: kv[0].lower())),
    }
    settings_doc = {
        **stamp,
        "byFeature": dict(sorted(by_feature.items(), key=lambda kv: kv[0].lower())),
    }
    features_path = out_dir / "features.json"
    settings_path = out_dir / "settings-map.json"
    features_path.write_text(json.dumps(features_doc, indent=2) + "\n", encoding="utf-8")
    settings_path.write_text(json.dumps(settings_doc, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {features_path} ({features_doc['featureCount']} features)")
    print(f"Wrote {settings_path} ({len(settings_doc['byFeature'])} feature setting maps)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--seed",
        type=Path,
        default=None,
        help="Offline markdown feed of the PUBLIC config-values page (authoring)",
    )
    p.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch the live PUBLIC page, convert to a feed, enrich, merge into --out",
    )
    p.add_argument(
        "--merge",
        action="store_true",
        help="Merge this parse into existing JSON in --out (implied by --fetch)",
    )
    p.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Directory for features.json + settings-map.json",
    )
    p.add_argument(
        "--version",
        default=None,
        help="Stamp version (default: seed-YYYY-MM-DD or scrape-YYYY-MM-DD)",
    )
    args = p.parse_args(argv)

    today = date.today().isoformat()
    source_url = SOURCE_MD_URL
    do_merge = bool(args.fetch or args.merge)
    if args.fetch:
        print(f"Fetching {SOURCE_MD_URL} …", file=sys.stderr)
        try:
            text, source_url = fetch_live_feed()
        except Exception as e:  # noqa: BLE001 — keep shipped cache; exit non-zero
            print(f"Error: {e}", file=sys.stderr)
            print(
                "Keeping the current cache. Retry when the network is available.",
                file=sys.stderr,
            )
            return 1
        version = args.version or f"scrape-{today}"
    else:
        if args.seed is None:
            print(
                "Error: pass --seed <markdown-feed> or --fetch for a live scrape",
                file=sys.stderr,
            )
            return 2
        if not args.seed.is_file():
            print(f"Error: seed file not found: {args.seed}", file=sys.stderr)
            return 2
        text = feed_from_text(args.seed.read_text(encoding="utf-8"))
        version = args.version or f"seed-{today}"

    features, by_feature, warnings = parse_markdown(text)
    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)

    err = sanity_check(features, by_feature)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    existing = load_existing_catalog(args.out)
    live_count = len(features)
    if do_merge:
        existing_count = existing[2] if existing else None
        if live_parse_too_thin(live_count, existing_count):
            print(
                f"Error: live parse is too thin to merge "
                f"({live_count} features; existing={existing_count}). "
                "Keeping the current cache.",
                file=sys.stderr,
            )
            return 1
        if existing:
            features, by_feature = merge_catalogs(
                existing[0], existing[1], features, by_feature
            )
            print(
                f"Merged live parse ({live_count}) into existing cache "
                f"({existing[2]}) → {len(features)} features",
                file=sys.stderr,
            )
    elif args.fetch and live_parse_too_thin(live_count, None):
        print(
            f"Error: live scrape featureCount {live_count} looks low. Not writing.",
            file=sys.stderr,
        )
        return 1

    emit(
        features,
        by_feature,
        args.out,
        version=version,
        fetched_at=today,
        source_url=source_url,
    )
    print(f"OK: {len(features)} features, {len(by_feature)} settings maps, version={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
