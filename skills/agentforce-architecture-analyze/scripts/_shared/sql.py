"""SQL-escaping helpers for SOQL string literals.
"""
from __future__ import annotations


def _escape_sql_literal(s: str) -> str:
    """Double single quotes per SOQL escaping rule. Handles O'Brien →
    O''Brien, `'; DROP --` → `''; DROP --` (still harmless because it's
    wrapped in surrounding single quotes)."""
    return s.replace("'", "''")
