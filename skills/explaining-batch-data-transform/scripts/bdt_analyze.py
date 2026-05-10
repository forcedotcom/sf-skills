#!/usr/bin/env python3
"""Analyze Salesforce Data Cloud Batch Data Transform (BDT) JSON.

This module provides a generic typed-DAG parser over BDT JSON definitions.
Grounded against the canonical BDT Connect API InputRepresentation classes.
Design principle: structural facts come from deterministic graph walks here;
narrative explanations are built by the host LLM.

Usage (CLI lands in a later plan):
    python bdt_analyze.py <subcommand> <bdt.json> [...]

Requirements:
    - Python 3.9+ (standard library only).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple


# --------- Exit codes ---------------------------------------------------------
EXIT_OK = 0
EXIT_NOT_FOUND = 2      # unknown node / field
EXIT_BAD_INPUT = 3      # malformed JSON / bad shape / cycle


# --------- Exceptions --------------------------------------------------------
class BdtInputError(Exception):
    """Raised on any malformed input. CLI maps this to exit code 3."""


class BdtNotFoundError(Exception):
    """Raised when a queried node or field doesn't exist. CLI maps to exit 2."""


@dataclass
class Node:
    """One entry in BDT `nodes{}`."""
    name: str
    action: str
    sources: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    schema: Optional[Dict[str, Any]] = None
    ui_label: Optional[str] = None
    ui_description: Optional[str] = None

    @property
    def display_name(self) -> str:
        """UI label if present and non-empty; else node name."""
        if self.ui_label:
            return f"{self.ui_label} ({self.name})"
        return self.name


@dataclass
class Definition:
    """One parsed STL block from a BDT payload.

    A `DataTransform` always holds at least one of these (length 1 for the
    editor-export and single-definition Connect API shapes, length N for the
    multi-definition Connect API shape).
    """
    index: int
    version: Optional[str]
    nodes: Dict[str, Node]
    ui: Dict[str, Any]
    name: Optional[str] = None
    label: Optional[str] = None


