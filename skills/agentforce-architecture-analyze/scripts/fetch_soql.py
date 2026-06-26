"""SOQL-based body fetchers for Wave A (GenAi normalized DAG) + Wave B
(Flow / Apex body bodies).

Phase 2 Batch 1: this module is the single surface `main.py`'s orchestrator
composes against. Every function in this module is a thin wrapper over
`soql_loader` + `rest_client.{tooling_query, data_query}`. Three invariants:

    1. Credentials always flow through a `creds_provider` closure
       (`Callable[[], tuple[str, str]]`) so `retry_on_401`'s refresh path
       can deliver fresh creds into the retry. See rest_client 
    2. Empty list inputs short-circuit to `[]` WITHOUT firing a SOQL call.
       `load_soql_in` refuses empty lists (SF syntax error), so callers
       upstream shouldn't have to guard every batch site — guard once here.
    3. `api_version` (.4-R4, 2026-05-02) is REQUIRED on every fetcher.
       The prior `rest_client.tooling_query` pinned `v60.0` and that
       floor was the source of on orgs running v66 — which
       genuinely expose fields v60 does not (`BotDefinition.Description`
       is the observed case). Callers read the version once via
       `main._derive_org_ids` (from `sf org display --json`) and thread
       it through here. Same defensive pattern as for
       `on_401_refresh`: no default, so a missed call-site is a
       TypeError at call time, not a silent regression.

All failure paths use `rest_client.redact_error` implicitly: the helpers
raise `RestClientError` with pre-redacted messages. Callers that log should
call `redact_error(exc)` themselves rather than `str(exc)` on any wrapped
urllib/subprocess exception — redaction at the reporting site is
defence-in-depth.

`on_401_refresh` is a REQUIRED keyword-only arg
on every fetcher in this module. The previous default (`on_401_refresh
or creds_provider`) silently collapsed to "re-read the same stale token"
when a caller passed `None` — the retry would hit the identical stale
token on the second attempt and 401 again, bypassing entirely.
Making the parameter required surfaces that misuse as a TypeError at
import/call time instead of as a silent auth failure under load.
"""
from __future__ import annotations

import logging
import urllib.error
from typing import Callable, Tuple

from rest_client import data_query, tooling_query
from soql_loader import load_soql, load_soql_in

logger = logging.getLogger(__name__)


CredsProvider = Callable[[], Tuple[str, str]]


# ---------------------------------------------------------------------------
# Small record-extraction helper. SF REST query responses wrap the row list
# under `.records`; tooling + data surfaces agree on this shape. One helper
# keeps the Wave A/B fetchers trivial — they call `_records(tooling_query(...))`
# and return a list[dict].
# ---------------------------------------------------------------------------


def _records(response: dict) -> list[dict]:
    """Extract records list from a SOQL query response.

    SF REST returns `{"totalSize": N, "done": true, "records": [...]}` on
    both Data and Tooling APIs. A missing `records` key (malformed response,
    empty result) degrades to `[]` — callers that need a single record
    slice the list themselves; callers that batch don't have to branch on
    "records missing".
    """
    if not isinstance(response, dict):
        return []
    recs = response.get("records")
    if not isinstance(recs, list):
        return []
    return recs


# ===========================================================================
# Wave A — GenAi normalized fetchers (Tooling API only)
# ===========================================================================
# DAG, per plan section B.5:
#
# A1 planner_definition_by_agent_chain scalar: AGENT_NAME [+ VERSION]
# A2 plugins_by_planner scalar: PLANNER_ID
# A3 planner_bundle_functions scalar: PLANNER_ID
# A4 functions_by_plugins list: PLUGIN_IDS
# A5 plugin_instructions_by_plugin_ids list: PLUGIN_IDS
# A6 plugin_functions_by_plugin_ids list: PLUGIN_IDS
# A7 planner_attrs_by_parent_ids list: PARENT_IDS
#
# Ordering: A1 first (provides planner_id). Then A2 + A3 can parallelize.
# Once A2 yields plugin_ids, A4 / A5 / A6 parallelize. A7 last once A4
# yields function_ids.
# ---------------------------------------------------------------------------


