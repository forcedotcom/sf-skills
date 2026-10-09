#!/usr/bin/env bash
# configure-and-report.sh - author a WorkSkillRouting rule (field-value -> required Omni Skill) for a related entity via the Metadata API; detect-before-write, idempotent, graceful-degrade when the feature is unavailable. Args, env, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 5 ]; then
  echo '{"error":"Usage: bash configure-and-report.sh <org-alias> <related_entity> <field> <skill> <value> [rule_master_label]"}' >&2
  exit 1
fi

ORG="$1"
RELATED_ENTITY="$2"
FIELD="$3"
SKILL="$4"
VALUE="$5"
MASTER_LABEL_EXPLICIT=false
{ [ -n "${6:-}" ] || [ -n "${RULE_MASTER_LABEL:-}" ]; } && MASTER_LABEL_EXPLICIT=true
IS_ACTIVE_EXPLICIT=false
[ -n "${IS_ACTIVE:-}" ] && IS_ACTIVE_EXPLICIT=true
RULE_MASTER_LABEL="${6:-${RULE_MASTER_LABEL:-$RELATED_ENTITY Skill Routing}}"

RULE_DN="${RULE_DEVELOPER_NAME:-$RELATED_ENTITY}"
IS_ACTIVE="${IS_ACTIVE:-true}"
SKILL_LEVEL="${SKILL_LEVEL:-}"
SKILL_PRIORITY="${SKILL_PRIORITY:-}"
IS_ADDITIONAL_SKILL="${IS_ADDITIONAL_SKILL:-}"

