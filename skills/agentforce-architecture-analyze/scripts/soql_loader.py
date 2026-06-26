"""SOQL template loader — reads assets/soql/*.soql and substitutes {{PARAM}} values.

every value passed in via **params is regex-revalidated at the
substitution boundary via `fs_guard.validate_api_name`. This is defence
in depth — callers (SKILL.md phase 1, parse_bundle.extract_planner_name,
parse_wave.discovered_names) already validate at their own boundaries, but
centralizing the gate here guarantees that any future caller can't bypass
it by forgetting to validate first.

Why no escape function: `validate_api_name` restricts every substituted
string to `^[A-Za-z0-9_]+$` — the legal character set for Salesforce
DeveloperName / API-name identifiers. No quote, apostrophe, semicolon,
parenthesis, or whitespace can ever reach the SOQL builder, so there is
nothing to escape. Adding an escape step would be both dead code and a
false reassurance that unvalidated input is somehow safe.

`load_soql_in` adds support for `WHERE X IN (...)`
list placeholders. The BFS fan-out passes across Apex/Flow/Plugin/Function
discovery each need to batch-query by a list of ids or names; forcing
one SOQL call per element would blow up both the query-count budget and
the request-latency floor. The new function shares the `load_soql`
validation path (every element goes through `fs_guard.validate_api_name`)
so list inputs cannot widen the SOQL-injection surface — `'`, `;`, `--`,
whitespace, and every other SOQL metachar remain unreachable. The
existing `load_soql` signature is unchanged.

SOQL-string-substitution loader with validation at the substitution
boundary. Every value substituted into a `{{token}}` placeholder is
regex-validated before insertion.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from config import SOQL_DIR, fs_guard  # fs_guard re-exported by config.py from _shared/


class SoqlParamError(ValueError):
    """Raised when a parameter value fails revalidation at the substitution site.

    Carries the failing key + a 20-char preview of the rejected value. Callers
    (parse_bundle, parse_wave, main.py) catch this and add the key to
    `_unresolved[]` with `reason=invalid-soql-param:<key>` so the pipeline
    continues with `STATUS=PARTIAL_OK` rather than aborting on a single
    malformed name.
    """

    def __init__(self, key: str, value, reason: str) -> None:
        self.key = key
        self.reason = reason
        # Preview is bounded to 20 chars to avoid echoing arbitrarily-long
        # attacker-controlled strings into logs.
        try:
            preview = str(value)[:20]
        except Exception:
            preview = "<unreprable>"
        self.preview = preview
        super().__init__(
            f"SOQL param {key!r} rejected: {reason} (preview={preview!r})"
        )


class SoqlTemplateNotFound(LookupError):
    """Raised when `load_soql(name)` cannot locate a matching template file.

    the message deliberately carries ONLY the requested
    template name — never the absolute SOQL_DIR path. This prevents leaking
    the filesystem layout of the skill install (which the attacker does not
    otherwise need to know) via error messages that bubble up to logs or
    RESULT blocks.

    Distinct from `FileNotFoundError` so callers can tell "template missing"
    apart from "filesystem I/O error" (permission denied, etc.) at the
    except-clause layer.
    """

    def __init__(self, name: str) -> None:
        # Preview bounds the echoed name at 60 chars. The validator forbids
        # traversal characters anyway, but defence in depth against an
        # arbitrarily-long attacker-controlled name ever reaching logs.
        try:
            preview = str(name)[:60]
        except Exception:
            preview = "<unreprable>"
        self.name = preview
        super().__init__(f"SOQL template not found: {preview!r}")


def load_soql(name: str, **params) -> str:
    """Read assets/soql/<name>.soql and substitute {{PARAM}} placeholders.

    every value in `params` is revalidated via
    `fs_guard.validate_api_name` before being substituted. Invalid values
    (non-string, empty, or containing any character outside [A-Za-z0-9_])
    raise `SoqlParamError`.

    `name` itself is validated via the same
    `fs_guard.validate_api_name` regex BEFORE any filesystem access.
    Without this, a caller that sources `name` from data (config file,
    user argument, etc.) could read `SOQL_DIR/../../../tmp/pwn.soql` via
    traversal. All SOQL template filenames in this skill match
    `^[A-Za-z0-9_]+$` (e.g. `bot_version_lookup`, `plugins_by_planner`),
    so the regex is the correct gate.

    Substitution is single-pass: `str.replace` does not re-scan the output,
    so a value that contains `{{OTHER}}` cannot re-trigger substitution of
    a different key. This is verified by test_soql_loader.
    """
    # validate the template name BEFORE touching the filesystem.
    # A raw `../../../etc/passwd` would otherwise resolve via read_text().
    try:
        fs_guard.validate_api_name(name, label="soql_template_name")
    except fs_guard.ValidationError as e:
        raise SoqlParamError("soql_template_name", name, e.reason) from None

    # revalidate every SOQL param before substitution. No exceptions,
    # no "this caller already validated" shortcuts. Defence in depth.
    for key, value in params.items():
        try:
            fs_guard.validate_api_name(value, label=key)
        except fs_guard.ValidationError as e:
            raise SoqlParamError(key, value, e.reason) from None

    # translate FileNotFoundError into SoqlTemplateNotFound so the
    # absolute SOQL_DIR path never bleeds into caller-visible error text.
    # We intentionally do NOT chain the original exception (`from None`) —
    # the original carries the full path in `filename`/`strerror`.
    try:
        soql = (SOQL_DIR / f"{name}.soql").read_text()
    except FileNotFoundError:
        raise SoqlTemplateNotFound(name) from None

    for key, value in params.items():
        # Plain str.replace: single-pass by construction. No re-substitution
        # of placeholders that appear inside a substituted value (see test).
        soql = soql.replace(f"{{{{{key}}}}}", value)
    return soql.strip()


def load_soql_in(
    name: str,
    *,
    string_params: Optional[Dict[str, str]] = None,
    list_params: Dict[str, List[str]],
) -> str:
    """Read assets/soql/<name>.soql and substitute both scalar and list placeholders.

    the BFS fan-out builds `WHERE X IN (:list)` queries
    (apex_class_bodies_by_names, flow_definition_by_ids, plugin_functions_
    by_plugin_ids, etc.). The existing `load_soql` only handles scalar
    string substitution; this sibling covers the list case without
    touching that signature.

    Parameters
    ----------
    name:
        Template filename (without `.soql`). Validated via
        `fs_guard.validate_api_name` BEFORE any filesystem access — same
        defence-in-depth gate as `load_soql` .
    string_params:
        Optional scalar {{KEY}} → value map. Values revalidated through
        `fs_guard.validate_api_name` — identical path to `load_soql`.
        Useful for templates that mix a single scalar value with a list
        in the same query. No active callers at present (retired with
        `flow_definition_ids_by_name_with_ns.soql` on 2026-05-05); kept
        on the signature as a stable extension point.
    list_params:
        Required. {{KEY}} → list-of-strings map. Each element is
        revalidated through `fs_guard.validate_api_name`; any failure
        aborts the whole call with `SoqlParamError(key=<list-key>, ...)`.
        Empty lists raise — SOQL `WHERE X IN ()` is a syntax error in
        Salesforce, fail fast rather than let the CLI surface an opaque
        500.

    Rendering
    ---------
    Lists render as `','.join(f"'{v}'" for v in sorted(set(list_value)))`:
    single-quoted, comma-separated, no surrounding parens. The `.soql`
    template supplies the parens around the `{{PLACEHOLDER}}` so the
    result reads `WHERE Id IN ('A','B','C')`.

    Deduplication is load-bearing: SOQL tolerates dupes but they waste
    the 100k-char query-length budget. Sort is for deterministic order —
    stable cache keys and diffable test output.

    Returns
    -------
    Substituted, `.strip()`-ed SOQL string.
    """
    # validate template name BEFORE touching the filesystem.
    try:
        fs_guard.validate_api_name(name, label="soql_template_name")
    except fs_guard.ValidationError as e:
        raise SoqlParamError("soql_template_name", name, e.reason) from None

    string_params = string_params or {}

    # / revalidate scalar params — same path as `load_soql`.
    for key, value in string_params.items():
        try:
            fs_guard.validate_api_name(value, label=key)
        except fs_guard.ValidationError as e:
            raise SoqlParamError(key, value, e.reason) from None

    # validate list params first (deterministic failure order — we
    # want the first bad element, not a partially-rendered string).
    rendered_lists: Dict[str, str] = {}
    for key, list_value in list_params.items():
        if not isinstance(list_value, list):
            raise SoqlParamError(
                key,
                list_value,
                f"list_params[{key}] must be a list, got {type(list_value).__name__}",
            )
        if not list_value:
            # Salesforce `WHERE X IN ()` is a hard syntax error — fail fast
            # at the loader, not at the CLI. Callers should branch on the
            # empty-list case upstream (e.g. skip the whole SOQL) rather
            # than rely on an empty-clause fallback.
            raise SoqlParamError(
                key, "[]", "empty-list-would-produce-invalid-soql",
            )
        # Dedupe + sort: cache-key stable, query-length budget sparing.
        # `sorted(set(...))` raises TypeError on non-hashable elements;
        # validate_api_name below will surface the real cause for
        # non-strings, so gate on type FIRST.
        for element in list_value:
            try:
                fs_guard.validate_api_name(element, label=key)
            except fs_guard.ValidationError as e:
                raise SoqlParamError(key, element, e.reason) from None
        unique_sorted = sorted(set(list_value))
        # Single-quote each element, comma-join. The `.soql` template
        # supplies the surrounding parens around `{{KEY}}`.
        rendered_lists[key] = ",".join(f"'{v}'" for v in unique_sorted)

    # translate FileNotFoundError into SoqlTemplateNotFound. Same
    # hygiene contract as `load_soql` — the absolute SOQL_DIR path must
    # not bleed into caller-visible error text.
    try:
        soql = (SOQL_DIR / f"{name}.soql").read_text()
    except FileNotFoundError:
        raise SoqlTemplateNotFound(name) from None

    # Single-pass substitution, same semantics as `load_soql`. Scalars
    # first, lists second — the order is only relevant if a scalar value
    # could contain a list-placeholder token, which `validate_api_name`
    # forbids (no `{` or `}` in `[A-Za-z0-9_]+`).
    for key, value in string_params.items():
        soql = soql.replace(f"{{{{{key}}}}}", value)
    for key, rendered in rendered_lists.items():
        soql = soql.replace(f"{{{{{key}}}}}", rendered)
    return soql.strip()
