"""NGA InvocationTarget ID-prefix router.

NGA bots store Salesforce Ids in GenAiFunctionDefinition.InvocationTarget,
not DeveloperNames. This module resolves the kind by the 3-char key prefix.

unknown prefixes MUST NEVER raise — Salesforce is free to introduce
new NGA target types (e.g., a hypothetical `0aN...` AgentCapability) and
the skill must degrade gracefully. Callers use `resolve_or_unresolved` to
append a `_unresolved[]` entry with a diagnostic reason and get back
`("unknown", "skip")` so the wave orchestrator can keep parsing.

Invariants:
  * Only the 3-char prefix is consulted for Id-based routing — 15-char
    and 18-char Ids both map the same way.
  * `standard_action` kind is selected by caller context (bundle's
    `invocationTargetType == "standardInvocableAction"`), not by prefix —
    standard actions have no Id. Its presence in the Kind union is
    scaffolding for call-site type-checking.
  * `REGISTERED_PREFIXES` exposes the known prefix set as a frozenset for
    tests and probe-channel validation.
"""
from __future__ import annotations

import re
from typing import Literal

Kind = Literal[
    "apex",
    "flow_definition",
    "flow_version",
    "prompt_template",
    "standard_action",
    "unknown",
]
Channel = Literal[
    "tooling_soql",
    "retrieve_required",
    "skip",
]

_PREFIX_MAP: dict[str, tuple[Kind, Channel]] = {
    "01p": ("apex", "tooling_soql"),
    "300": ("flow_definition", "tooling_soql"),
    "301": ("flow_version", "tooling_soql"),
    "0hf": ("prompt_template", "retrieve_required"),
}

# public reverse-lookup set. `frozenset` (not set) so callers can't
# mutate the authoritative table by accident.
REGISTERED_PREFIXES: frozenset[str] = frozenset(_PREFIX_MAP.keys())

# Salesforce Ids are 15 or 18 chars, alphanumeric only. This is the gate
# between "could be a real Id with an unknown prefix" (treat as an NGA
# addition we don't know about yet) and "garbage input" (empty, wrong
# length, bad characters — treat as invalid format).
_SF_ID_RE = re.compile(r"^[A-Za-z0-9]+$")
_SF_ID_LENGTHS = frozenset({15, 18})


def looks_like_sf_id(id_str: object) -> bool:
    """True iff `id_str` is a 15- or 18-char alphanumeric string.

    promoted from module-private `_looks_like_sf_id`
    so `main._route` can gate calls to `resolve_or_unresolved` on the
    Id shape without reaching into a leading-underscore symbol (same
    surface). Underscore form retained as a deprecated alias.
    """
    if not isinstance(id_str, str):
        return False
    if len(id_str) not in _SF_ID_LENGTHS:
        return False
    return bool(_SF_ID_RE.match(id_str))


# backcompat alias — deprecated; use `looks_like_sf_id`.
_looks_like_sf_id = looks_like_sf_id


def resolve_target_id(id_str: str) -> tuple[Kind, Channel]:
    """Return (kind, resolvable_via) for a Salesforce Id.

    unknown prefixes NEVER raise — callers observing ("unknown", "skip")
    are expected to route through `resolve_or_unresolved` (or equivalent)
    to append an `_unresolved[]` entry. This function stays pure — it does
    not mutate any caller state, does not log.
    """
    if not id_str or not isinstance(id_str, str) or len(id_str) < 3:
        return ("unknown", "skip")
    prefix = id_str[:3]
    return _PREFIX_MAP.get(prefix, ("unknown", "skip"))


def resolve_or_unresolved(
    id_str: object,
    unresolved: list[dict],
) -> tuple[Kind, Channel]:
    """Like `resolve_target_id` but records failures into `unresolved`.

    semantics:
      * Valid Salesforce Id (15 or 18 alphanumeric chars) with known prefix:
        route as usual. `unresolved` untouched.
      * Valid Id shape, unknown prefix: append
        `{"id": <id>, "reason": f"unknown-id-prefix:{id[:3]}"}` and
        return ("unknown", "skip"). This is the "NGA shipped a new type"
        path — the wave orchestrator keeps running.
      * Not an Id shape (empty/None/wrong length/bad chars): append
        `{"id": str(id_str), "reason": "invalid-id-format"}` and return
        ("unknown", "skip"). Distinct reason so triage can tell "NGA
        added something new" apart from "caller passed us garbage."

    `unresolved` is mutated in place — same contract as `_unresolved[]`
    throughout the skill. Caller owns the list.
    """
    if _looks_like_sf_id(id_str):
        kind, channel = resolve_target_id(id_str)  # type: ignore[arg-type]
        if kind == "unknown":
            # Real Id shape, prefix we don't recognize — record the prefix
            # so triage can add it to _PREFIX_MAP.
            unresolved.append({
                "id": id_str,
                "reason": f"unknown-id-prefix:{id_str[:3]}",  # type: ignore[index]
            })
        return (kind, channel)

    # Not a valid Id shape — empty, None, wrong length, or bad chars.
    unresolved.append({
        "id": str(id_str),
        "reason": "invalid-id-format",
    })
    return ("unknown", "skip")
