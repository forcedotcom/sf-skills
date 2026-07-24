#!/bin/bash
# Shared library for Sales Agent authoring bundle publish and activation
#
# Functions:
#   publish_and_activate_agent <org-alias> <on-error-behavior> [output-style]
#
# Parameters:
#   org-alias: Salesforce org alias
#   on-error-behavior: "exit" (hard fail on error) or "return" (return non-zero)
#   output-style: "plain" (default, plain echo) or "structured" (log_pass/log_info style)
#
# Returns:
#   0 on success
#   1 on failure
#
# Environment:
#   SCRIPT_DIR must be set (parent script's directory)

# Source agent-detection helpers (pm_bot_latest_version, etc.)
# Use a local resolution that doesn't depend on the caller's SCRIPT_DIR.
# shellcheck source=./agent-detection.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/agent-detection.sh"

publish_and_activate_agent() {
  local ORG_ALIAS="$1"
  local ON_ERROR="${2:-exit}"
  local OUTPUT_STYLE="${3:-plain}"

  # Clear exported state from any prior call to prevent stale values on failure
  unset AGENT_VERSION
  unset AGENT_API_NAME

  local AGENT_BUNDLE="$SCRIPT_DIR/../assets/sales_management_agent.agent"
  local BUNDLE_META="$SCRIPT_DIR/../assets/sales_management_agent.bundle-meta.xml"

  # Output helper functions based on style
  local msg_header msg_pass msg_error msg_info
  if [[ "$OUTPUT_STYLE" == "structured" ]]; then
    msg_header() { log_info "$1"; }
    msg_pass() { log_pass "$1"; }
    msg_error() { echo "  ERROR: $1"; }
    msg_info() { echo "    $1"; }
  else
    msg_header() { echo "=== $1 ==="; }
    msg_pass() { echo "  ✓ $1"; }
    msg_error() { echo "  ERROR: $1"; }
    msg_info() { echo "  $1"; }
  fi

  # Check for bundle assets
  if [[ ! -f "$AGENT_BUNDLE" || ! -f "$BUNDLE_META" ]]; then
    msg_error "Agent bundle assets not found at: $AGENT_BUNDLE"
    if [[ "$ON_ERROR" == "exit" ]]; then
      echo ""
      echo "SETUP FAILED: A Pipeline Management BotDefinition is REQUIRED for user interaction."
      exit 1
    fi
    return 1
  fi

  msg_header "Creating Sales Agent via authoring bundle"

  # Create temp directory for bundle deployment
  local TEMP_DIR
  TEMP_DIR=$(mktemp -d -t sales-agent-bundle.XXXXXX)
  # Use EXIT trap so it fires even on explicit exit calls
  trap 'rm -rf "$TEMP_DIR"' EXIT

  # Create sfdx-project.json in temp dir
  cat > "$TEMP_DIR/sfdx-project.json" << 'SFDX'
{"packageDirectories": [{"path": "force-app", "default": true}], "sourceApiVersion": "67.0"}
SFDX

  # Copy authoring bundle to temp deployment directory
  mkdir -p "$TEMP_DIR/force-app/main/default/aiAuthoringBundles/SalesAgent"
  if ! cp "$AGENT_BUNDLE" "$TEMP_DIR/force-app/main/default/aiAuthoringBundles/SalesAgent/SalesAgent.agent"; then
    msg_error "Failed to stage bundle agent file"
    rm -rf "$TEMP_DIR"
    trap - EXIT
    if [[ "$ON_ERROR" == "exit" ]]; then
      echo ""
      echo "SETUP FAILED: A Pipeline Management BotDefinition is REQUIRED for user interaction."
      exit 1
    fi
    return 1
  fi
  if ! cp "$BUNDLE_META" "$TEMP_DIR/force-app/main/default/aiAuthoringBundles/SalesAgent/SalesAgent.bundle-meta.xml"; then
    msg_error "Failed to stage bundle metadata file"
    rm -rf "$TEMP_DIR"
    trap - EXIT
    if [[ "$ON_ERROR" == "exit" ]]; then
      echo ""
      echo "SETUP FAILED: A Pipeline Management BotDefinition is REQUIRED for user interaction."
      exit 1
    fi
    return 1
  fi

  # Publish authoring bundle from temp directory
  msg_info "Publishing Sales Agent authoring bundle..."
  local PUBLISH_RESULT
  PUBLISH_RESULT=$(cd "$TEMP_DIR" && sf agent publish authoring-bundle --json --api-name SalesAgent --target-org "$ORG_ALIAS" 2>/dev/null || echo '{"status":1}')

  if ! echo "$PUBLISH_RESULT" | jq -e '.status == 0' >/dev/null 2>&1; then
    local PUBLISH_ERR
    PUBLISH_ERR=$(echo "$PUBLISH_RESULT" | jq -r '.message // .result.message // .result.errors[0].message // "unknown"' 2>/dev/null || echo "unknown")
    msg_error "Authoring bundle publish failed: $PUBLISH_ERR"
    rm -rf "$TEMP_DIR"
    trap - EXIT
    if [[ "$ON_ERROR" == "exit" ]]; then
      echo ""
      echo "SETUP FAILED: A Pipeline Management BotDefinition is REQUIRED for user interaction."
      exit 1
    fi
    return 1
  fi

  msg_pass "Sales Agent published successfully"

  # Query for the latest BotVersion with retry (async provisioning).
  # Match the bot by AgentTemplate (the same field the scheduled flow uses),
  # not by hardcoded DeveloperName — the bundle may publish under a different
  # local name in some orgs.
  msg_info "Querying for latest version..."
  local LATEST_VERSION=""
  for attempt in {1..3}; do
    LATEST_VERSION=$(pm_bot_latest_version "$ORG_ALIAS")

    if [[ -n "$LATEST_VERSION" ]]; then
      break
    fi

    if [[ $attempt -lt 3 ]]; then
      echo "    Version not yet available, retrying in 5s... (attempt $attempt/3)"
      sleep 5
    fi
  done

  if [[ -z "$LATEST_VERSION" ]]; then
    msg_error "Could not query BotVersion after publish. BotDefinition may still be provisioning. Wait 30s and check Setup → Agents."
    rm -rf "$TEMP_DIR"
    trap - EXIT
    if [[ "$ON_ERROR" == "exit" ]]; then
      echo ""
      echo "SETUP FAILED: A Pipeline Management BotDefinition is REQUIRED for user interaction."
      exit 1
    fi
    return 1
  fi

  # Resolve the actual published DeveloperName from AgentTemplate so we
  # activate whatever name the bundle landed under (defaults to "SalesAgent"
  # but the org may already have an upgraded NGA bot with a different name).
  AGENT_API_NAME=$(pm_bot_developer_name "$ORG_ALIAS")
  if [[ -z "$AGENT_API_NAME" ]]; then
    AGENT_API_NAME="SalesAgent"
  fi

  # Activate the agent with dynamic version
  msg_info "Activating $AGENT_API_NAME version $LATEST_VERSION..."
  local ACTIVATE_RESULT
  ACTIVATE_RESULT=$(sf agent activate --api-name "$AGENT_API_NAME" --version "$LATEST_VERSION" --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')

  if ! echo "$ACTIVATE_RESULT" | jq -e '.status == 0' >/dev/null 2>&1; then
    local ACTIVATE_ERR
    ACTIVATE_ERR=$(echo "$ACTIVATE_RESULT" | jq -r '.message // .result.message // .result.errors[0].message // "unknown"' 2>/dev/null || echo "unknown")
    msg_error "Agent activation failed: $ACTIVATE_ERR. The agent was published but activation failed."
    rm -rf "$TEMP_DIR"
    trap - EXIT
    if [[ "$ON_ERROR" == "exit" ]]; then
      echo ""
      echo "SETUP FAILED: A Pipeline Management BotDefinition is REQUIRED for user interaction."
      exit 1
    fi
    return 1
  fi

  msg_pass "$AGENT_API_NAME activated successfully (version $LATEST_VERSION)"

  # Export version and resolved api-name for caller to use
  export AGENT_VERSION="$LATEST_VERSION"
  export AGENT_API_NAME

  # Clean up temp directory before returning (EXIT trap only fires on exit, not return)
  rm -rf "$TEMP_DIR"
  trap - EXIT  # Remove the trap since we've already cleaned up

  return 0
}