@dataclass
class DataTransform:
    """Parsed BDT JSON, with a typed DAG view.

    The parser accepts both the editor-export shape (`nodes` at top level) and
    the Connect API create-payload shapes (`definition` or `definitions[]`
    wrappers around the editor-export content). When a wrapper is detected the
    parser descends into the STL definition(s) transparently; outer metadata
    (name, label, type, dataSpaceName) is preserved as optional attributes.

    For multi-definition payloads, every definition is parsed and kept on
    `self.definitions`. The currently-selected definition (default index 0)
    drives the pass-through properties `nodes`, `version`, and `ui`, so all
    existing methods operate on the selected block with no signature changes.
    Callers can hop between definitions with `select_definition(index)`.
    """
    definitions: List[Definition]
    # Outer-wrapper metadata (only populated for Connect API input shapes).
    name: Optional[str] = None
    label: Optional[str] = None
    data_transform_type: Optional[str] = None
    data_space_name: Optional[str] = None
    # Which definition the accessor properties return; 0 by default.
    selected_index: int = 0

    # --- Backward-compat pass-through properties ---------------------------
    # Existing callers (tests + CLI handlers) read `.nodes`, `.version`, `.ui`
    # as simple attributes; keep that shape by delegating to the selected
    # definition.

    @property
    def nodes(self) -> Dict[str, Node]:
        return self.definitions[self.selected_index].nodes

    @property
    def version(self) -> Optional[str]:
        return self.definitions[self.selected_index].version

    @property
    def ui(self) -> Dict[str, Any]:
        return self.definitions[self.selected_index].ui

    @property
    def definition_count(self) -> int:
        return len(self.definitions)

    @property
    def definition_index(self) -> int:
        return self.selected_index

    def select_definition(self, index: int) -> None:
        """Pick which definition the accessor properties (and the rest of the
        API surface) operate on. Raises `BdtNotFoundError` if `index` is out
        of range."""
        if type(index) is not int or index < 0 or index >= len(self.definitions):
            raise BdtNotFoundError(
                f"Definition index {index} out of range; payload has "
                f"{len(self.definitions)} definitions "
                f"(indices 0-{len(self.definitions) - 1})."
            )
        self.selected_index = index

    @classmethod
    def from_path(cls, path: pathlib.Path) -> "DataTransform":
        path = pathlib.Path(path)
        try:
            raw = json.loads(path.read_text())
        except OSError as e:
            raise BdtInputError(f"Cannot read {path}: {e}") from e
        except json.JSONDecodeError as e:
            raise BdtInputError(
                f"Invalid JSON in {path} at line {e.lineno}, col {e.colno}: {e.msg}"
            ) from e
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "DataTransform":
        if not isinstance(raw, Mapping):
            raise BdtInputError("Top-level BDT JSON must be an object")

        # --- Shape detection -------------------------------------------------
        # 1. Editor-export shape: `nodes` at top level — exactly one definition.
        # 2. Connect API single-definition shape: `definition` object with
        #    `nodes` — one definition, plus outer wrapper metadata.
        # 3. Connect API multi-definition shape: non-empty `definitions` array
        #    whose entries each have `nodes` — N definitions, plus outer
        #    wrapper metadata. Every definition is parsed.
        outer_name: Optional[str] = None
        outer_label: Optional[str] = None
        outer_type: Optional[str] = None
        outer_data_space: Optional[str] = None
        raw_definitions: List[Mapping[str, Any]]

        if isinstance(raw.get("nodes"), Mapping):
            raw_definitions = [raw]
        elif (isinstance(raw.get("definition"), Mapping)
              and isinstance(raw["definition"].get("nodes"), Mapping)):
            raw_definitions = [raw["definition"]]
            outer_name = raw.get("name") if isinstance(raw.get("name"), str) else None
            outer_label = raw.get("label") if isinstance(raw.get("label"), str) else None
            outer_type = raw.get("type") if isinstance(raw.get("type"), str) else None
            outer_data_space = (
                raw.get("dataSpaceName") if isinstance(raw.get("dataSpaceName"), str) else None
            )
        elif (isinstance(raw.get("definitions"), list)
              and len(raw["definitions"]) > 0
              and all(
                  isinstance(d, Mapping) and isinstance(d.get("nodes"), Mapping)
                  for d in raw["definitions"]
              )):
            raw_definitions = list(raw["definitions"])
            outer_name = raw.get("name") if isinstance(raw.get("name"), str) else None
            outer_label = raw.get("label") if isinstance(raw.get("label"), str) else None
            outer_type = raw.get("type") if isinstance(raw.get("type"), str) else None
            outer_data_space = (
                raw.get("dataSpaceName") if isinstance(raw.get("dataSpaceName"), str) else None
            )
        else:
            raise BdtInputError(
                "Expected 'nodes' at top level, or 'definition.nodes', "
                "or 'definitions[].nodes'; none found"
            )

        definitions: List[Definition] = []
        for idx, def_raw in enumerate(raw_definitions):
            definitions.append(
                cls._parse_definition(
                    idx, def_raw,
                    fallback_name=outer_name,
                    fallback_label=outer_label,
                )
            )

        return cls(
            definitions=definitions,
            name=outer_name,
            label=outer_label,
            data_transform_type=outer_type,
            data_space_name=outer_data_space,
            selected_index=0,
        )

    @classmethod
    def _parse_definition(
        cls,
        index: int,
        definition: Mapping[str, Any],
        fallback_name: Optional[str] = None,
        fallback_label: Optional[str] = None,
    ) -> Definition:
        """Parse a single STL block into a `Definition`.

        `name`/`label` come from the definition itself when present; otherwise
        fall back to the outer wrapper's values (so a single-definition API
        payload still carries the transform's name on `definitions[0]`).
        """
        nodes_raw = definition.get("nodes")
        if not isinstance(nodes_raw, Mapping):
            # Defensive: the shape-detection step should keep this out.
            raise BdtInputError(
                "Expected 'nodes' at top level, or 'definition.nodes', "
                "or 'definitions[].nodes'; none found"
            )
        ui = definition.get("ui") or {}
        ui_nodes = (ui.get("nodes") if isinstance(ui, Mapping) else {}) or {}

        nodes: Dict[str, Node] = {}
        for name, body in nodes_raw.items():
            if not isinstance(body, Mapping):
                raise BdtInputError(f"Node {name!r} body is not an object")
            action = body.get("action")
            if not isinstance(action, str) or not action:
                raise BdtInputError(f"Node {name!r} missing string 'action'")
            srcs = body.get("sources") or []
            if not isinstance(srcs, list):
                raise BdtInputError(f"Node {name!r} 'sources' is not a list")
            ui_entry = ui_nodes.get(name) or {}
            nodes[name] = Node(
                name=name,
                action=action,
                sources=list(srcs),
                parameters=dict(body.get("parameters") or {}),
                schema=body.get("schema"),
                ui_label=(ui_entry.get("label") if isinstance(ui_entry, Mapping) else None) or None,
                ui_description=(ui_entry.get("description") if isinstance(ui_entry, Mapping) else None) or None,
            )

        def_name = definition.get("name") if isinstance(definition.get("name"), str) else None
        def_label = definition.get("label") if isinstance(definition.get("label"), str) else None

        return Definition(
            index=index,
            version=definition.get("version"),
            nodes=nodes,
            ui=dict(ui) if isinstance(ui, Mapping) else {},
            name=def_name or fallback_name,
            label=def_label or fallback_label,
        )

    def warnings(self) -> List[str]:
        """Non-fatal advisories about the parsed BDT.

        The multi-definition case used to emit an advisory here ("payload
        contains N definitions; this skill explains the first only"). With
        full multi-definition support that warning is gone; the method is
        preserved for future advisories and currently returns an empty list.
        """
        return []

    def roots(self) -> List[str]:
        """Node names with no sources (data enters here)."""
        return [name for name, n in self.nodes.items() if not n.sources]

    def sinks(self) -> List[str]:
        """Node names that are not listed as a source by any other node (data exits here)."""
        referenced = set()
        for n in self.nodes.values():
            referenced.update(n.sources)
        return [name for name in self.nodes if name not in referenced]

    def topo_order(self) -> List[str]:
        """Kahn's algorithm. Raises BdtInputError on cycles."""
        from collections import deque
        in_degree: Dict[str, int] = {name: 0 for name in self.nodes}
        forward: Dict[str, List[str]] = {name: [] for name in self.nodes}
        for name, n in self.nodes.items():
            for s in n.sources:
                if s not in self.nodes:
                    # Broken reference — count as in-edge so the dependent node stays blocked
                    in_degree[name] += 1
                    continue
                forward[s].append(name)
                in_degree[name] += 1

        # Sort zero-in-degree nodes once for deterministic starting order
        ready = deque(sorted([name for name, d in in_degree.items() if d == 0]))
        order: List[str] = []
        while ready:
            current = ready.popleft()
            order.append(current)
            # Collect newly-ready nodes, sort them once, append
            newly_ready = []
            for consumer in forward[current]:
                in_degree[consumer] -= 1
                if in_degree[consumer] == 0:
                    newly_ready.append(consumer)
            for node in sorted(newly_ready):
                ready.append(node)

        if len(order) != len(self.nodes):
            stuck = [n for n in self.nodes if n not in order]
            raise BdtInputError(
                f"Cycle or broken reference detected; unresolved nodes: {sorted(stuck)}"
            )
        return order

    def _topo_order_subset(self, subset: Set[str]) -> List[str]:
        """Kahn's algorithm restricted to `subset`.

        Only edges whose endpoints are both in `subset` are considered. This
        tolerates broken references that sit outside the queried sub-DAG and
        avoids crashing on unrelated cycles. Assumes the sub-DAG itself is
        acyclic (caller guarantees this by restricting to a reachable set
        via a walk that skips broken refs).
        """
        in_degree: Dict[str, int] = {name: 0 for name in subset}
        forward: Dict[str, List[str]] = {name: [] for name in subset}
        for name in subset:
            n = self.nodes[name]
            for s in n.sources:
                if s in subset:
                    forward[s].append(name)
                    in_degree[name] += 1
        ready = sorted([name for name, d in in_degree.items() if d == 0])
        order: List[str] = []
        while ready:
            ready.sort()
            current = ready.pop(0)
            order.append(current)
            for consumer in sorted(forward[current]):
                in_degree[consumer] -= 1
                if in_degree[consumer] == 0:
                    ready.append(consumer)
        return order

    def upstream(self, node_name: str) -> List[str]:
        """All nodes transitively feeding `node_name`, in topological order."""
        if node_name not in self.nodes:
            raise BdtNotFoundError(
                f"No node named {node_name!r}. Available: "
                f"{sorted(list(self.nodes.keys()))[:20]}"
            )
        visited: Set[str] = set()
        stack = list(self.nodes[node_name].sources)
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            if cur not in self.nodes:
                # Broken reference — skip (surfaced via broken_references())
                continue
            visited.add(cur)
            stack.extend(self.nodes[cur].sources)
        # Sort only the reachable sub-DAG (+ the queried node itself), which is
        # guaranteed clean. Drop the queried node from the returned list so
        # upstream() returns just the ancestors.
        sub = visited | {node_name}
        topo = self._topo_order_subset(sub)
        return [n for n in topo if n in visited]

    def downstream(self, node_name: str) -> List[str]:
        """All nodes transitively consuming `node_name`, in topological order."""
        if node_name not in self.nodes:
            raise BdtNotFoundError(
                f"No node named {node_name!r}. Available: "
                f"{sorted(list(self.nodes.keys()))[:20]}"
            )
        # Build reverse adjacency on the fly
        consumers: Dict[str, List[str]] = {name: [] for name in self.nodes}
        for name, n in self.nodes.items():
            for s in n.sources:
                if s in consumers:
                    consumers[s].append(name)
        visited: Set[str] = set()
        stack = list(consumers[node_name])
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            stack.extend(consumers[cur])
        # Sort only the reachable sub-DAG; tolerate unrelated broken refs/cycles.
        sub = visited | {node_name}
        topo = self._topo_order_subset(sub)
        return [n for n in topo if n in visited]

    def broken_references(self) -> List[Tuple[str, str]]:
        """List of (node_name, missing_source) pairs. Empty if BDT is well-formed."""
        out = []
        for name, n in self.nodes.items():
            for s in n.sources:
                if s not in self.nodes:
                    out.append((name, s))
        return sorted(out)


