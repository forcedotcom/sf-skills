#!/usr/bin/env bash
# Read-only prerequisite check for Data 360 code extension development.
# Usage: bash check_env.sh [PROJECT_DIR] [ORG] [system|venv]
#   Pass "" to let the script resolve a value (see SKILL.md Phase 0a):
#   PROJECT_DIR: argument > $D360_PROJECT_DIR > /home/codebuilder/dx-project (Code Builder) > current folder
#   ORG:         argument > $D360_TARGET_ORG > CLI default org if Connected > the only Connected org
# Prints the resolved values, the org's API version, the Python mode, and the <PY_ENV>
# line to start every shell block with, then checks everything else. Printed values are
# literal (no $(...)), so agents can copy them into commands that need no extra approval.
# Changes nothing. Exits 1 if any required check fails (including an unresolved org).

PROJECT_DIR="${1:-}"
ORG_ALIAS="${2:-}"
MODE="${3:-}"

fail=0
ok()   { printf '✅ %s\n' "$1"; }
bad()  { printf '❌ %s\n   → %s\n' "$1" "$2"; fail=1; }
warn() { printf '⚠️  %s\n   → %s\n' "$1" "$2"; }
pyver() { "$1" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null; }
ext_managed() { "$1" -c 'import os, sys, sysconfig; sys.exit(0 if os.path.exists(os.path.join(sysconfig.get_path("stdlib"), "EXTERNALLY-MANAGED")) else 1)' 2>/dev/null; }
org_status() { sf org display --target-org "$1" --json 2>/dev/null | jq -r '.result.connectedStatus // empty' 2>/dev/null; }

# ---- sf must be able to run here --------------------------------------------
# Agent sandboxes (for example Codex) can block sf from writing ~/.sf, so every sf
# call crashes with EPERM. The plugin and org checks would then report false ❌s.
if command -v sf >/dev/null 2>&1 && [ -z "$(sf --version 2>/dev/null)" ]; then
  bad "sf CLI is installed but can't run in this shell (usually a sandbox blocking writes to ~/.sf)" \
      "rerun this check with permission to run outside the sandbox; the plugin, org and other results can't be trusted until then"
  exit 1
fi

# ---- Resolve PROJECT_DIR ----------------------------------------------------
if [ -n "$PROJECT_DIR" ]; then         PROJECT_SRC="argument"
elif [ -n "$D360_PROJECT_DIR" ]; then  PROJECT_DIR="$D360_PROJECT_DIR"; PROJECT_SRC="D360_PROJECT_DIR"
elif [ -d /home/codebuilder/dx-project ]; then PROJECT_DIR=/home/codebuilder/dx-project; PROJECT_SRC="Code Builder workspace"
else                                   PROJECT_DIR="$PWD"; PROJECT_SRC="current folder"
fi
PROJECT_DIR="${PROJECT_DIR%/}"

