#!/usr/bin/env python3
"""Generate and score the deterministic Salesforce plugin-discovery catalog.

The checked catalog (``catalog/plugins.json``) is generated from a
single source: the repo-root marketplace (``.claude-plugin/marketplace.json``,
hashed for provenance). Claude Code's real marketplace schema already carries
everything the matcher needs natively — a plugin entry's ``description``,
``keywords`` (the discovery-tags array), a free-form ``metadata`` object (which
Claude Code itself never reads, so it is the correct home for our
``metadata.match.examplePrompts``), and a ``source`` that is either a
relative-path string (a local plugin in this repo) or a source object
(``github``/``url``/``git-subdir``/``npm``/``archive``/``command`` for a plugin
hosted elsewhere).

Opt-in rule (uniform for every entry, local or external): an entry is a
suggestion candidate **iff** it declares a non-empty ``keywords`` array AND is
not held via ``internalPlugins`` in the repo-root ``config.yml``. An opted-in
entry must also carry ``metadata.match.examplePrompts``; keywords without
example prompts is a data error the generator raises on (fail fast). "Local vs
external" is no longer stored — it is trivially derivable from whether ``source``
is a string vs. an object.

Because Claude Code copies only a plugin's own directory into the local plugin
cache at install time (never the sibling ``.claude-plugin/marketplace.json`` two
levels up), the runtime (``load_catalog``) can never read the marketplace live.
``build_catalog``/``generate``/``check`` run at build/CI/dev time — where the
full monorepo checkout is available — and emit this static snapshot, which ships
bundled inside the plugin; ``load_catalog`` at runtime just reads that snapshot.

``score_prompt_against_catalog`` is a separate, pure matching function: a
BM25-lite scorer over each plugin's ``match`` text, followed by a
near-duplicate collapse so two candidates suppress each other only when they
are both close in score AND matched on substantially the same evidence. It
returns every distinct plugin that clears the floor — never a single winner.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import NamedTuple, Optional

try:
    import capability_registry as registry
except ImportError:
    module_path = Path(__file__).resolve().parent / "capability_registry.py"
    spec = importlib.util.spec_from_file_location("plugin_catalog_capability_registry", module_path)
    if spec is None or spec.loader is None:
        raise
    registry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry)

SCHEMA_VERSION = "1.0"
ARTIFACT_RELATIVE = Path("catalog/plugins.json")
MARKETPLACE_RELATIVE = Path(".claude-plugin/marketplace.json")
PluginCatalogError = registry.RegistryError


def read_internal_plugin_holds(path: Path) -> set[str]:
    """Parse the repo's intentionally small ``internalPlugins`` YAML list without PyYAML."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PluginCatalogError(f"{path}: cannot read internal plugin holds: {exc}") from exc
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("internalPlugins:"):
            continue
        value = stripped.split(":", 1)[1].strip()
        if value:
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError) as exc:
                raise PluginCatalogError(f"{path}: unsupported inline internalPlugins list") from exc
            if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                raise PluginCatalogError(f"{path}: internalPlugins must be a string list")
            held = set(parsed)
        else:
            held = set()
            for child in lines[index + 1:]:
                if child and not child[0].isspace():
                    break
                match = re.match(r"^\s+-\s+(['\"]?)([a-z0-9-]+)\1\s*$", child)
                if child.strip() and not match:
                    raise PluginCatalogError(f"{path}: unsupported internalPlugins list entry")
                if match:
                    held.add(match.group(2))
        if any(not registry.NAME_PATTERN.fullmatch(name) for name in held):
            raise PluginCatalogError(f"{path}: invalid internalPlugins plugin name")
        return held
    raise PluginCatalogError(f"{path}: missing internalPlugins list")


def _has_control(value: str) -> bool:
    return any(unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in value)


