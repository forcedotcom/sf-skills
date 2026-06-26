"""BFS graph builder — walks the cross-type reference graph.

 (visited keys = (kind, canonical_name) tuples) +  (MAX_DEPTH=5 cap
→ _partial + PARTIAL_OK) land in Batches 2 and 3.
"""
from __future__ import annotations


def build_fetch_graph() -> dict:
    """TODO  + BFS with per-kind visited tuples, cycle-safe,
    MAX_DEPTH cap surfaces as _partial=true in the tree.
    """
    raise NotImplementedError("build_fetch_graph implements in P0 Batches 2+3")