# ---- Resolve the org (alias, or username if it has no alias) ----------------
ORG_CANDIDATES=""
if [ -n "$ORG_ALIAS" ]; then          ORG_SRC="argument"
elif [ -n "$D360_TARGET_ORG" ]; then  ORG_ALIAS="$D360_TARGET_ORG"; ORG_SRC="D360_TARGET_ORG"
elif command -v sf >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
  default=$(sf config get target-org --json 2>/dev/null | jq -r '.result[0].value // empty')
  if [ -n "$default" ] && [ "$(org_status "$default")" = "Connected" ]; then
    ORG_ALIAS="$default"; ORG_SRC="CLI default org, Connected"
  else
    # Every Connected org, once, as "alias-or-username".
    connected=$(sf org list --json 2>/dev/null | jq -r '[.result[]?[]? | select(.connectedStatus == "Connected")]
      | unique_by(.username) | .[] | (.alias // .username)')
    count=$(printf '%s' "$connected" | grep -c .)
    if [ "$count" = 1 ]; then ORG_ALIAS="$connected"; ORG_SRC="only Connected org"
    elif [ "$count" -gt 1 ]; then ORG_CANDIDATES=$(printf '%s' "$connected" | paste -sd, - | sed 's/,/, /g')
    fi
  fi
fi

echo "PROJECT_DIR=$PROJECT_DIR   ($PROJECT_SRC)"
if [ -n "$ORG_ALIAS" ]; then
  echo "ORG_ALIAS=$ORG_ALIAS   ($ORG_SRC)"
elif [ -n "$ORG_CANDIDATES" ]; then
  echo "ORG_ALIAS=   (ambiguous: several Connected orgs and no Connected default: $ORG_CANDIDATES)"
else
  echo "ORG_ALIAS=   (no Connected org found)"
fi

# ---- Python mode ------------------------------------------------------------
if [ -z "$MODE" ]; then
  if [ -d "$PROJECT_DIR/.venv" ]; then
    MODE=venv          # an existing venv always wins
  elif [ "$(pyver python3)" = "3.11" ] && python3 -m pip --version >/dev/null 2>&1 && ! ext_managed python3; then
    MODE=system
  elif command -v python3.11 >/dev/null 2>&1; then
    MODE=venv          # 3.11 exists but is not the default python3 (typical macOS)
  else
    MODE=none
  fi
fi

case "$MODE" in
  venv)   PY_ENV="source $(printf '%q' "$PROJECT_DIR/.venv/bin/activate")" ;;
  system) USER_BIN="$(python3 -m site --user-base 2>/dev/null)/bin"
          PY_ENV="export PATH=\"$USER_BIN:\$PATH\"" ;;
  *)      PY_ENV="" ;;
esac
echo "MODE=$MODE"
[ -n "$PY_ENV" ] && echo "PY_ENV=$PY_ENV"
echo

# ---- sf CLI and plugin ------------------------------------------------------
if command -v sf >/dev/null 2>&1; then
  ok "sf CLI: $(sf --version 2>/dev/null | head -1)"
  plugin=$(sf plugins 2>/dev/null | grep -i 'data-code-extension')
  [ -n "$plugin" ] && ok "plugin: $plugin" \
    || bad "data-code-extension plugin missing" "sf plugins install @salesforce/plugin-data-code-extension"
else
  bad "sf CLI missing" "environment-setup.md §2"
fi

# ---- Python -----------------------------------------------------------------
case "$MODE" in
  none)
    bad "no Python 3.11 found (python3 is $(pyver python3 || echo missing))" "environment-setup.md §3"
    ;;
  venv)
    if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
      # Apply the mode exactly as the agent will, then check what the plugin sees.
      . "$PROJECT_DIR/.venv/bin/activate"
      v=$(pyver python3)
      [ "$v" = "3.11" ] && ok "venv python3 is 3.11 ($(command -v python3))" \
        || bad "venv python3 is ${v:-missing}, must be 3.11" "recreate: rm -rf .venv && python3.11 -m venv .venv"
      python3 -m pip --version >/dev/null 2>&1 \
        || bad "venv has no pip (created with uv venv?)" "recreate with: python3.11 -m venv .venv"
      if [ -n "$PYSPARK_PYTHON" ] && [ "$PYSPARK_PYTHON" = "$PYSPARK_DRIVER_PYTHON" ]; then
        ok "PYSPARK_PYTHON=$PYSPARK_PYTHON"
      else
        bad "PySpark hook missing from .venv/bin/activate (run fails with PYTHON_VERSION_MISMATCH)" "bash <SKILL_DIR>/scripts/venv_hook.sh $PROJECT_DIR"
      fi
    else
      bad "no venv at $PROJECT_DIR/.venv" "python3.11 -m venv .venv  (not uv venv), then scripts/venv_hook.sh"
    fi
    ;;
  system)
    eval "$PY_ENV"
    v=$(pyver python3)
    [ "$v" = "3.11" ] && ok "python3 is 3.11 ($(python3 --version 2>&1), $(command -v python3))" \
      || bad "python3 is ${v:-missing}, system mode needs 3.11" "use venv mode (environment-setup.md §3b)"
    python3 -m pip --version >/dev/null 2>&1 && ok "python3 -m pip available" \
      || bad "python3 has no pip" "environment-setup.md §3a (install pip for this Python)"
    ext_managed python3 \
      && bad "system Python is externally managed (PEP 668); pip install will be refused" "use venv mode (environment-setup.md §3b)"
    # The plugin tries pip3 first; a pip3 from another Python can report the SDK as installed
    # while python3 can't import it.
    if command -v pip3 >/dev/null 2>&1; then
      case "$(pip3 --version 2>/dev/null)" in
        *'python 3.11'*) ok "pip3 belongs to Python 3.11" ;;
        *) warn "pip3 belongs to another Python: $(pip3 --version 2>/dev/null)" "always install with python3 -m pip" ;;
      esac
    fi
    ;;