def _load_marketplace(repo_root: Path) -> tuple[bytes, dict, list[dict]]:
    """Read+parse the repo-root marketplace, returning its raw bytes (for the
    provenance hash), the parsed object, and its validated plugin-entry list."""
    marketplace_path = repo_root / MARKETPLACE_RELATIVE
    marketplace_bytes = registry.read_regular_file_bytes(marketplace_path, max_bytes=1024 * 1024)
    try:
        marketplace_data = json.loads(marketplace_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PluginCatalogError(f"{marketplace_path}: cannot load marketplace manifest: {exc}") from exc
    if (type(marketplace_data) is not dict or type(marketplace_data.get("name")) is not str
            or type(marketplace_data.get("plugins")) is not list):
        raise PluginCatalogError(f"{marketplace_path}: invalid marketplace manifest")
    entries: list[dict] = []
    for entry in marketplace_data["plugins"]:
        if type(entry) is not dict or type(entry.get("name")) is not str:
            raise PluginCatalogError(f"{marketplace_path}: invalid marketplace plugin entry")
        entries.append(entry)
    return marketplace_bytes, marketplace_data, entries


def _is_suggestion_candidate(entry: dict, held: set[str]) -> bool:
    """Opt-in signal: a plugin is a discovery candidate iff it declares a
    non-empty ``keywords`` array and is not held via ``internalPlugins``."""
    if entry["name"] in held:
        return False
    keywords = entry.get("keywords")
    return isinstance(keywords, list) and len(keywords) > 0


def build_catalog(repo_root: Path, plugin_root: Path) -> dict:
    """Build the plugin-discovery catalog from the repo-root marketplace.

    Every plugin entry that opts in (non-empty ``keywords`` and not held) is
    emitted as a flattened row carrying its verbatim ``source`` and the match
    text native to the marketplace. An opted-in entry that omits
    ``metadata.match.examplePrompts`` is a data error (fail fast). ``plugin_root``
    is retained for signature symmetry with the rest of the module."""
    marketplace_path = repo_root / MARKETPLACE_RELATIVE
    marketplace_bytes, _, entries = _load_marketplace(repo_root)
    held = read_internal_plugin_holds(repo_root / "config.yml")

    plugins: list[dict] = []
    for entry in entries:
        if not _is_suggestion_candidate(entry, held):
            continue
        name = entry["name"]
        description = entry.get("description")
        if type(description) is not str or not description:
            raise PluginCatalogError(f"{marketplace_path}: {name!r} is missing a marketplace description")
        source = entry.get("source")
        if not ((type(source) is str and source) or (type(source) is dict and source)):
            raise PluginCatalogError(f"{marketplace_path}: {name!r} has an invalid marketplace source")
        keywords = entry["keywords"]
        if not all(type(item) is str and item for item in keywords):
            raise PluginCatalogError(f"{marketplace_path}: {name!r} has invalid keywords")
        metadata = entry.get("metadata")
        match_meta = metadata.get("match") if isinstance(metadata, dict) else None
        example_prompts = match_meta.get("examplePrompts") if isinstance(match_meta, dict) else None
        if not (isinstance(example_prompts, list) and example_prompts
                and all(type(item) is str and item for item in example_prompts)):
            raise PluginCatalogError(
                f"{marketplace_path}: {name!r} opts in via keywords but is missing "
                f"metadata.match.examplePrompts"
            )
        anchor_terms = match_meta.get("anchorTerms") if isinstance(match_meta, dict) else None
        if anchor_terms is not None and not (
            isinstance(anchor_terms, list) and anchor_terms
            and all(type(item) is str and item for item in anchor_terms)
        ):
            raise PluginCatalogError(f"{marketplace_path}: {name!r} has invalid metadata.match.anchorTerms")
        anchor_companions = match_meta.get("anchorCompanions") if isinstance(match_meta, dict) else None
        if anchor_companions is not None and not (
            isinstance(anchor_companions, dict) and anchor_companions
            and all(
                type(key) is str and key in (anchor_terms or [])
                and isinstance(value, list) and value
                and all(type(item) is str and item for item in value)
                for key, value in anchor_companions.items()
            )
        ):
            raise PluginCatalogError(f"{marketplace_path}: {name!r} has invalid metadata.match.anchorCompanions")
        entry_command = match_meta.get("entryCommand") if isinstance(match_meta, dict) else None
        if entry_command is not None and not (type(entry_command) is str and entry_command):
            raise PluginCatalogError(f"{marketplace_path}: {name!r} has invalid metadata.match.entryCommand")
        match = {
            "description": description,
            "keywords": list(keywords),
            "examplePrompts": list(example_prompts),
        }
        if anchor_terms:
            match["anchorTerms"] = list(anchor_terms)
        if anchor_companions:
            match["anchorCompanions"] = {key: list(value) for key, value in anchor_companions.items()}
        if entry_command:
            match["entryCommand"] = entry_command
        plugins.append({
            "name": name,
            "source": copy.deepcopy(source),
            "match": match,
        })

    plugins.sort(key=lambda item: item["name"])
    names = [item["name"] for item in plugins]
    if len(names) != len(set(names)):
        raise PluginCatalogError("plugin catalog has duplicate plugin names")

    data = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedFrom": {
            "marketplace": MARKETPLACE_RELATIVE.as_posix(),
            "marketplaceSha256": hashlib.sha256(marketplace_bytes).hexdigest(),
        },
        "plugins": plugins,
    }
    _validate_catalog(data, "generated plugin catalog")
    return data