# --------- CLI ---------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bdt_analyze",
        description="Explain and investigate Salesforce Data Cloud BDT JSON.",
    )
    sub = p.add_subparsers(dest="subcommand", required=True)

    # Common: --json flag + path positional + --definition selector.
    # `--definition N` picks which entry in a multi-definition Connect API
    # payload the subcommand operates on. Default 0 (the first definition,
    # matching the historical behavior).
    def _common(sp, with_definition: bool = True):
        sp.add_argument("path", help="Path to BDT JSON file")
        sp.add_argument("--json", action="store_true", dest="as_json",
                        help="Emit machine-readable JSON instead of Markdown")
        if with_definition:
            sp.add_argument(
                "--definition", type=int, default=0, dest="definition",
                help=(
                    "Which definition to operate on in a multi-definition "
                    "Connect API payload (0-indexed, default 0). Use the "
                    "'definitions' subcommand to list them."
                ),
            )

    for name, help_text in [
        ("summary", "High-level digest: counts, sources, outputs"),
        ("sources", "All graph-root nodes with their dataset details"),
        ("outputs", "All graph-sink nodes with their target details"),
        ("stages", "Topologically ordered list of nodes with action + hint"),
        ("nodes", "Every node in topo order with a one-line parameter digest"),
    ]:
        s = sub.add_parser(name, help=help_text)
        _common(s)
        if name == "nodes":
            s.add_argument("--limit", type=int, default=0,
                           help="Cap row count (0 = no limit)")

    # `node <path> <name>`
    n = sub.add_parser("node", help="Full detail of one node")
    _common(n)
    n.add_argument("node_name", help="The node name (key in `nodes` map)")

    # Lineage / tracing subcommands
    lg = sub.add_parser("lineage", help="All upstream nodes feeding a target node")
    _common(lg)
    lg.add_argument("node_name", help="The target node name")

    ft = sub.add_parser("field-trace", help="Trace a field back through the DAG")
    _common(ft)
    ft.add_argument("field_name", help="Field name (qualified or unqualified)")

    fm = sub.add_parser("formula", help="Focused formula expression + upstream field deps")
    _common(fm)
    fm.add_argument("node_name", help="A formula or computeRelative node name")

    # `definitions <path>` — list every definition in a payload. Always
    # operates on the whole set, so no --definition flag here.
    dfs = sub.add_parser("definitions",
                         help="List every definition in the payload (one row per definition)")
    _common(dfs, with_definition=False)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Returns exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        bdt = DataTransform.from_path(args.path)
    except BdtInputError as e:
        print(str(e), file=sys.stderr)
        return EXIT_BAD_INPUT

    # Select the requested definition (default 0). `definitions` subcommand
    # doesn't expose the flag — it always reports on the full list.
    definition_idx = getattr(args, "definition", 0)
    if definition_idx != 0 or args.subcommand != "definitions":
        # Only validate/select when the flag is present (it's missing on
        # `definitions`, which always walks the full list). The 0-default
        # also goes through here for consistency; `select_definition(0)` is
        # always safe given we guarantee at least one definition exists.
        try:
            bdt.select_definition(definition_idx)
        except BdtNotFoundError as e:
            # Spec: out-of-range `--definition` exits 2 with a message that
            # points the user at the `definitions` subcommand.
            msg = (
                f"Definition index {definition_idx} out of range; payload "
                f"has {bdt.definition_count} definitions "
                f"(indices 0-{bdt.definition_count - 1}). "
                f"Use 'definitions <path>' to list them."
            )
            # Preserve the underlying error type for completeness, but surface
            # the user-facing message on stderr.
            _ = e
            print(msg, file=sys.stderr)
            return EXIT_NOT_FOUND

    dispatch = {
        "summary": cmd_summary,
        "sources": cmd_sources,
        "outputs": cmd_outputs,
        "stages":  cmd_stages,
        "nodes":   cmd_nodes,
        "node":    cmd_node,
        "lineage": cmd_lineage,
        "field-trace": cmd_field_trace,
        "formula": cmd_formula,
        "definitions": cmd_definitions,
    }
    handler = dispatch.get(args.subcommand)
    if handler is None:
        print(f"Unknown subcommand: {args.subcommand!r}", file=sys.stderr)
        return EXIT_BAD_INPUT
    try:
        output = handler(bdt, args)
    except BdtNotFoundError as e:
        print(str(e), file=sys.stderr)
        return EXIT_NOT_FOUND
    except BdtInputError as e:
        print(str(e), file=sys.stderr)
        return EXIT_BAD_INPUT
    print(output)
    return EXIT_OK


# --------- Field-discovery helpers ------------------------------------------

