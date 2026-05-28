"""Canonical SQL-escaping helpers for investigating-agentforce-d360.

Single source of truth for DC-SQL string-literal escaping. Behavioral contract
is fixed — do not change the escape strategy without updating every caller and
its tests.
"""
from __future__ import annotations


def _escape_sql_literal(s: str) -> str:
    """Double single quotes per DC SQL escaping rule. Handles O'Brien →
    O''Brien, `'; DROP --` → `''; DROP --` (still harmless because it's
    wrapped in surrounding single quotes)."""
    return s.replace("'", "''")