def held_plugin_descriptions(repo_root: Path, plugin_root: Path) -> dict[str, str]:
    """Match-text of every plugin currently held via ``internalPlugins`` -- the
    release leak-scanner's protected set, mirroring the skill-level
    protected-description scan in ``verify-public-plugin-release.py``. Reads the
    same single source ``build_catalog`` does, but for held names instead of
    visible ones, so the held-vs-visible boundary can never diverge between
    generation and the gate. ``plugin_root`` is retained for signature symmetry."""
    held = read_internal_plugin_holds(repo_root / "config.yml")
    if not held:
        return {}
    _, _, entries = _load_marketplace(repo_root)
    descriptions: dict[str, str] = {}
    for entry in entries:
        if entry.get("name") in held:
            description = entry.get("description")
            if isinstance(description, str) and description:
                descriptions[entry["name"]] = description
    return descriptions


def _serialized(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def generate(repo_root: Path, plugin_root: Path, artifact: Optional[Path] = None) -> Path:
    destination = artifact or plugin_root / ARTIFACT_RELATIVE
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        _serialized(build_catalog(repo_root, plugin_root)),
        encoding="utf-8",
        newline="\n",
    )
    return destination


def check(repo_root: Path, plugin_root: Path, artifact: Optional[Path] = None) -> bool:
    destination = artifact or plugin_root / ARTIFACT_RELATIVE
    try:
        actual = registry.read_regular_file_bytes(destination, max_bytes=16 * 1024 * 1024).decode("utf-8")
    except (OSError, UnicodeError, PluginCatalogError) as exc:
        raise PluginCatalogError(f"{destination}: plugin catalog artifact is missing: {exc}") from exc
    if actual != _serialized(build_catalog(repo_root, plugin_root)):
        raise PluginCatalogError(f"{destination}: plugin catalog artifact is stale; run plugin_catalog.py --generate")
    return True


_TOP_KEYS = {"schemaVersion", "generatedFrom", "plugins"}
_GENERATED_FROM_KEYS = {"marketplace", "marketplaceSha256"}
_PLUGIN_KEYS = {"name", "source", "match"}
_MATCH_REQUIRED_KEYS = {"description", "keywords", "examplePrompts"}
_MATCH_OPTIONAL_KEYS = {"anchorTerms", "anchorCompanions", "entryCommand"}
_MATCH_KEYS = _MATCH_REQUIRED_KEYS | _MATCH_OPTIONAL_KEYS