# Matches an unquoted identifier reasonable as a field name: optional qualifier
# (e.g., "SalesOrder.ssot__Id__c") followed by the identifier itself.
_FIELD_NAME_RE = re.compile(r'\b(?:[A-Za-z_][A-Za-z0-9_]*\.)?[A-Za-z_][A-Za-z0-9_]*\b')

# Reserved identifiers we exclude when scraping a formula expression for field refs.
_SQL_RESERVED = {
    "case", "when", "then", "else", "end", "and", "or", "not", "null", "true", "false",
    "if", "is", "in", "like", "between", "cast", "as",
    # Common SFSQL functions — callers can add more if needed.
    "abs", "ceiling", "exp", "floor", "log", "max", "min", "mod", "power", "round", "sqrt", "trunc",
    "concat", "contains", "ends", "length", "lower", "ltrim", "rtrim", "substitute", "substr",
    "text", "trim", "upper", "uuid", "value", "begins",
    "adddays", "addmonths", "datediff", "datetimevalue", "datevalue", "day", "monthdiff",
    "now", "today", "weekday",
    "blankvalue", "isblank", "isnull", "nullvalue",
    "sequence", "explode",
    "row_number", "rank", "dense_rank", "lag", "lead", "first_value", "last_value",
    "nth_value", "ntile", "percent_rank", "cume_dist",
    "coalesce",
    # Type names
    "number", "text", "boolean", "date", "datetime",
}


def fields_produced(node: "Node") -> List[str]:
    """Which field names this node emits into its output stream.

    Heuristic per action type. Unknown actions fall back to [] (caller must cope).
    """
    p = node.parameters if isinstance(node.parameters, dict) else {}
    if node.action == "load":
        return list(p.get("fields") or [])
    if node.action in ("formula", "computeRelative"):
        return [f.get("name") for f in (p.get("fields") or [])
                if isinstance(f, dict) and f.get("name")]
    if node.action == "outputD360":
        return [m.get("targetField") for m in (p.get("fieldsMappings") or [])
                if isinstance(m, dict) and m.get("targetField")]
    if node.action == "schema":
        # Schema nodes rename/drop; renamed names come from slice.fields[].newProperties.name
        fs = (p.get("fields") or [])
        out = []
        for f in fs:
            if isinstance(f, dict):
                np_ = f.get("newProperties") or {}
                out.append(np_.get("name") or f.get("name"))
        return [x for x in out if x]
    if node.action == "aggregate":
        # Aggregations add their output names; groupings pass through as-is
        out = list(p.get("groupings") or [])
        for a in (p.get("aggregations") or []):
            if isinstance(a, dict) and a.get("name"):
                out.append(a["name"])
        return out
    # Default: we can't guess — caller must inspect parameters directly.
    return []


def fields_consumed(node: "Node") -> List[str]:
    """Which upstream field names this node reads.

    For pass-through nodes we return [] — callers that need "what flows through
    this node" should look at `fields_produced` on the source(s).
    """
    p = node.parameters if isinstance(node.parameters, dict) else {}
    if node.action == "load":
        return []
    if node.action == "join":
        out = list(p.get("leftKeys") or []) + list(p.get("rightKeys") or [])
        return out
    if node.action == "filter":
        return [e.get("field") for e in (p.get("filterExpressions") or [])
                if isinstance(e, dict) and e.get("field")]
    if node.action in ("formula", "computeRelative"):
        consumed = set()
        for f in (p.get("fields") or []):
            if isinstance(f, dict):
                expr = f.get("formulaExpression") or ""
                consumed.update(_scrape_field_refs(expr))
        # computeRelative also consumes partitionBy + orderBy fields
        if node.action == "computeRelative":
            consumed.update(p.get("partitionBy") or [])
            for ob in (p.get("orderBy") or []):
                if isinstance(ob, dict) and ob.get("fieldName"):
                    consumed.add(ob["fieldName"])
        return sorted(consumed)
    if node.action == "aggregate":
        out = list(p.get("groupings") or [])
        for a in (p.get("aggregations") or []):
            if isinstance(a, dict) and a.get("source"):
                out.append(a["source"])
        # Also hierarchical fields
        for f_key in ("selfField", "parentField", "percentageField"):
            v = p.get(f_key)
            if v:
                out.append(v)
        return out
    if node.action == "outputD360":
        return [m.get("sourceField") for m in (p.get("fieldsMappings") or [])
                if isinstance(m, dict) and m.get("sourceField")]
    if node.action == "schema":
        return [f.get("name") for f in (p.get("fields") or [])
                if isinstance(f, dict) and f.get("name")]
    return []


def _scrape_field_refs(expression: str) -> List[str]:
    """Pull likely field identifiers out of a SQL-ish formula expression.

    This is a heuristic: it returns identifiers that aren't reserved keywords or
    function names. Callers should still treat results as a *candidate* set, not
    a verified one. In particular, we also pick up quoted identifiers.
    """
    if not isinstance(expression, str):
        return []
    # Also capture "Quoted.Name" style identifiers
    quoted = re.findall(r'"([A-Za-z_][\w.]*)"', expression)
    bare = _FIELD_NAME_RE.findall(expression)
    candidates = set(quoted) | set(bare)
    # Drop reserved tokens (case-insensitive) and numeric-looking tokens
    out = []
    for c in candidates:
        last = c.rsplit(".", 1)[-1]
        if last.lower() in _SQL_RESERVED:
            continue
        if last.isdigit():
            continue
        out.append(c)
    # Deduplicate while preserving order
    seen = set()
    dedup = []
    for c in out:
        if c not in seen:
            seen.add(c)
            dedup.append(c)
    return dedup


