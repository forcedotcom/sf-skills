#!/bin/bash
# Shared library for Pipeline Management agent detection.
#
# The Pipeline Management scheduled flow (sales_pipe_mgmt__OppSuggGenSchFlow)
# finds the Sales Agent bot by querying BotDefinition.AgentTemplate, NOT by
# a hardcoded DeveloperName. Setup/verify scripts must match the same logic
# so they detect the agent regardless of what local name (SalesAgent,
# Sale_Agent, etc.) it was published with.
#
# The product currently supports two agent templates:
#   - SalesMgmt__SalesAgent      (legacy)
#   - SalesMgmt__NGASalesAgent   (upgraded NGA, used by our authoring bundle)
#
# Both flows (Test.flow, Process_Field_Update_Suggestions.flow) check
# AgentTemplate. We do the same here.

# Comma-separated AgentTemplate API names that identify a Pipeline Management
# Sales Agent. Quoted for SOQL IN(...) usage.
PM_AGENT_TEMPLATES_SOQL="'SalesMgmt__NGASalesAgent','SalesMgmt__SalesAgent'"

# Activation state lives on BotVersion.Status (Active|Inactive), not on
# BotDefinition (which only has IsDeleted).
#
# DEPRECATED: This correlated subquery hangs 60+ seconds on some orgs and must
# NOT be embedded in detection queries (removed in de77d520). Retained only so
# any lingering external caller still resolves the symbol; callers that need to
# know whether a bot is active should run a SEPARATE flat query on BotVersion
# (e.g. SELECT COUNT() FROM BotVersion WHERE BotDefinitionId='...' AND
# Status='Active') instead of splicing this into a BotDefinition WHERE clause.
PM_ACTIVE_BOT_FILTER="Id IN (SELECT BotDefinitionId FROM BotVersion WHERE Status = 'Active')"

# Print the DeveloperName of the Pipeline Management BotDefinition (if any),
# detected by AgentTemplate. Empty string when not found.
#
# NOTE: Does NOT filter by Active status to avoid slow/hanging subqueries.
# Callers should verify Active status separately if needed.
#
# Usage: name=$(pm_bot_developer_name "$ORG_ALIAS")
pm_bot_developer_name() {
  local org_alias="$1"
  sf data query \
    --query "SELECT DeveloperName FROM BotDefinition WHERE AgentTemplate IN (${PM_AGENT_TEMPLATES_SOQL}) ORDER BY LastModifiedDate DESC LIMIT 1" \
    --target-org "$org_alias" \
    --json 2>/dev/null \
    | jq -r '.result.records[0].DeveloperName // empty' 2>/dev/null \
    || echo ""
}

# Print the total number of Pipeline Management bots (BotDefinition rows
# matching PM AgentTemplate). Returns 0 if none, on error, or if the result
# can't be parsed.
#
# NOTE: Does NOT filter by Active status to avoid slow/hanging subqueries.
#
# Usage: count=$(pm_bot_count "$ORG_ALIAS")
pm_bot_count() {
  local org_alias="$1"
  local count
  count=$(sf data query \
    --query "SELECT Id FROM BotDefinition WHERE AgentTemplate IN (${PM_AGENT_TEMPLATES_SOQL})" \
    --target-org "$org_alias" \
    --json 2>/dev/null \
    | jq -r '.result.totalSize // 0' 2>/dev/null \
    | head -1 | tr -cd '0-9')
  echo "${count:-0}"
}

# Print the AgentTemplate API name of the active Pipeline Management bot.
# Used to keep the deployed flow's SalesManagementAgentTemplate constant
# in sync with the actual bot on the org (legacy SalesMgmt__SalesAgent vs
# upgraded SalesMgmt__NGASalesAgent), so the flow's BotDefinition lookup
# will match at runtime.
#
# Selection rule when both templates have a bot: prefer NGA (the forward
# direction; our authoring bundle publishes NGA). SOQL does not support CASE
# in ORDER BY, so we query NGA first and fall back to legacy.
#
# NOTE: Does NOT filter by Active status to avoid slow/hanging subqueries.
# Callers should verify Active status separately if needed.
#
# Exit codes distinguish failure modes for callers:
#   0 + stdout populated  -> bot found, prints template name
#   1 + empty stdout      -> no PM bot exists on the org
#   2 + empty stdout      -> SOQL/auth/network failure (transient)
#
# Usage:
#   if tpl=$(pm_bot_agent_template "$ORG_ALIAS"); then ... fi
#   rc=$?  # 0=ok, 1=no-bot, 2=query-failed
pm_bot_agent_template() {
  local org_alias="$1"
  local raw rc tpl

  raw=$(sf data query \
    --query "SELECT AgentTemplate FROM BotDefinition WHERE AgentTemplate = 'SalesMgmt__NGASalesAgent' ORDER BY LastModifiedDate DESC LIMIT 1" \
    --target-org "$org_alias" \
    --json 2>/dev/null)
  rc=$?
  if [[ $rc -ne 0 || -z "$raw" ]]; then
    return 2
  fi
  tpl=$(echo "$raw" | jq -r '.result.records[0].AgentTemplate // empty' 2>/dev/null)
  if [[ -n "$tpl" ]]; then
    echo "$tpl"
    return 0
  fi

  raw=$(sf data query \
    --query "SELECT AgentTemplate FROM BotDefinition WHERE AgentTemplate = 'SalesMgmt__SalesAgent' ORDER BY LastModifiedDate DESC LIMIT 1" \
    --target-org "$org_alias" \
    --json 2>/dev/null)
  rc=$?
  if [[ $rc -ne 0 || -z "$raw" ]]; then
    return 2
  fi
  tpl=$(echo "$raw" | jq -r '.result.records[0].AgentTemplate // empty' 2>/dev/null)
  if [[ -n "$tpl" ]]; then
    echo "$tpl"
    return 0
  fi
  return 1
}