def _validate_catalog(data, context: str) -> None:
    if type(data) is not dict or set(data) != _TOP_KEYS:
        raise PluginCatalogError(f"{context}: invalid top-level plugin catalog keys")
    if data["schemaVersion"] != SCHEMA_VERSION:
        raise PluginCatalogError(f"{context}: unsupported plugin catalog schema version")
    generated_from = data["generatedFrom"]
    if (type(generated_from) is not dict or set(generated_from) != _GENERATED_FROM_KEYS
            or generated_from["marketplace"] != MARKETPLACE_RELATIVE.as_posix()
            or not registry._valid_hash(generated_from["marketplaceSha256"])):
        raise PluginCatalogError(f"{context}: invalid generatedFrom provenance")
    if type(data["plugins"]) is not list:
        raise PluginCatalogError(f"{context}: plugins must be an array")
    names: list[str] = []
    for index, row in enumerate(data["plugins"]):
        row_context = f"{context}: plugin row {index}"
        if type(row) is not dict or set(row) != _PLUGIN_KEYS:
            raise PluginCatalogError(f"{row_context}: invalid keys")
        name = row["name"]
        if type(name) is not str or not registry.NAME_PATTERN.fullmatch(name) or len(name) > 64:
            raise PluginCatalogError(f"{row_context}: invalid name")
        source = row["source"]
        # A local plugin's source is a relative-path string; an externally hosted
        # plugin's is a non-empty source object (github/url/npm/archive/...). We
        # keep it verbatim and only check it is one of those two shapes; whether
        # a source is trusted (local) is derived from `isinstance(source, str)`.
        if not ((type(source) is str and source) or (type(source) is dict and source)):
            raise PluginCatalogError(f"{row_context}: invalid source")
        match = row["match"]
        if type(match) is not dict or not (_MATCH_REQUIRED_KEYS <= set(match) <= _MATCH_KEYS):
            raise PluginCatalogError(f"{row_context}: invalid match keys")
        description = match["description"]
        if type(description) is not str or not 1 <= len(description) <= 1024 or _has_control(description):
            raise PluginCatalogError(f"{row_context}: invalid match description")
        keywords = match["keywords"]
        if (type(keywords) is not list or not keywords
                or not all(type(item) is str and item for item in keywords)
                or len(keywords) != len(set(keywords))):
            raise PluginCatalogError(f"{row_context}: invalid match keywords")
        prompts = match["examplePrompts"]
        if (type(prompts) is not list or not prompts
                or not all(type(item) is str and 1 <= len(item) <= 140 and not _has_control(item) for item in prompts)):
            raise PluginCatalogError(f"{row_context}: invalid match examplePrompts")
        if "anchorTerms" in match:
            anchor_terms = match["anchorTerms"]
            if (type(anchor_terms) is not list or not anchor_terms
                    or not all(type(item) is str and _TOKEN_PATTERN.fullmatch(item) for item in anchor_terms)
                    or len(anchor_terms) != len(set(anchor_terms))):
                raise PluginCatalogError(f"{row_context}: invalid match anchorTerms")
        if "anchorCompanions" in match:
            companions = match["anchorCompanions"]
            anchors = set(match.get("anchorTerms", ()))
            if (type(companions) is not dict or not companions
                    or not all(
                        type(key) is str and key in anchors
                        and type(value) is list and value
                        and all(type(item) is str and _TOKEN_PATTERN.fullmatch(item) for item in value)
                        and len(value) == len(set(value))
                        for key, value in companions.items()
                    )):
                raise PluginCatalogError(f"{row_context}: invalid match anchorCompanions")
        if "entryCommand" in match:
            entry_command = match["entryCommand"]
            if type(entry_command) is not str or len(entry_command) > 64 or not _ENTRY_COMMAND_PATTERN.fullmatch(entry_command):
                raise PluginCatalogError(f"{row_context}: invalid match entryCommand")
        names.append(name)
    if names != sorted(names) or len(names) != len(set(names)):
        raise PluginCatalogError(f"{context}: plugin names must be unique and sorted")