def _field_specific_upstream_deps(node: "Node", field: str) -> List[str]:
    """Deps relevant to `field` specifically, not all deps the node consumes.

    `fields_consumed(node)` gives the union of every field the node reads
    across *all* of its outputs. For field-trace narration we want a much
    tighter set: only the upstream fields that feed *this one* field. This
    keeps the trace output small and focused, which matters for real BDTs
    where a single `outputD360` may have 40+ mappings or a `formula` node
    may define a dozen unrelated output fields.
    """
    p = node.parameters if isinstance(node.parameters, dict) else {}
    action = node.action
    if action in ("formula", "computeRelative"):
        out: List[str] = []
        for f in (p.get("fields") or []):
            if isinstance(f, dict) and f.get("name") == field:
                out.extend(_scrape_field_refs(f.get("formulaExpression") or ""))
                break
        if action == "computeRelative":
            out.extend(p.get("partitionBy") or [])
            for ob in (p.get("orderBy") or []):
                if isinstance(ob, dict) and ob.get("fieldName"):
                    out.append(ob["fieldName"])
        # Deduplicate, preserve order
        seen: set = set()
        dedup: List[str] = []
        for x in out:
            if x not in seen:
                seen.add(x)
                dedup.append(x)
        return dedup
    if action == "outputD360":
        for m in (p.get("fieldsMappings") or []):
            if isinstance(m, dict) and m.get("targetField") == field:
                src = m.get("sourceField")
                return [src] if src else []
        return []
    if action == "aggregate":
        # If the field is one of the aggregations, return just its source.
        for a in (p.get("aggregations") or []):
            if isinstance(a, dict) and a.get("name") == field:
                src = a.get("source")
                return [src] if src else []
        # If it's one of the groupings (pass-through), the dep is itself.
        if field in (p.get("groupings") or []):
            return [field]
        return []
    if action == "schema":
        # Renames: if this node renamed some X to `field`, the dep is X.
        for f in (p.get("fields") or []):
            if isinstance(f, dict):
                np_ = f.get("newProperties") or {}
                if np_.get("name") == field:
                    return [f.get("name")] if f.get("name") else []
        return []
    if action == "load":
        return []
    # Fallback for unknown / unhandled actions — reuse the generic consumed set
    return fields_consumed(node)


def cmd_definitions(bdt: "DataTransform", args) -> str:
    """List every definition in the payload — one row per definition.

    Safe to call on editor-export or single-definition inputs: they always
    have exactly one row. On multi-definition payloads this is the entry
    point for the SKILL.md flow that offers the user a choice.
    """
    rows = []
    for d in bdt.definitions:
        rows.append({
            "index": d.index,
            "name": d.name,
            "label": d.label,
            "version": d.version,
            "node_count": len(d.nodes),
        })

    if getattr(args, "as_json", False):
        return json.dumps(rows, indent=2)

    lines = [f"# Definitions ({len(rows)})", ""]
    lines.append("| Index | Name | Label | Version | Nodes |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['index']} | "
            f"{r['name'] or '(no name)'} | "
            f"{r['label'] or '(no label)'} | "
            f"{r['version'] or '(unknown)'} | "
            f"{r['node_count']} |"
        )
    return "\n".join(lines)


def cmd_summary(bdt: "DataTransform", args) -> str:
    """High-level digest of the BDT."""
    action_counts = Counter(n.action for n in bdt.nodes.values())
    roots = bdt.roots()
    sinks = bdt.sinks()

    if getattr(args, "as_json", False):
        data = {
            "version": bdt.version,
            "total_nodes": len(bdt.nodes),
            "action_counts": dict(action_counts),
            "sources": [_source_digest(bdt, r) for r in roots],
            "outputs": [_output_digest(bdt, s) for s in sinks],
        }
        return json.dumps(data, indent=2)

    # Markdown
    lines = []
    lines.append("# BDT Summary")
    lines.append(f"Version: {bdt.version or '(unknown)'}")
    lines.append(f"Total nodes: {len(bdt.nodes)}")
    if action_counts:
        counts_str = ", ".join(f"{a}: {c}" for a, c in action_counts.most_common())
        lines.append(f"By action: {counts_str}")
    lines.append("")
    if roots:
        lines.append(f"## Sources ({len(roots)} nodes)")
        lines.append("| Node | Label | Dataset | Type | Field count |")
        lines.append("|---|---|---|---|---|")
        for r in roots:
            d = _source_digest(bdt, r)
            lines.append(
                f"| {r} | {d['label'] or '(no label)'} | "
                f"{d['dataset_name'] or '(none)'} | "
                f"{d['dataset_type'] or '(none)'} | "
                f"{d['field_count']} |"
            )
        lines.append("")
    if sinks:
        lines.append(f"## Outputs ({len(sinks)} nodes)")
        lines.append("| Node | Label | Target | Type | Mapping count |")
        lines.append("|---|---|---|---|---|")
        for s in sinks:
            d = _output_digest(bdt, s)
            lines.append(
                f"| {s} | {d['label'] or '(no label)'} | "
                f"{d['target_name'] or '(none)'} | "
                f"{d['target_type'] or '(none)'} | "
                f"{d['mapping_count']} |"
            )
    return "\n".join(lines)


def _source_digest(bdt: "DataTransform", name: str) -> dict:
    n = bdt.nodes[name]
    ds = (n.parameters.get("dataset") or {}) if isinstance(n.parameters, dict) else {}
    fields = n.parameters.get("fields") or [] if isinstance(n.parameters, dict) else []
    return {
        "name": name,
        "label": n.ui_label,
        "dataset_name": ds.get("name") if isinstance(ds, dict) else None,
        "dataset_type": ds.get("type") if isinstance(ds, dict) else None,
        "field_count": len(fields) if isinstance(fields, list) else 0,
    }


def _output_digest(bdt: "DataTransform", name: str) -> dict:
    n = bdt.nodes[name]
    p = n.parameters if isinstance(n.parameters, dict) else {}
    mappings = p.get("fieldsMappings") or []
    return {
        "name": name,
        "label": n.ui_label,
        "target_name": p.get("name"),
        "target_type": p.get("type"),
        "write_mode": p.get("writeMode"),
        "mapping_count": len(mappings) if isinstance(mappings, list) else 0,
    }