# Print the number of agent users that HOLD SalesManagementAgentUserPsg.
# This — not PSG existence — is a real "PM setup has run" signal, because the
# two PM PSGs (SalesManagementUserPsg / SalesManagementAgentUserPsg) ship with
# the Agentforce-for-Sales license and exist even in a never-configured org.
# Returns 0 if none / on error.
#
# Usage: n=$(pm_agent_user_holds_psg "$ORG_ALIAS")
pm_agent_user_holds_psg() {
  local org_alias="$1" count
  count=$(sf data query \
    --query "SELECT Id FROM PermissionSetAssignment WHERE Assignee.Username LIKE '%salesmanagementagentuser%' AND PermissionSetGroup.DeveloperName='SalesManagementAgentUserPsg'" \
    --target-org "$org_alias" --json 2>/dev/null \
    | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9')
  echo "${count:-0}"
}

# Print the number of scheduled flows cloned from the PM template
# (sales_pipe_mgmt__OppSuggGenSchFlow). A real "PM setup has run" signal.
# Returns 0 if none / on error.
#
# Usage: n=$(pm_flow_clone_exists "$ORG_ALIAS")
pm_flow_clone_exists() {
  local org_alias="$1" count
  count=$(sf data query \
    --query "SELECT Id FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" \
    --target-org "$org_alias" --json 2>/dev/null \
    | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9')
  echo "${count:-0}"
}

# Print the latest BotVersion VersionNumber for the PM bot (any status). Empty
# if no version exists. Note: This returns the most recent version regardless
# of activation status, which is necessary for the publish-then-activate flow
# where the freshly published version is still Inactive.
#
# Usage: ver=$(pm_bot_latest_version "$ORG_ALIAS")
pm_bot_latest_version() {
  local org_alias="$1"
  sf data query \
    --query "SELECT VersionNumber FROM BotVersion WHERE BotDefinition.AgentTemplate IN (${PM_AGENT_TEMPLATES_SOQL}) ORDER BY VersionNumber DESC LIMIT 1" \
    --target-org "$org_alias" \
    --json 2>/dev/null \
    | jq -r '.result.records[0].VersionNumber // empty' 2>/dev/null \
    || echo ""
}

# Print the number of ACTIVE BotVersions for the PM bot. A bot can exist
# (BotDefinition present) yet have no active version — this is exactly the
# state auto-provisioning leaves the bot in: the BotVersion lands Inactive and
# must be activated before the scheduled flow will add the agent user to
# opportunity teams or Agent Access can be defined. Uses a SEPARATE flat query
# on BotVersion (never a correlated subquery — see PM_ACTIVE_BOT_FILTER note).
# Returns 0 if none / on error.
#
# Usage: n=$(pm_bot_active_version_count "$ORG_ALIAS")
pm_bot_active_version_count() {
  local org_alias="$1" count
  count=$(sf data query \
    --query "SELECT Id FROM BotVersion WHERE BotDefinition.AgentTemplate IN (${PM_AGENT_TEMPLATES_SOQL}) AND Status = 'Active'" \
    --target-org "$org_alias" \
    --json 2>/dev/null \
    | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9')
  echo "${count:-0}"
}

# Ensure the PM bot has an ACTIVE BotVersion, activating the latest version if
# not. Idempotent: a no-op (returns 0) when an active version already exists.
# Uses `sf agent activate`, matching the activation path in
# publish_and_activate_agent. Prints progress via plain echo.
#
# Returns:
#   0 - an active version exists (already, or after successful activation)
#   1 - activation was attempted but failed, or no version exists to activate
#
# Usage: activate_pm_bot_if_inactive "$ORG_ALIAS"
activate_pm_bot_if_inactive() {
  local org_alias="$1"

  local active_count
  active_count=$(pm_bot_active_version_count "$org_alias")
  if [[ "$active_count" -ge 1 ]]; then
    return 0
  fi

  local latest_version api_name
  latest_version=$(pm_bot_latest_version "$org_alias")
  if [[ -z "$latest_version" ]]; then
    echo "  ERROR: BotDefinition exists but has no BotVersion to activate."
    return 1
  fi

  api_name=$(pm_bot_developer_name "$org_alias")
  [[ -z "$api_name" ]] && api_name="SalesAgent"

  echo "  Activating $api_name version $latest_version (auto-provisioned version was Inactive)..."
  local activate_result
  activate_result=$(sf agent activate --api-name "$api_name" --version "$latest_version" --target-org "$org_alias" --json 2>/dev/null || echo '{"status":1}')

  if ! echo "$activate_result" | jq -e '.status == 0' >/dev/null 2>&1; then
    local activate_err
    activate_err=$(echo "$activate_result" | jq -r '.message // .result.message // .result.errors[0].message // "unknown"' 2>/dev/null || echo "unknown")
    echo "  ERROR: Agent activation failed: $activate_err"
    return 1
  fi

  # Confirm the activation took effect (async on some orgs).
  local attempt
  for attempt in {1..3}; do
    active_count=$(pm_bot_active_version_count "$org_alias")
    [[ "$active_count" -ge 1 ]] && return 0
    [[ $attempt -lt 3 ]] && sleep 5
  done

  # sf agent activate returned success; treat as activated even if the
  # confirmation query lagged.
  return 0
}
