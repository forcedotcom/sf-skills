#!/usr/bin/env bash
# Venv mode only. Pins PySpark to the project venv's Python by adding two exports
# to <PROJECT_DIR>/.venv/bin/activate. Safe to rerun; adds the lines once.
# Usage: bash venv_hook.sh <PROJECT_DIR>
# Rerun after recreating the venv (a new venv regenerates activate).

PROJECT_DIR="${1:?usage: venv_hook.sh <PROJECT_DIR>}"
ACTIVATE="$PROJECT_DIR/.venv/bin/activate"

[ -f "$ACTIVATE" ] || { echo "❌ $ACTIVATE not found; create the venv first: python3.11 -m venv .venv"; exit 1; }

if grep -q 'PYSPARK_PYTHON' "$ACTIVATE"; then
  echo "✅ PySpark hook already present in $ACTIVATE, skipping"
else
  cat >> "$ACTIVATE" <<'EOF'

# Data 360 code extension: Spark driver and workers must use this venv's Python 3.11
export PYSPARK_PYTHON="$VIRTUAL_ENV/bin/python"
export PYSPARK_DRIVER_PYTHON="$VIRTUAL_ENV/bin/python"
EOF
  echo "✅ PySpark hook added to $ACTIVATE"
fi