def fetch_planner_definition(
    agent_api_name: str,
    version: str | None,
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> dict | None:
    """Wave A1: resolve the live GenAiPlannerDefinition for (agent, version).

    Agentforce generates an accretive chain of planner DeveloperNames as
    agents version up — v1 = `<Agent>`, v2 = `<Agent>_v2`, v3 =
    `<Agent>_v2_v3`, ... The chain shape is unpredictable from
    (agent, version) alone, but an invariant holds: for vN the
    DeveloperName always starts with `<agent_api_name>` and ends with
    `_v<N>` for N>=2; for v1 it is exactly `<agent_api_name>`. A single
    SOQL LIKE lookup pinned to that shape lands on the correct row
    regardless of chain depth.

    Branching:
      * `version` is None / empty / "v1" → exact match. SOQL built
        inline as `LIKE '<agent_api_name>'` (no wildcards — degenerate
        LIKE is equivalent to `=`). The v1 branch bypasses the chain
        template because the template's `%\\_{{VERSION}}` tail has no
        sensible empty-version rendering.
      * v2+ → LIKE `<agent_api_name>%\\_<version>`. The backslash escapes
        the single-char wildcard `_` so `_v2` matches literally, not as
        "any character then v2".

    Escaping note (2026-05-05): the SOQL template on disk carries `\\_`
    (one backslash, one underscore) because the REST Query endpoint
    consumes the body verbatim — no shell, no extra quoting layer. If a
    future caller ever shells this through `bash -c`, the backslash would
    need doubling; we don't currently have that call path.

    Disambiguation: if the LIKE returns multiple rows (e.g. a longer
    chain name ALSO matches the pattern because it happens to end in
    `_v2` too), pick the shortest DeveloperName — the canonical chain
    ends at exactly `<agent_api_name>...<_v{version}>` with no suffix,
    so shortest always wins.

    Returns the planner dict or `None` if no row matches.

    `load_soql` revalidates each substituted value against
    `[A-Za-z0-9_]+` . `agent_api_name` and `version` satisfy that
    regex; the `%\\_` literals live in the SOQL template, not in a
    substituted variable, so they never traverse the validator.
    """
    v = (version or "").strip()
    if v in ("", "v1"):
        # v1 branch: DeveloperName is exactly `<agent_api_name>`. A LIKE
        # with no wildcards is equivalent to `=`. We can't re-use the
        # chain template with an empty VERSION (load_soql rejects empty
        # strings AND the template's trailing `%\_{{VERSION}}` wouldn't
        # collapse cleanly), so build the SOQL directly here. We still
        # run the agent_api_name through the same validator load_soql
        # uses, so the v1 path has no weaker injection surface than the
        # v2+ path.
        from config import fs_guard  # re-exported from _shared/
        from soql_loader import SoqlParamError as _SoqlParamError
        try:
            fs_guard.validate_api_name(agent_api_name, label="AGENT_NAME")
        except fs_guard.ValidationError as e:
            raise _SoqlParamError("AGENT_NAME", agent_api_name, e.reason) from None
        soql = (
            "SELECT Id, DeveloperName, MasterLabel, Description, "
            "PlannerType, Capabilities, AgentGraph\n"
            "FROM GenAiPlannerDefinition\n"
            f"WHERE DeveloperName LIKE '{agent_api_name}'"
        )
    else:
        soql = load_soql(
            "planner_definition_by_agent_chain",
            AGENT_NAME=agent_api_name,
            VERSION=v,
        )
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    recs = _records(resp)
    if not recs:
        return None
    # Disambiguate on shortest DeveloperName — the canonical chain row
    # has no suffix beyond `_v<N>`. A longer row means the LIKE also
    # matched a deeper-chain planner that happens to share the suffix.
    recs.sort(key=lambda r: len(r.get("DeveloperName") or ""))
    return recs[0]


def fetch_plugins_by_planner(
    planner_id: str,
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave A2: topic list for a planner."""
    soql = load_soql("plugins_by_planner", PLANNER_ID=planner_id)
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_planner_bundle_functions(
    planner_id: str,
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave A3: planner-bundle-scope function join rows (classic).

    NGA planners have no bundle-scope functions (PlannerId is null on
    every row); this query returns [] on NGA orgs. Caller doesn't have
    to branch.
    """
    soql = load_soql("planner_bundle_functions", PLANNER_ID=planner_id)
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_functions_by_plugins(
    plugin_ids: list[str],
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave A4: actions (GenAiFunctionDefinition) under a planner's plugins.

    User invariant: a planner never has direct functions (PlannerId-only
    rows with no PluginId are orphan data, not live actions). The prior
    `PlannerId = '<id>' OR ...` leg dragged in those orphans and
    surfaced them as stray root-level children. The query is now a
    single IN-list over plugin_ids; the PlannerId + ParentId columns
    stay in the SELECT for downstream consumers (parse_bundle, etc.)
    that still read them.

    Empty `plugin_ids` short-circuits — a SequentialPlannerIntent-
    Classifier bot with zero plugins has no plugin-scope functions to
    fetch. `load_soql_in` refuses empty lists; we guard here so callers
    don't have to.
    """
    if not plugin_ids:
        return []
    soql = load_soql_in(
        "functions_by_plugins",
        list_params={"PLUGIN_IDS": plugin_ids},
    )
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_plugin_instructions(
    plugin_ids: list[str],
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave A5: per-topic instruction rows.

    Empty `plugin_ids` → []; no SOQL fired. SequentialPlannerIntent-
    Classifier bots and NGA single-planner shapes hit this path.
    """
    if not plugin_ids:
        return []
    soql = load_soql_in(
        "plugin_instructions_by_plugin_ids",
        list_params={"PLUGIN_IDS": plugin_ids},
    )
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_plugin_functions(
    plugin_ids: list[str],
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave A6: plugin → function join rows."""
    if not plugin_ids:
        return []
    soql = load_soql_in(
        "plugin_functions_by_plugin_ids",
        list_params={"PLUGIN_IDS": plugin_ids},
    )
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_planner_attrs(
    parent_ids: list[str],
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave A7: attribute mappings for a list of parent ids.

    Polymorphic ParentId: pass the UNION of function_ids + planner_id.
    Bot shape with zero functions (no actions registered) → []; no SOQL
    fired. Caller must include the planner_id even when function_ids is
    empty — this helper doesn't fabricate it.
    """
    if not parent_ids:
        return []
    soql = load_soql_in(
        "planner_attrs_by_parent_ids",
        list_params={"PARENT_IDS": parent_ids},
    )
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


# ===========================================================================
# Wave B — body fetchers (Flow, Apex). Tooling API.
# ===========================================================================
# These are the leaves: once Wave A gives us the function rows, we resolve
# every InvocationTarget into one of flow / apex / prompt (prompt body
# lands via retrieve in Batch 2, not here).
#
# The single-row Flow.Metadata path is the big parallelism opportunity —
# `fetch_flow_metadata` is called N times (one per version id) and
# dispatched through `parallel_retrieve.fetch_bodies_parallel`.
# ---------------------------------------------------------------------------


def fetch_apex_bodies_by_names(
    names: list[str],
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave B3 classic: Apex bodies keyed by DeveloperName.

    Returns `[{Id, Name, Body, SymbolTable, ApiVersion, IsValid}, ...]`.
    Batch-safe on `Name IN (...)` even though SymbolTable is
    complexvalue (confirmed live — see references/soql_fields.md).
    """
    if not names:
        return []
    soql = load_soql_in(
        "apex_class_bodies_by_names",
        list_params={"NAMES_LIST": names},
    )
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_apex_bodies_by_ids(
    ids: list[str],
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave B3 NGA: Apex bodies keyed by Id.

    NGA functions store InvocationTarget as Salesforce Ids (e.g. `01p...`);
    this is the reverse-lookup path that translates back to Name + Body.
    """
    if not ids:
        return []
    soql = load_soql_in(
        "apex_class_bodies_by_ids",
        list_params={"APEX_IDS_LIST": ids},
    )
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_flow_definition_view_by_durable_ids(
    durable_ids: list[str],
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Data API fallback: resolve managed-installed flow names via
    `FlowDefinitionView`.

    `FlowDefinition` (Tooling) does not index managed-installed flows for
    subscriber orgs — the Tooling query for a `ns__BareName` returns zero
    rows even when the flow genuinely exists. `FlowDefinitionView` (Data
    API only, NOT Tooling) does expose those rows via its `DurableId`
    column, which for managed-installed flows IS the qualified
    `ns__BareName` string.

    Caveats baked into the consumer contract (see
    `fetch_flow_definition_ids_by_names` downstream projection):
      * `FlowDefinitionView.ActiveVersionId` is a composite display
        string (e.g. `SvcCopilotTmpl__VerifyCode-1`), not a real
        `Flow.Id`. It cannot be used to fetch the flow body XML —
        managed flow bodies are IP-protected and not retrievable.
      * Callers must project these rows with `ActiveVersionId=None` and
        `_body_available=False` so the Wave B metadata fetcher skips
        body retrieval for them.

    Empty input short-circuits to `[]` without firing a SOQL call —
    matches the contract on every other list-shaped fetcher in this
    module.
    """
    if not durable_ids:
        return []
    soql = load_soql_in(
        "flow_definition_view_by_durable_ids",
        list_params={"DURABLE_IDS_LIST": durable_ids},
    )
    resp = data_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_flow_definition_ids_by_names(
    names: list[str],
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave B1 classic: resolve Flow DeveloperName list → FlowDefinition rows.

    Returns `[{Id, DeveloperName, NamespacePrefix, ActiveVersionId,
    _bare_developer_name, _source, _body_available, ...}, ...]`.
    Two-hop to `Flow` via `ActiveVersionId`; this is the first hop.

    Resolution path (2026-05-05, post-retirement of the managed-ns
    Tooling bucket): fire ONE Tooling `FlowDefinition` query for every
    input name verbatim — the template filters `NamespacePrefix IS NULL`
    so only unmanaged rows come back. Managed names like
    `ns__BareName` return zero rows from Tooling on subscriber orgs
    regardless of how we bucket them (live scouting confirmed Tooling
    FlowDefinition simply does not index managed-installed flows for
    subscribers), so attempting per-namespace Tooling queries adds cost
    and returns nothing useful. Anything the unmanaged query doesn't
    resolve falls through to `FlowDefinitionView` (Data API), which DOES
    expose managed-installed flows via `DurableId = ns__BareName`.

    FlowDefinitionView rows carry `Id=None`, `ActiveVersionId=None`,
    `_body_available=False`, and `_source="FlowDefinitionView"` so
    downstream flow metadata retrieval short-circuits (there's no real
    version Id to fetch a body with, and managed flow bodies are
    IP-protected regardless).

    Real Tooling rows carry `_source="FlowDefinition"` and
    `_body_available=True` set explicitly — consumers can dispatch on
    source rather than inferring from absence.
    """
    if not names:
        return []

    rows: list[dict] = []
    # Track every input name we successfully resolve via the Tooling
    # FlowDefinition path. Anything left over goes through the
    # FlowDefinitionView fallback.
    resolved_names: set[str] = set()

    # Unmanaged Tooling query: template explicitly filters
    # `NamespacePrefix = NULL`. Managed-qualified names (`ns__BareName`)
    # passed through here will simply return zero rows — which is fine,
    # the view fallback below catches them. The null-ns filter is
    # load-bearing: dropping it would widen to unrelated managed rows
    # that happen to collide on a bare DeveloperName.
    #
    # Bug G fix: the SOQL template uses `= NULL`, NOT `IS NULL`. Tooling
    # Query API rejects `IS NULL` with `MALFORMED_QUERY: unexpected
    # token: 'NamespacePrefix IS'`. Only the Data API parser accepts
    # both forms. Commit aa01d52 mistakenly switched this template to
    # `IS NULL` (to silence a Prizm scanner false-positive) on the
    # premise that "both forms parse identically" — true for Data API,
    # false for Tooling. That broke wave-B subflow resolution: every
    # call here 400'd, the FDV fallback below also returned zero
    # because it filters by Salesforce Id (300...), and BFS hit the
    # iteration cap. Do NOT re-introduce `IS NULL` in this template.
    soql = load_soql_in(
        "flow_definition_ids_by_names",
        list_params={"NAMES_LIST": list(names)},
    )
    # Bug D.2 fix: tolerate HTTPError on the Tooling call. A single name
    # in `names` that violates Salesforce's DeveloperName limits (e.g.
    # length >40 chars, or chars Salesforce treats as non-identifier
    # despite passing fs_guard.validate_api_name) causes the WHOLE batch
    # to 400. Without this `try`, the entire wave-B round failed and the
    # FDV fallback below was never reached — managed names were never
    # resolved, BFS hit the iteration cap, operator saw cryptic
    # `wave-b-iteration-cap` entries instead of the actual root cause.
    # On HTTPError, fall through with `resolved_names` empty so every
    # input is re-tried via FDV; FDV uses Data API (different validation)
    # and tends to accept names Tooling rejects.
    try:
        resp = tooling_query(
            creds_provider, soql,
            api_version=api_version,
            on_401_refresh=on_401_refresh,
        )
        for r in _records(resp):
            dev_name = r.get("DeveloperName")
            if dev_name:
                r["_bare_developer_name"] = dev_name
                r["_source"] = "FlowDefinition"
                r["_body_available"] = True
                rows.append(r)
                resolved_names.add(dev_name)
    except urllib.error.HTTPError as exc:
        # Don't propagate — the FDV fallback below handles every
        # unresolved name. Log enough for triage; rest_client already
        # attached `_response_body_preview` (Bug D.1) so the body is
        # available downstream if a caller wants to inspect.
        logger.debug(
            "fetch_flow_definition_ids_by_names: Tooling batch failed "
            "(HTTP %d); falling through to FlowDefinitionView for all %d names",
            getattr(exc, "code", 0), len(names),
        )

    # FlowDefinitionView fallback — Data API. Any input name Tooling
    # didn't resolve is re-queried as a DurableId. Managed-installed
    # flows are the motivating case; the view also covers unmanaged
    # rows the Tooling surface misses for any other reason.
    unresolved_names = [n for n in names if n not in resolved_names]
    if unresolved_names:
        view_rows = fetch_flow_definition_view_by_durable_ids(
            sorted(set(unresolved_names)),
            creds_provider,
            api_version=api_version,
            on_401_refresh=on_401_refresh,
        )
        for view_row in view_rows:
            durable_id = view_row.get("DurableId")
            if not durable_id:
                continue
            rows.append({
                "Id": None,
                # Qualified ns__bare (matches bundle invocationTarget +
                # parse_wave visited-set dedupe key).
                "DeveloperName": durable_id,
                "NamespacePrefix": view_row.get("NamespacePrefix"),
                # ActiveVersionId on FlowDefinitionView is a composite
                # display string (`ns__Name-<n>`), NOT a real Flow.Id.
                # Null it so downstream `fetch_flow_metadata` dispatch
                # skips body retrieval for these rows.
                "ActiveVersionId": None,
                "_bare_developer_name": view_row.get("ApiName"),
                "_body_available": False,
                "_source": "FlowDefinitionView",
                "_flow_view_label": view_row.get("Label"),
                "_flow_view_manageable_state": view_row.get("ManageableState"),
            })

    return rows


def fetch_flow_definition_by_ids(
    ids: list[str],
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Wave B1 NGA: reverse-lookup FlowDefinition Id → DeveloperName.

    NGA functions store Ids (`300...`). This resolves them back to names
    so the tree's leaf nodes can carry the human-readable DeveloperName
    and the active version id for Wave B2.
    """
    if not ids:
        return []
    soql = load_soql_in(
        "flow_definition_by_ids",
        list_params={"FLOW_DEF_IDS_LIST": ids},
    )
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_flow_metadata(
    flow_version_id: str,
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> dict | None:
    """Wave B2: single-row Flow.Metadata fetch.

    `complexvalue` fields (Metadata + FullName) force a single-row
    retrieval (`WHERE Id = '<id>'`). Returns the row dict or `None` on
    miss. Called once per version id; parallelism happens in `main.py`
    via `parallel_retrieve.fetch_bodies_parallel`.
    """
    soql = load_soql("flow_metadata_by_id", FLOW_VERSION_ID=flow_version_id)
    resp = tooling_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    recs = _records(resp)
    return recs[0] if recs else None


# ===========================================================================
# Bot resolution (Data API) — Phase 4 of main.py. Separate from Wave A/B
# because the routing is DATA_QUERY not tooling, and the shape is simpler.
# ===========================================================================


def fetch_bot_versions(
    agent_api_name: str,
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> list[dict]:
    """Data API: resolve bot versions for a given bot DeveloperName.

    Mirrors `resolve_bot.py` step 1 but routed through `data_query` so
    the 401-refresh path is active. `resolve_bot.py` itself shells out
    to `sf data query` and is retained as the env-var-driven entry-point
    for Bash harness callers; `main.py` uses this in-process variant.
    """
    soql = load_soql("bot_version_lookup", AGENT_API_NAME=agent_api_name)
    resp = data_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    return _records(resp)


def fetch_bot_definition_details(
    agent_api_name: str,
    creds_provider: CredsProvider,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> dict | None:
    """Data API: BotDefinition metadata (MasterLabel, AgentTemplate, ...).

    Returns the single matching BotDefinition row or None. Feeds the
    `tree["agent"]` fields in parse_wave's init_tree.
    """
    soql = load_soql("bot_definition_details", AGENT_API_NAME=agent_api_name)
    resp = data_query(
        creds_provider, soql,
        api_version=api_version,
        on_401_refresh=on_401_refresh,
    )
    recs = _records(resp)
    return recs[0] if recs else None