esac

# ---- SDK and pipreqs (as the plugin will see them) --------------------------
if [ "$MODE" != none ] && command -v python3 >/dev/null 2>&1; then
  sdk=$(python3 -c 'import importlib.metadata as m; print(m.version("salesforce-data-customcode"))' 2>/dev/null)
  if [ -n "$sdk" ] && python3 -c 'import datacustomcode' 2>/dev/null; then
    ok "salesforce-data-customcode $sdk (importable by python3)"
  else
    [ "$MODE" = system ] && cmd="python3 -m pip install --user --upgrade salesforce-data-customcode pipreqs" \
                         || cmd="python3 -m pip install --upgrade salesforce-data-customcode pipreqs"
    bad "SDK not importable by python3" "$cmd"
  fi
  command -v pipreqs >/dev/null 2>&1 && ok "pipreqs on PATH ($(command -v pipreqs))" \
    || bad "pipreqs not on PATH (scan fails with PipreqsScanError)" "$PY_ENV && python3 -m pip install $( [ "$MODE" = system ] && echo '--user ')pipreqs"
fi

# ---- Java -------------------------------------------------------------------
if command -v java >/dev/null 2>&1 || [ -n "$JAVA_HOME" ]; then
  jv=$("${JAVA_HOME:+$JAVA_HOME/bin/}java" -version 2>&1 | head -1)
  case "$jv" in
    *'"17'*|*'"11'*|*' 17'*|*' 11'*) ok "Java: $jv" ;;
    *'"21'*|*' 21'*) warn "Java: $jv" "works for SDK reads, transforms and local run; df.toPandas() with Arrow fails on Java 21 (PySpark 3.5). Use JDK 17 if your code calls toPandas or pandas UDFs" ;;
    *'Unable to locate'*|'') bad "no JDK found" "environment-setup.md §1 Java" ;;
    *) warn "Java: $jv" "JDK 17 recommended for PySpark 3.5 (11 also works)" ;;
  esac
else
  bad "no Java found" "environment-setup.md §1 Java"
fi

# ---- Docker (deploy only) ---------------------------------------------------
if docker info --format '{{.ServerVersion}}' >/dev/null 2>&1; then
  ok "Docker running"
else
  warn "Docker not running or not installed" "needed for deploy only; without it you can develop and run here and deploy elsewhere"
fi

# ---- jq ---------------------------------------------------------------------
command -v jq >/dev/null 2>&1 && ok "jq installed" || warn "jq missing" "install jq"

# ---- Org connection ---------------------------------------------------------
if [ -n "$ORG_ALIAS" ] && command -v sf >/dev/null 2>&1; then
  org_json=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null)
  status=$(printf '%s' "$org_json" | jq -r '.result.connectedStatus // empty' 2>/dev/null)
  api=$(printf '%s' "$org_json" | jq -r '.result.apiVersion // empty' 2>/dev/null)
  [ "$status" = "Connected" ] && { ok "org $ORG_ALIAS: Connected"; echo "API_VERSION=$api"; } \
    || bad "org $ORG_ALIAS: ${status:-not found}" "sf org login web --instance-url <ORG_URL> --alias $ORG_ALIAS  (user must log in)"
elif [ -n "$ORG_CANDIDATES" ]; then
  bad "org not resolved: several Connected orgs ($ORG_CANDIDATES)" "ask the user which one, then pass it as the second argument"
else
  bad "no Connected org" "sf org login web --instance-url <ORG_URL> --alias <ORG_ALIAS>  (user must log in)"
fi

echo
echo "Manual check (no API): Data Cloud Setup → Feature Manager → 'Code Extension' must be ON."
exit $fail