# ---- validation (reject before any sf call) ----
if ! [[ "$RELATED_ENTITY" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid related_entity '$RELATED_ENTITY'. Must be an sObject API name (letters, digits, underscores; max 80).\"}" >&2
  exit 1
fi
if ! [[ "$FIELD" =~ ^[A-Za-z][A-Za-z0-9_.]{0,120}$ ]]; then
  echo "{\"error\":\"Invalid field '$FIELD'. Use a field API name, optionally Entity.Field (letters, digits, underscores, dots).\"}" >&2
  exit 1
fi
if ! [[ "$SKILL" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid skill '$SKILL'. Must be a Skill DeveloperName (letters, digits, underscores; max 80).\"}" >&2
  exit 1
fi
if ! [[ "$VALUE" =~ ^[A-Za-z0-9][A-Za-z0-9\ _./-]{0,254}$ ]]; then
  echo "{\"error\":\"Invalid value '$VALUE'. Provide a plain field value (letters, digits, space, . _ / -); XML-reserved characters are not supported.\"}" >&2
  exit 1
fi
if ! [[ "$RULE_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid RULE_DEVELOPER_NAME '$RULE_DN'.\"}" >&2
  exit 1
fi
if ! [[ "$RULE_MASTER_LABEL" =~ ^[A-Za-z0-9][A-Za-z0-9\ _-]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid rule_master_label '$RULE_MASTER_LABEL'.\"}" >&2
  exit 1
fi
if [ "$IS_ACTIVE" != "true" ] && [ "$IS_ACTIVE" != "false" ]; then
  echo "{\"error\":\"Invalid IS_ACTIVE '$IS_ACTIVE' - must be true or false.\"}" >&2
  exit 1
fi
if [ -n "$SKILL_LEVEL" ] && { ! [[ "$SKILL_LEVEL" =~ ^[0-9]+$ ]] || [ "$SKILL_LEVEL" -gt 10 ]; }; then
  echo "{\"error\":\"Invalid SKILL_LEVEL '$SKILL_LEVEL' - must be an integer 0..10.\"}" >&2
  exit 1
fi
if [ -n "$SKILL_PRIORITY" ] && { ! [[ "$SKILL_PRIORITY" =~ ^[0-9]+$ ]] || [ "$SKILL_PRIORITY" -gt 10 ]; }; then
  echo "{\"error\":\"Invalid SKILL_PRIORITY '$SKILL_PRIORITY' - must be an integer 0..10.\"}" >&2
  exit 1
fi
if [ -n "$IS_ADDITIONAL_SKILL" ] && [ "$IS_ADDITIONAL_SKILL" != "true" ] && [ "$IS_ADDITIONAL_SKILL" != "false" ]; then
  echo "{\"error\":\"Invalid IS_ADDITIONAL_SKILL '$IS_ADDITIONAL_SKILL' - must be true or false.\"}" >&2
  exit 1
fi

# The Metadata API requires WorkSkillRoutingAttribute.field to be entity-qualified.
# Bare standard fields are otherwise resolved as CustomField metadata and fail to deploy.
if [[ "$FIELD" != *.* ]]; then
  FIELD="${RELATED_ENTITY}.${FIELD}"
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

emit_blocked() {
  local msg="$1"; local target_skill="${2:-}"
  local manual_actions='[]'
  if [ -n "$target_skill" ]; then
    manual_actions=$(jq -n --arg ts "$target_skill" '[{id:"MISSING_PREREQ",title:"Run prerequisite skill",target_skill:$ts}]')
  fi
  jq -n --arg msg "$msg" --arg rdn "$RULE_DN" --arg ent "$RELATED_ENTITY" --argjson ma "$manual_actions" \
    '{skill:"service-omni-work-skill-routing-configure",status:"blocked",
      rule:{developer_name:$rdn,related_entity:$ent,state:"not_deployed"},
      attribute:null,deploy_id:null,manual_actions:$ma,blocking_issue:$msg}'
  exit 1
}

emit_plan() {
  local detail="$1"
  jq -n --arg detail "$detail" --arg rdn "$RULE_DN" --arg ent "$RELATED_ENTITY" \
    '{skill:"service-omni-work-skill-routing-configure",status:"action_needed",plan_mode:true,
      plan_detail:$detail,rule:{developer_name:$rdn,related_entity:$ent},manual_actions:[],blocking_issue:null}'
  exit 0
}

# Step 1 - Organization + safe_to_write guard
ORG_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" --json 2>/dev/null) \
  || emit_blocked "Failed to query Organization for the safe_to_write guard."
IS_SANDBOX=$(echo "$ORG_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_JSON"   | jq -r '.result.records[0].OrganizationType')
SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] || [ "$TRIAL_EXP" != "null" ] \
   || [ "$ORG_TYPE" = "Developer Edition" ] || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi
[ "$SAFE_TO_WRITE" = "true" ] || emit_blocked "Refusing to author a routing rule on a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org."

# Step 2 - Referenced Skill must exist (a WorkSkillRoutingAttribute.skill points at a Skill DeveloperName)
SKILL_JSON=$(sf data query --target-org "$ORG" --json \
  --query "SELECT Id FROM Skill WHERE DeveloperName='$SKILL'" 2>/dev/null || echo '{}')
SKILL_COUNT=$(echo "$SKILL_JSON" | jq -r '.result.records | length' 2>/dev/null || echo 0)
[ "${SKILL_COUNT:-0}" -ge 1 ] || emit_blocked "Referenced Skill '$SKILL' does not exist; deploy it first so the rule can bind to it." "service-omni-skills-based-routing-configure"

# A metadata deploy replaces the full one-per-entity rule. Read and merge the
# current attribute array so adding Origin does not erase an existing Priority rule.
MERGE_MODE=true
[ "${WSR_REPLACE:-}" = "1" ] && MERGE_MODE=false
EXISTING_ATTRS='[]'
MERGED_FROM_EXISTING=false
if [ "$MERGE_MODE" = "true" ]; then
  WSR_META_JSON=$(sf data query --target-org "$ORG" --use-tooling-api --json \
    --query "SELECT Metadata FROM WorkSkillRouting WHERE DeveloperName='$RULE_DN'" 2>/dev/null || true)
  if echo "$WSR_META_JSON" | jq -e '.result.totalSize == 1' >/dev/null 2>&1; then
    MERGED_FROM_EXISTING=true
    EXISTING_ATTRS=$(echo "$WSR_META_JSON" | jq -c '.result.records[0].Metadata.workSkillRoutingAttributes // []')
    PRESERVED_LABEL=$(echo "$WSR_META_JSON" | jq -r '.result.records[0].Metadata.masterLabel // ""')
    PRESERVED_ACTIVE=$(echo "$WSR_META_JSON" | jq -r '.result.records[0].Metadata.isActive // empty')
    [ "$MASTER_LABEL_EXPLICIT" = "true" ] || [ -z "$PRESERVED_LABEL" ] || RULE_MASTER_LABEL="$PRESERVED_LABEL"
    [ "$IS_ACTIVE_EXPLICIT" = "true" ] || [ -z "$PRESERVED_ACTIVE" ] || IS_ACTIVE="$PRESERVED_ACTIVE"
  elif echo "$WSR_META_JSON" | jq -e '.result.totalSize == 0' >/dev/null 2>&1; then
    :
  elif ! echo "$WSR_META_JSON" | grep -qiE 'INVALID_TYPE|not available|no such|Cannot find'; then
    emit_blocked "Could not read existing WorkSkillRouting '$RULE_DN' for a merge. Refusing a destructive whole-rule replace; retry the read or set WSR_REPLACE=1 to overwrite intentionally."
  fi
fi

NEW_ATTR=$(jq -n \
  --arg field "$FIELD" --arg skill "$SKILL" --arg value "$VALUE" \
  --arg lvl "$SKILL_LEVEL" --arg pri "$SKILL_PRIORITY" --arg add "$IS_ADDITIONAL_SKILL" \
  '{field:$field,skill:$skill,value:$value}
   + (if $add=="" then {} else {isAdditionalSkill:($add=="true")} end)
   + (if $lvl=="" then {} else {skillLevel:($lvl|tonumber)} end)
   + (if $pri=="" then {} else {skillPriority:($pri|tonumber)} end)')
MERGED_ATTRS=$(jq -c -n --argjson existing "$EXISTING_ATTRS" --argjson new "$NEW_ATTR" \
  '($existing | map(select((.field==$new.field and .value==$new.value) | not))) + [$new]')
ATTR_COUNT=$(echo "$MERGED_ATTRS" | jq -r 'length')
PRESERVED_COUNT=$((ATTR_COUNT - 1))

# PLAN_ONLY - read-only; report intent and stop before any write.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  emit_plan "Would deploy WorkSkillRouting '$RULE_DN' on $RELATED_ENTITY (isActive=$IS_ACTIVE) mapping $FIELD='$VALUE' -> Skill '$SKILL'."
fi

# Step 3 - Materialize the WorkSkillRouting in XSD (alphabetical) order
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
cp "$SCRIPT_DIR/../assets/sfdx-project.json" "$WORK/sfdx-project.json" 2>/dev/null \
  || echo '{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"66.0"}' > "$WORK/sfdx-project.json"
WSR_DIR="$WORK/force-app/main/default/workSkillRoutings"
mkdir -p "$WSR_DIR"

ATTR_XML=$(echo "$MERGED_ATTRS" | jq -r '
  def xe: tostring | gsub("&";"&amp;") | gsub("<";"&lt;") | gsub(">";"&gt;");
  .[] |
  "    <workSkillRoutingAttributes>",
  "        <field>\(.field|xe)</field>",
  (if has("isAdditionalSkill") then "        <isAdditionalSkill>\(.isAdditionalSkill)</isAdditionalSkill>" else empty end),
  "        <skill>\(.skill|xe)</skill>",
  (if .skillLevel != null then "        <skillLevel>\(.skillLevel)</skillLevel>" else empty end),
  (if .skillPriority != null then "        <skillPriority>\(.skillPriority)</skillPriority>" else empty end),
  "        <value>\(.value|xe)</value>",
  "    </workSkillRoutingAttributes>"
')

cat > "$WSR_DIR/${RULE_DN}.workSkillRouting-meta.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<WorkSkillRouting xmlns="http://soap.sforce.com/2006/04/metadata">
    <isActive>${IS_ACTIVE}</isActive>
    <masterLabel>${RULE_MASTER_LABEL}</masterLabel>
    <relatedEntity>${RELATED_ENTITY}</relatedEntity>
${ATTR_XML}
</WorkSkillRouting>
XML

# Step 4 - Deploy (async + poll to terminal state)
START_JSON=$(cd "$WORK" && sf project deploy start --target-org "$ORG" \
  --metadata "WorkSkillRouting:${RULE_DN}" --async --json 2>/dev/null || true)
DEPLOY_ID=$(echo "$START_JSON" | jq -r '.result.id // ""' 2>/dev/null)
DEPLOY_JSON="$START_JSON"

if [ -n "$DEPLOY_ID" ] && [ "$DEPLOY_ID" != "null" ]; then
  POLL_STATUS=""
  for _ in $(seq 1 60); do
    REPORT_JSON=$(cd "$WORK" && sf project deploy report --job-id "$DEPLOY_ID" --target-org "$ORG" --json 2>/dev/null || true)
    CUR_STATUS=$(echo "$REPORT_JSON" | jq -r '.result.status // ""' 2>/dev/null)
    case "$CUR_STATUS" in
      Succeeded|Failed|SucceededPartial|Canceled) DEPLOY_JSON="$REPORT_JSON"; POLL_STATUS="$CUR_STATUS"; break ;;
    esac
    sleep 15
  done
  [ -n "$POLL_STATUS" ] || emit_blocked "WorkSkillRouting deploy job $DEPLOY_ID did not reach a terminal state within the poll budget. Not reporting success."
fi

DEPLOY_SUCCESS=$(echo "$DEPLOY_JSON" | jq -r '.result.success // false' 2>/dev/null)
DEPLOY_ID=$(echo "$DEPLOY_JSON"      | jq -r '.result.id      // ""'    2>/dev/null)

if [ "$DEPLOY_SUCCESS" != "true" ]; then
  FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.result.details.componentFailures // [] | map(.problem) | join("; ")' 2>/dev/null)
  [ -n "$FAILURES" ] && [ "$FAILURES" != "null" ] || FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.message // .result.errorMessage // "Unknown deploy error"' 2>/dev/null)
  case "$FAILURES" in
    *INVALID_TYPE*|*"Cannot find"*|*"not available"*|*"WorkSkillRouting"*)
      emit_blocked "WorkSkillRouting is not available on this org (skills-based routing may be off, or the feature is not provisioned on this trial/CDO): $FAILURES" "service-omni-base-settings-configure" ;;
    *"$SKILL"*)
      emit_blocked "Deploy failed: Skill '$SKILL' could not be resolved by the rule. $FAILURES" "service-omni-skills-based-routing-configure" ;;
    *) emit_blocked "WorkSkillRouting deploy failed: $FAILURES" ;;
  esac
fi

STATE_WSR=$(echo "$DEPLOY_JSON" | jq -r --arg fn "$RULE_DN" \
  '.result.files[] | select(.fullName==$fn and .type=="WorkSkillRouting") | .state' 2>/dev/null | head -1)
STATE_WSR="${STATE_WSR:-unknown}"
case "$STATE_WSR" in
  Created|Changed|Unchanged) ;;
  *) emit_blocked "Deploy reported success overall but WorkSkillRouting '$RULE_DN' has an unrecognized/absent state \"$STATE_WSR\" (expected Created, Changed, or Unchanged). Not reporting success." ;;
esac

STATUS="reused"
[ "$STATE_WSR" = "Created" ] && STATUS="created"
[ "$STATE_WSR" = "Changed" ] && STATUS="updated"

jq -n \
  --arg status "$STATUS" \
  --arg rdn "$RULE_DN" --arg lbl "$RULE_MASTER_LABEL" --arg ent "$RELATED_ENTITY" --arg act "$IS_ACTIVE" --arg state "$STATE_WSR" \
  --arg field "$FIELD" --arg skill "$SKILL" --arg value "$VALUE" \
  --arg lvl "$SKILL_LEVEL" --arg pri "$SKILL_PRIORITY" --arg add "$IS_ADDITIONAL_SKILL" \
  --arg deploy_id "$DEPLOY_ID" \
  --argjson merged_from_existing "$MERGED_FROM_EXISTING" \
  --argjson attribute_count "$ATTR_COUNT" \
  --argjson preserved_count "$PRESERVED_COUNT" \
  '{
    skill: "service-omni-work-skill-routing-configure",
    status: $status,
    rule: {developer_name:$rdn, master_label:$lbl, related_entity:$ent, is_active:($act=="true"), state:$state},
    merge: {merged_from_existing:$merged_from_existing, attribute_count:$attribute_count, preserved_count:$preserved_count},
    attribute: {
      field:$field, skill:$skill, value:$value,
      skill_level:(if $lvl=="" then null else ($lvl|tonumber) end),
      skill_priority:(if $pri=="" then null else ($pri|tonumber) end),
      is_additional_skill:(if $add=="" then null else ($add=="true") end)
    },
    deploy_id: (if $deploy_id=="" then null else $deploy_id end),
    manual_actions: [],
    blocking_issue: null
  }'