def load_catalog(plugin_root: Path) -> dict:
    path = plugin_root / ARTIFACT_RELATIVE
    try:
        data = json.loads(
            registry.read_regular_file_bytes(path, max_bytes=16 * 1024 * 1024).decode("utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError, PluginCatalogError) as exc:
        raise PluginCatalogError(f"{path}: cannot load plugin catalog: {exc}") from exc
    _validate_catalog(data, str(path))
    return data


# ── Phase 2: pure prompt-vs-catalog matching (BM25-lite + dedup gate) ──
#
# score_prompt_against_catalog is a pure function: no I/O, no emit, no marker
# access. It scores every plugin in the catalog independently and returns
# every distinct candidate that clears MIN_SCORE_THRESHOLD — never a single
# winner (Change 1). BM25 scores are unbounded, so the thresholds below are a
# deliberately conservative starting point, not a calibrated probability; they
# are the single seam to retune once real prompts are observed.
BM25_K1 = 1.5
BM25_B = 0.75
MIN_SCORE_THRESHOLD = 1.0
HIGH_CONFIDENCE_THRESHOLD = 3.5
DEDUP_SCORE_MARGIN = 1.0
DEDUP_OVERLAP_THRESHOLD = 0.6
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
# A plugin's own entry command (e.g. `/salesforce-test-drive:start`) -- the
# single slash command a returning user runs when the plugin is already
# installed. Curated first-party data, so a malformed value fails the build.
_ENTRY_COMMAND_PATTERN = re.compile(r"/[a-z0-9]+(?:-[a-z0-9]+)*(?::[a-z0-9]+(?:-[a-z0-9]+)*)?")
# Common request scaffolding is not product evidence. Leaving these terms in
# the BM25 query lets short follow-ups such as "add a field to it" accumulate a
# high score from words repeated in a marketplace description even though the
# prompt names no React, LWC, CMS, or Agentforce concept. Remove the same terms
# from queries and plugin documents so scores remain symmetric and are driven
# by substantive capability vocabulary.
_GENERIC_MATCH_TERMS = frozenset({
    "a", "add", "an", "and", "app", "are", "as", "at", "be", "build", "by", "can",
    "create", "do", "edit", "find", "for", "from", "generate", "have", "i",
    "in", "is", "it", "make", "me", "my", "need", "of", "on", "or", "please",
    "salesforce", "search", "that", "the", "this", "to", "use", "want", "we",
    "with", "you", "your",
})


class Match(NamedTuple):
    plugin: dict
    score: float
    band: str
    matched_terms: frozenset


def _tokenize(text: str) -> list[str]:
    return [
        token for token in _TOKEN_PATTERN.findall(text.lower())
        if len(token) > 1 and token not in _GENERIC_MATCH_TERMS
    ]


def _plugin_document_tokens(plugin: dict) -> list[str]:
    match = plugin["match"]
    text = " ".join([match["description"], *match["keywords"], *match["examplePrompts"]])
    return _tokenize(text)


def _bm25_score(
    query_terms: set,
    doc_tokens: list[str],
    doc_freq: dict,
    avg_doc_len: float,
    total_docs: int,
) -> tuple:
    doc_len = len(doc_tokens)
    if doc_len == 0 or not query_terms:
        return 0.0, frozenset()
    term_counts = Counter(doc_tokens)
    score = 0.0
    matched = set()
    for term in query_terms:
        freq = term_counts.get(term, 0)
        if freq == 0:
            continue
        doc_count = doc_freq.get(term, 0)
        idf = math.log((total_docs - doc_count + 0.5) / (doc_count + 0.5) + 1.0)
        denominator = freq + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / avg_doc_len)
        term_score = idf * (freq * (BM25_K1 + 1)) / denominator
        if term_score > 0:
            score += term_score
            matched.add(term)
    return score, frozenset(matched)


def _jaccard(left: frozenset, right: frozenset) -> float:
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _collapse_near_duplicates(candidates: list, *, margin: float, overlap_threshold: float) -> list:
    """Collapse a candidate into an already-kept one only when both the scores
    are within `margin` AND the matched-term sets overlap beyond
    `overlap_threshold`. Score proximity alone never suppresses a distinct
    plugin — evidence overlap must agree too."""
    kept: list = []
    for candidate in candidates:
        if any(
            abs(existing.score - candidate.score) <= margin
            and _jaccard(existing.matched_terms, candidate.matched_terms) >= overlap_threshold
            for existing in kept
        ):
            continue
        kept.append(candidate)
    return kept


def score_prompt_against_catalog(
    prompt: str,
    catalog_data: dict,
    *,
    high_confidence_threshold: Optional[float] = None,
    require_anchor_terms: bool = True,
) -> list:
    """Score `prompt` against every plugin in `catalog_data`, ranked descending.

    Returns a ranked list of Match, empty when nothing clears the threshold.
    Pure function: no I/O, no emit, no marker access.

    `high_confidence_threshold` overrides the module's HIGH_CONFIDENCE_THRESHOLD
    for the high/medium band split (the caller's resolved sensitivity setting);
    None uses the module default. It never affects MIN_SCORE_THRESHOLD -- a
    candidate that doesn't clear the floor never appears at all, regardless of
    sensitivity.

    `require_anchor_terms` (default True) gates a candidate that declares
    `anchorTerms` on having at least one of them among the prompt's matched
    terms. Callers on a high-confidence-only proactive surface (SessionStart,
    UserPromptSubmit) should leave this True; callers on a surface where the
    user's own act of invoking it is the evidence (explicit discovery, the
    reactive bypass gate) should pass False to restore plain high+medium
    recall for plugins whose anchor set doesn't cover every legitimate phrase.
    """
    threshold = HIGH_CONFIDENCE_THRESHOLD if high_confidence_threshold is None else high_confidence_threshold
    plugins = catalog_data["plugins"]
    query_terms = set(_tokenize(prompt))
    if not query_terms or not plugins:
        return []
    doc_tokens_by_name = {plugin["name"]: _plugin_document_tokens(plugin) for plugin in plugins}
    total_docs = len(plugins)
    total_len = sum(len(tokens) for tokens in doc_tokens_by_name.values())
    avg_doc_len = total_len / total_docs if total_docs else 0.0
    if avg_doc_len == 0:
        return []
    doc_freq: dict = {}
    for tokens in doc_tokens_by_name.values():
        for term in set(tokens):
            doc_freq[term] = doc_freq.get(term, 0) + 1
    candidates: list = []
    for plugin in plugins:
        score, matched_terms = _bm25_score(
            query_terms, doc_tokens_by_name[plugin["name"]], doc_freq, avg_doc_len, total_docs
        )
        if score < MIN_SCORE_THRESHOLD:
            continue
        # A plugin declaring anchorTerms only counts as matched when the prompt's
        # evidence includes at least one of its own anchor terms -- a generic
        # word shared with the rest of the corpus can never carry the match alone.
        # An anchor term may itself be a common English word (e.g. test-drive's
        # "drive", a verb in "drive adoption/traffic/results"); such a term
        # declares `anchorCompanions` so it only anchors when a corroborating
        # companion is also present in the prompt -- proxying the "test drive"
        # phrase via the token "test" rather than firing on bare "drive". Callers
        # that already require explicit user intent to reach the scorer
        # (require_anchor_terms=False) skip this gate; it exists to stop a
        # generic-word coincidence from *interrupting* the user unprompted.
        anchor_terms = plugin["match"].get("anchorTerms")
        if require_anchor_terms and anchor_terms:
            companions = plugin["match"].get("anchorCompanions") or {}
            anchor_hits = {
                term for term in matched_terms.intersection(anchor_terms)
                if not companions.get(term) or not query_terms.isdisjoint(companions[term])
            }
            if not anchor_hits:
                continue
        band = "high" if score >= threshold else "medium"
        candidates.append(Match(plugin=plugin, score=score, band=band, matched_terms=matched_terms))
    candidates.sort(key=lambda item: item.score, reverse=True)
    return _collapse_near_duplicates(candidates, margin=DEDUP_SCORE_MARGIN, overlap_threshold=DEDUP_OVERLAP_THRESHOLD)


def _repo_root(plugin_root: Path) -> Path:
    candidate = plugin_root.resolve()
    while candidate != candidate.parent:
        if (candidate / "config.yml").is_file() and (candidate / "skills").is_dir():
            return candidate
        candidate = candidate.parent
    raise PluginCatalogError("internal checkout is unavailable")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--generate", action="store_true")
    modes.add_argument("--check", action="store_true")
    options = parser.parse_args(argv)
    plugin_root = Path(__file__).resolve().parent.parent
    try:
        repo_root = _repo_root(plugin_root)
        if options.generate:
            path = generate(repo_root, plugin_root)
            print(f"generated {path.relative_to(repo_root)}")
        else:
            check(repo_root, plugin_root)
            print(f"plugin catalog is current: {(plugin_root / ARTIFACT_RELATIVE).relative_to(repo_root)}")
    except PluginCatalogError as exc:
        print(f"plugin catalog error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