def cmd_sources(bdt: "DataTransform", args) -> str:
    roots = bdt.roots()
    enriched = []
    for r in roots:
        n = bdt.nodes[r]
        p = n.parameters if isinstance(n.parameters, dict) else {}
        ds = p.get("dataset") or {}
        enriched.append({
            "name": r,
            "label": n.ui_label,
            "dataset_name": ds.get("name") if isinstance(ds, dict) else None,
            "dataset_type": ds.get("type") if isinstance(ds, dict) else None,
            "fields": list(p.get("fields") or []),
            "action": n.action,
        })
    if getattr(args, "as_json", False):
        return json.dumps(enriched, indent=2)
    lines = [f"# Sources ({len(enriched)} node(s))", ""]
    for e in enriched:
        lines.append(f"## {e['name']}" + (f" — {e['label']}" if e['label'] else ""))
        lines.append(f"- action: `{e['action']}`")
        lines.append(f"- dataset: `{e['dataset_name']}` ({e['dataset_type']})")
        if e['fields']:
            lines.append(f"- fields ({len(e['fields'])}): " + ", ".join(f"`{f}`" for f in e['fields']))
        else:
            lines.append("- fields: _(none declared)_")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cmd_outputs(bdt: "DataTransform", args) -> str:
    sinks = bdt.sinks()
    enriched = []
    for s in sinks:
        n = bdt.nodes[s]
        p = n.parameters if isinstance(n.parameters, dict) else {}
        mappings = p.get("fieldsMappings") or []
        enriched.append({
            "name": s,
            "label": n.ui_label,
            "action": n.action,
            "target_name": p.get("name"),
            "target_type": p.get("type"),
            "write_mode": p.get("writeMode"),
            "dedup_order": list(p.get("dedupOrder") or []),
            "mappings": [
                {
                    "source": m.get("sourceField") if isinstance(m, dict) else None,
                    "target": m.get("targetField") if isinstance(m, dict) else None,
                }
                for m in (mappings if isinstance(mappings, list) else [])
            ],
        })
    if getattr(args, "as_json", False):
        return json.dumps(enriched, indent=2)
    lines = [f"# Outputs ({len(enriched)} node(s))", ""]
    for e in enriched:
        lines.append(f"## {e['name']}" + (f" — {e['label']}" if e['label'] else ""))
        lines.append(f"- action: `{e['action']}`")
        lines.append(f"- target: `{e['target_name']}` ({e['target_type']})")
        lines.append(f"- writeMode: `{e['write_mode']}`")
        if e['dedup_order']:
            lines.append(f"- dedupOrder: {e['dedup_order']}")
        if e['mappings']:
            lines.append("")
            lines.append(f"### Field mappings ({len(e['mappings'])})")
            lines.append("| Source field | Target field |")
            lines.append("|---|---|")
            for m in e['mappings']:
                lines.append(f"| `{m['source']}` | `{m['target']}` |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# One-line purpose hint per known action. Unknown actions fall back to the raw action name.
_ACTION_HINT = {
    "load":             "Load data from a DMO or DLO",
    "filter":           "Keep rows matching filter criteria",
    "sqlFilter":        "Keep rows matching a raw SQL predicate",
    "join":             "Join two upstream streams",
    "formula":          "Add derived columns via per-row formulas",
    "computeRelative":  "Compute a window function over partitioned/ordered rows",
    "aggregate":        "Group-by aggregation",
    "extractGrains":    "Fan out rows across time grains",
    "extractTable":     "Extract a table from flattened JSON",
    "schema":           "Rename/drop/reshape columns",
    "outputD360":       "Write rows to a target DMO/DLO",
    "appendV2":         "Union rows from multiple upstream streams",
    "flatten":          "Flatten nested structure",
    "flattenJson":      "Flatten a JSON field into rows/columns",
    "split":            "Split rows across multiple outputs",
    "typeCast":         "Cast field types",
    "update":           "Update records",
    "bucket":           "Bucket field values",
    "formatDate":       "Reformat date values",
    "extension":        "Run custom extension logic",
    "extensionFunction":"Run custom extension function",
    "cdpPredict":       "Apply a prediction model",
    "jsonAggregate":    "Aggregate JSON fields",
    "save":             "Save intermediate result",
    "recommendation":   "Apply a recommendation model",
}


def cmd_stages(bdt: "DataTransform", args) -> str:
    order = bdt.topo_order()
    rows = []
    for name in order:
        n = bdt.nodes[name]
        hint = _ACTION_HINT.get(n.action, f"({n.action} — not in known catalog)")
        rows.append({
            "name": name,
            "label": n.ui_label,
            "action": n.action,
            "sources": list(n.sources),
            "hint": hint,
        })
    if getattr(args, "as_json", False):
        return json.dumps(rows, indent=2)
    lines = [f"# Stages ({len(rows)} node(s), topological order)", ""]
    for i, r in enumerate(rows, 1):
        srcs = ", ".join(f"`{s}`" for s in r["sources"]) if r["sources"] else "_(root)_"
        label_part = f" — {r['label']}" if r['label'] else ""
        lines.append(f"{i}. **{r['name']}**{label_part}  `{r['action']}`")
        lines.append(f"   - sources: {srcs}")
        lines.append(f"   - {r['hint']}")
    return "\n".join(lines)


def cmd_nodes(bdt: "DataTransform", args) -> str:
    order = bdt.topo_order()
    limit = getattr(args, "limit", 0) or 0
    limited = limit > 0 and len(order) > limit
    shown = order[:limit] if limited else order

    rows = []
    for name in shown:
        n = bdt.nodes[name]
        rows.append({
            "name": name,
            "label": n.ui_label,
            "action": n.action,
            "sources": list(n.sources),
            "param_digest": _param_digest(n),
        })

    if getattr(args, "as_json", False):
        return json.dumps({"total": len(order), "shown": len(rows), "nodes": rows}, indent=2)

    lines = [f"# Nodes ({len(order)} total)"]
    if limited:
        lines.append(f"_Output limited to {limit} of {len(order)} — re-run without --limit for full list._")
    lines.append("")
    lines.append("| Node | Label | Action | Sources | Digest |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        srcs = ", ".join(r["sources"]) if r["sources"] else "_(root)_"
        label = r["label"] or ""
        digest = r["param_digest"].replace("|", "\\|")
        lines.append(f"| {r['name']} | {label} | {r['action']} | {srcs} | {digest} |")
    return "\n".join(lines)


def _param_digest(n: "Node") -> str:
    """One-line Markdown-safe parameter summary. Never exceeds ~120 chars."""
    p = n.parameters if isinstance(n.parameters, dict) else {}
    if n.action == "load":
        ds = p.get("dataset") or {}
        ds_name = ds.get("name") if isinstance(ds, dict) else "?"
        fc = len(p.get("fields") or [])
        return f"dataset=`{ds_name}`, {fc} field(s)"
    if n.action == "join":
        return (f"type=`{p.get('joinType')}` "
                f"leftKeys={p.get('leftKeys')} rightKeys={p.get('rightKeys')} "
                f"rightQualifier=`{p.get('rightQualifier')}`")
    if n.action == "filter":
        exprs = p.get("filterExpressions") or []
        return f"{len(exprs)} expression(s), logic=`{p.get('filterBooleanLogic') or 'all AND'}`"
    if n.action in ("formula", "computeRelative"):
        fs = p.get("fields") or []
        names = ", ".join(f.get("name", "?") for f in fs if isinstance(f, dict))
        extra = ""
        if n.action == "computeRelative":
            extra = f" partitionBy={p.get('partitionBy')} orderBy={p.get('orderBy')}"
        return f"{len(fs)} output field(s): {names}{extra}"
    if n.action == "aggregate":
        aggs = p.get("aggregations") or []
        groupings = p.get("groupings") or []
        return f"{len(aggs)} aggregation(s), groupBy={groupings}"
    if n.action == "outputD360":
        mc = len(p.get("fieldsMappings") or [])
        return f"target=`{p.get('name')}` ({p.get('type')}) writeMode=`{p.get('writeMode')}` {mc} mapping(s)"
    if n.action == "schema":
        slc = p.get("slice") or {}
        return f"slice.mode=`{slc.get('mode')}` {len(slc.get('fields') or [])} field(s)"
    # Fallback: show param keys only
    keys = list(p.keys())[:5]
    return f"parameters keys: {keys}"


def cmd_node(bdt: "DataTransform", args) -> str:
    name = args.node_name
    if name not in bdt.nodes:
        available = sorted(bdt.nodes.keys())[:20]
        raise BdtNotFoundError(
            f"No node named {name!r}. Available (first 20): {available}"
        )
    n = bdt.nodes[name]
    # Compute consumers (nodes that list this one as a source)
    consumers = [m for m, other in bdt.nodes.items() if name in other.sources]

    if getattr(args, "as_json", False):
        return json.dumps({
            "name": n.name,
            "label": n.ui_label,
            "description": n.ui_description,
            "action": n.action,
            "sources": n.sources,
            "consumers": consumers,
            "parameters": n.parameters,
            "schema": n.schema,
        }, indent=2)

    lines = [f"# {n.name}" + (f" — {n.ui_label}" if n.ui_label else "")]
    if n.ui_description:
        lines.append(f"> {n.ui_description}")
    lines.append("")
    lines.append(f"- **action:** `{n.action}`")
    lines.append(f"- **hint:** {_ACTION_HINT.get(n.action, '(not in known catalog)')}")
    lines.append(f"- **sources:** {n.sources or '_(root)_'}")
    lines.append(f"- **direct consumers:** {consumers or '_(sink — no downstream)_'}")
    lines.append("")
    lines.append("## Parameters")
    lines.append("```json")
    lines.append(json.dumps(n.parameters, indent=2, default=str))
    lines.append("```")
    if n.schema:
        lines.append("")
        lines.append("## Schema block")
        lines.append("```json")
        lines.append(json.dumps(n.schema, indent=2, default=str))
        lines.append("```")
    return "\n".join(lines)


def cmd_lineage(bdt: "DataTransform", args) -> str:
    target = args.node_name
    if target not in bdt.nodes:
        available = sorted(bdt.nodes.keys())[:20]
        raise BdtNotFoundError(
            f"No node named {target!r}. Available (first 20): {available}"
        )
    upstream_names = bdt.upstream(target)  # topo-ordered

    rows = []
    for name in upstream_names:
        n = bdt.nodes[name]
        rows.append({
            "name": name,
            "action": n.action,
            "label": n.ui_label,
            "sources": list(n.sources),
        })

    if getattr(args, "as_json", False):
        return json.dumps({"target": target, "upstream": rows}, indent=2)

    lines = [f"# Lineage of {target}"]
    t = bdt.nodes[target]
    if t.ui_label:
        lines.append(f"_{t.ui_label}_")
    lines.append("")
    if not upstream_names:
        lines.append(f"`{target}` is a graph root (no upstream).")
        return "\n".join(lines)
    lines.append(f"{len(upstream_names)} upstream node(s), topological order:")
    lines.append("")
    for r in rows:
        arrow = "  ← " if r["sources"] else "    "
        label_part = f" — {r['label']}" if r['label'] else ""
        lines.append(f"{arrow}**{r['name']}** `{r['action']}`{label_part}")
        if r['sources']:
            srcs = ", ".join(f"`{s}`" for s in r['sources'])
            lines.append(f"     (fed by {srcs})")
    lines.append("")
    lines.append(f"  → **{target}** `{t.action}`" + (f" — {t.ui_label}" if t.ui_label else ""))
    return "\n".join(lines)


def cmd_field_trace(bdt: "DataTransform", args) -> str:
    field = args.field_name
    # Cache topo order once — `bdt.topo_order()` walks the whole graph.
    topo = bdt.topo_order()
    # 1. Find all nodes that "produce" this field (per fields_produced heuristic).
    definers = []
    for name in topo:
        n = bdt.nodes[name]
        produced = fields_produced(n)
        if field in produced:
            definers.append(n)

    # 2. If nothing matched, also try matching the unqualified part (drop any "Qualifier." prefix)
    if not definers:
        unq = field.rsplit(".", 1)[-1]
        for name in topo:
            n = bdt.nodes[name]
            produced = fields_produced(n)
            if unq in produced:
                definers.append(n)
                field = unq  # report with the unqualified name we actually matched

    if not definers:
        available_sample = []
        for name in list(bdt.nodes.keys())[:10]:
            available_sample.extend(fields_produced(bdt.nodes[name]))
        raise BdtNotFoundError(
            f"Field {args.field_name!r} is not defined by any node in this BDT. "
            f"Sample of visible field names (from the first 10 nodes): "
            f"{sorted(set(available_sample))[:20]}"
        )

    # 3. For each definer, compute: (a) the formula or mapping that defines it, if any;
    #    (b) its direct upstream field dependencies (`fields_consumed`).
    def _definition_of(n: "Node", fname: str) -> dict:
        p = n.parameters if isinstance(n.parameters, dict) else {}
        detail = {"kind": n.action}
        if n.action in ("formula", "computeRelative"):
            for f in (p.get("fields") or []):
                if isinstance(f, dict) and f.get("name") == fname:
                    detail["formulaExpression"] = f.get("formulaExpression")
                    detail["type"] = f.get("type")
                    detail["label"] = f.get("label")
                    break
        elif n.action == "outputD360":
            for m in (p.get("fieldsMappings") or []):
                if isinstance(m, dict) and m.get("targetField") == fname:
                    detail["sourceField"] = m.get("sourceField")
                    break
        elif n.action == "load":
            ds = p.get("dataset") or {}
            detail["dataset"] = {"name": ds.get("name"), "type": ds.get("type")}
        elif n.action == "aggregate":
            for a in (p.get("aggregations") or []):
                if isinstance(a, dict) and a.get("name") == fname:
                    detail["aggregation"] = {
                        "action": a.get("action"),
                        "source": a.get("source"),
                    }
                    break
        elif n.action == "schema":
            for f in (p.get("fields") or []):
                if isinstance(f, dict):
                    np_ = f.get("newProperties") or {}
                    if (np_.get("name") or f.get("name")) == fname:
                        detail["renamed_from"] = f.get("name")
                        detail["renamed_to"] = np_.get("name")
                        break
        return detail

    result = []
    for n in definers:
        entry = {
            "node": n.name,
            "label": n.ui_label,
            "action": n.action,
            "definition": _definition_of(n, field),
            # Narrowed to deps of *this specific field*, not every field the
            # node consumes. For output/formula/aggregate nodes with many
            # unrelated output fields this dramatically reduces trace size
            # and noise. The broader node-level context is still available
            # via `upstream_chain` below.
            "upstream_deps": _field_specific_upstream_deps(n, field),
            "sources": list(n.sources),
        }
        result.append(entry)

    # Upstream node chain for the first definer (for narration convenience)
    chain = []
    if definers:
        chain = bdt.upstream(definers[0].name) + [definers[0].name]

    if getattr(args, "as_json", False):
        return json.dumps({
            "field": field,
            "definitions": result,
            "upstream_chain": chain,
        }, indent=2)

    lines = [f"# Field trace: `{field}`"]
    if len(definers) > 1:
        lines.append(f"> Field is defined in {len(definers)} places (first in topological order listed first).")
    lines.append("")
    for i, entry in enumerate(result, 1):
        header = f"## {i}. Defined by {entry['node']}"
        if entry['label']:
            header += f" — {entry['label']}"
        lines.append(header)
        lines.append(f"- action: `{entry['action']}`")
        d = entry['definition']
        if d.get("formulaExpression"):
            lines.append(f"- formula: `{d['formulaExpression']}`")
            if d.get("type"):
                lines.append(f"- type: `{d['type']}`")
        if d.get("sourceField"):
            lines.append(f"- sourced from: `{d['sourceField']}`")
        if d.get("dataset"):
            lines.append(f"- loaded from: `{d['dataset']['name']}` ({d['dataset']['type']})")
        if d.get("aggregation"):
            a = d['aggregation']
            lines.append(f"- aggregation: `{a['action']}` over `{a['source']}`")
        if d.get("renamed_from"):
            lines.append(f"- renamed: `{d['renamed_from']}` → `{d['renamed_to']}`")
        if entry['upstream_deps']:
            lines.append(f"- upstream field deps: {entry['upstream_deps']}")
        lines.append(f"- upstream nodes: {entry['sources'] or '_(root)_'}")
        lines.append("")
    if chain:
        lines.append("## Upstream node chain")
        lines.append(" → ".join(f"`{c}`" for c in chain))
    return "\n".join(lines)


def cmd_formula(bdt: "DataTransform", args) -> str:
    name = args.node_name
    if name not in bdt.nodes:
        raise BdtNotFoundError(
            f"No node named {name!r}. Available (first 20): "
            f"{sorted(bdt.nodes.keys())[:20]}"
        )
    n = bdt.nodes[name]
    if n.action not in ("formula", "computeRelative"):
        raise BdtInputError(
            f"Node {name!r} has action {n.action!r}; `formula` subcommand "
            f"only applies to `formula` and `computeRelative` nodes. "
            f"Use `node {name}` instead."
        )
    p = n.parameters if isinstance(n.parameters, dict) else {}
    fields_out = p.get("fields") or []
    consumed = fields_consumed(n)

    # For each consumed field, find the node that defines it (if any) — give
    # the LLM ready context for I2-style reasoning. Hoist `bdt.upstream(name)`
    # out of the loop — it's a pure function of `name` and walks the graph.
    # Pre-compute fields_produced for every upstream node once (was O(consumed × upstream))
    upstream_names = bdt.upstream(name)
    upstream_fields_map = {up_name: fields_produced(bdt.nodes[up_name]) for up_name in upstream_names}
    upstream_defs = {}
    for f in consumed:
        matches = []
        for up_name in upstream_names:
            up = bdt.nodes[up_name]
            prod = upstream_fields_map[up_name]
            if f in prod or f.rsplit(".", 1)[-1] in prod:
                matches.append({
                    "node": up_name,
                    "action": up.action,
                    "label": up.ui_label,
                })
        if matches:
            upstream_defs[f] = matches[-1]

    payload = {
        "node": name,
        "label": n.ui_label,
        "action": n.action,
        "formula_fields": [
            {
                "name": f.get("name"),
                "label": f.get("label"),
                "type": f.get("type"),
                "formulaExpression": f.get("formulaExpression"),
            }
            for f in fields_out if isinstance(f, dict)
        ],
        "consumed_fields": consumed,
        "upstream_field_definitions": upstream_defs,
    }
    if n.action == "computeRelative":
        payload["partitionBy"] = list(p.get("partitionBy") or [])
        payload["orderBy"] = p.get("orderBy") or []

    if getattr(args, "as_json", False):
        return json.dumps(payload, indent=2)

    lines = [f"# Formula extract: {name}" + (f" — {n.ui_label}" if n.ui_label else "")]
    lines.append(f"- action: `{n.action}`")
    if n.action == "computeRelative":
        lines.append(f"- partitionBy: {payload['partitionBy']}")
        lines.append(f"- orderBy: {payload['orderBy']}")
    lines.append("")
    lines.append("## Output fields")
    for f in payload["formula_fields"]:
        lines.append(f"### `{f['name']}`" + (f" _{f['label']}_" if f['label'] else ""))
        lines.append(f"- type: `{f['type']}`")
        lines.append(f"- expression: `{f['formulaExpression']}`")
        lines.append("")
    lines.append("## Upstream field dependencies")
    if not consumed:
        lines.append("_(none detected — expression may reference only literals)_")
    else:
        for f in consumed:
            defn = upstream_defs.get(f)
            if defn:
                label = f" _{defn['label']}_" if defn.get('label') else ""
                lines.append(f"- `{f}` ← **{defn['node']}** (`{defn['action']}`){label}")
            else:
                lines.append(f"- `{f}` ← (no upstream definition found — may be a literal or a passthrough)")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
