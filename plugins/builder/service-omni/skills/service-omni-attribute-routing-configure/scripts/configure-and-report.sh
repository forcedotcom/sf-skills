#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage:
  bash configure-and-report.sh <org> list
  bash configure-and-report.sh <org> get <rule-id>
  bash configure-and-report.sh <org> create <developer-name> <label> <related-entity>
  bash configure-and-report.sh <org> add-attribute <rule-id> <field> <value> <skill-id> <level> <related-entity> [additional] [priority]
  bash configure-and-report.sh <org> set-active <rule-id> true|false
  CONFIRM_DELETE=1 bash configure-and-report.sh <org> delete-attribute <attribute-id>
  CONFIRM_DELETE=1 bash configure-and-report.sh <org> delete-rule <rule-id>
EOF
}

emit_blocked() {
  jq -n --arg operation "$OPERATION" --arg issue "$1" \
    '{skill:"service-omni-attribute-routing-configure",status:"blocked",operation:$operation,result:null,blocking_issue:$issue}'
  exit 1
}

valid_id() { [[ "$1" =~ ^[A-Za-z0-9]{15,18}$ ]]; }
valid_name() { [[ "$1" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; }
valid_entity() {
  case "$1" in
    Case|ChangeRequest|ContactRequest|FlowOrchestrationWorkItem|Incident|Lead|LiveChatTranscript|MessagingSession|Order|Problem|SocialPost|VoiceCall|WorkOrder) return 0 ;;
    *) return 1 ;;
  esac
}

safe_to_write() {
  local org_json is_sandbox trial_exp org_type
  org_json=$(sf data query --target-org "$ORG" --json \
    --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" 2>/dev/null) \
    || emit_blocked "Failed to establish the target org safety boundary."
  is_sandbox=$(jq -r '.result.records[0].IsSandbox // false' <<<"$org_json")
  trial_exp=$(jq -r '.result.records[0].TrialExpirationDate // "null"' <<<"$org_json")
  org_type=$(jq -r '.result.records[0].OrganizationType // ""' <<<"$org_json")
  if [ "$is_sandbox" != "true" ] && [ "$trial_exp" = "null" ] \
     && [ "$org_type" != "Developer Edition" ] && [ "$org_type" != "Base Edition" ]; then
    emit_blocked "Refusing to change attribute routing in a production customer org. Use a sandbox, trial, Developer Edition, or Base Edition org."
  fi
}

request() {
  local method="$1" endpoint="$2" body="${3:-}"
  if [ -n "$body" ]; then
    REQUEST_OUTPUT=$(FORCE_COLOR=0 sf api request rest "$endpoint" --method "$method" --body "$body" --target-org "$ORG" 2>/dev/null) \
      || emit_blocked "The Tooling API $method operation failed."
  else
    REQUEST_OUTPUT=$(FORCE_COLOR=0 sf api request rest "$endpoint" --method "$method" --target-org "$ORG" 2>/dev/null) \
      || emit_blocked "The Tooling API $method operation failed."
  fi
  if [ -z "$REQUEST_OUTPUT" ] && { [ "$method" = "PATCH" ] || [ "$method" = "DELETE" ]; }; then
    REQUEST_OUTPUT='{}'
  fi
  jq -e . >/dev/null 2>&1 <<<"$REQUEST_OUTPUT" \
    || emit_blocked "The Tooling API $method operation returned malformed JSON."
}

delete_tooling_record() {
  local object="$1" record_id="$2"
  DELETE_OUTPUT=$(FORCE_COLOR=0 sf data delete record --target-org "$ORG" --json --api-version "$API_VERSION" --use-tooling-api \
    --sobject "$object" --record-id "$record_id" 2>/dev/null) \
    || emit_blocked "The Tooling API DELETE operation failed."
  jq -e '.status == 0 and .result.success == true' >/dev/null 2>&1 <<<"$DELETE_OUTPUT" \
    || emit_blocked "The Tooling API DELETE operation returned an unsuccessful result."
}

ensure_available() {
  request GET "$BASE/sobjects/WorkSkillRouting/describe"
  [ "$(jq -r '.createable // false' <<<"$REQUEST_OUTPUT")" = "true" ] \
    || emit_blocked "WorkSkillRouting is unavailable or read-only. Enable Omni-Channel and Skills-Based Routing, then retry."
}

[ $# -ge 2 ] || { usage; exit 2; }
ORG="$1"
OPERATION="$2"
shift 2
API_VERSION="${SF_API_VERSION:-68.0}"
BASE="/services/data/v${API_VERSION}/tooling"

sf org display --target-org "$ORG" --json >/dev/null 2>&1 \
  || emit_blocked "The target org is not authenticated or cannot be reached."

case "$OPERATION" in
  list)
    [ $# -eq 0 ] || { usage; exit 2; }
    result=$(sf data query --target-org "$ORG" --use-tooling-api --json \
      --query "SELECT Id, DeveloperName, MasterLabel, IsActive, RelatedEntity FROM WorkSkillRouting ORDER BY DeveloperName" 2>/dev/null) \
      || emit_blocked "WorkSkillRouting is unavailable. Enable Omni-Channel and Skills-Based Routing, then retry."
    jq -n --argjson records "$(jq -c '.result.records // []' <<<"$result")" \
      '{skill:"service-omni-attribute-routing-configure",status:"analyzed",operation:"list",result:{records:$records,count:($records|length)},blocking_issue:null}'
    ;;
  get)
    [ $# -eq 1 ] && valid_id "$1" || emit_blocked "get requires a valid 15- or 18-character WorkSkillRouting Id."
    request GET "$BASE/sobjects/WorkSkillRouting/$1"
    result="$REQUEST_OUTPUT"
    jq -n --argjson record "$result" \
      '{skill:"service-omni-attribute-routing-configure",status:"analyzed",operation:"get",result:{record:$record},blocking_issue:null}'
    ;;
  create)
    [ $# -eq 3 ] || emit_blocked "create requires developer-name, label, and related-entity."
    developer_name="$1"; label="$2"; entity="$3"
    valid_name "$developer_name" || emit_blocked "Invalid routing-rule developer name."
    valid_entity "$entity" || emit_blocked "Unsupported related entity '$entity'."
    ensure_available
    existing_query=$(sf data query --target-org "$ORG" --use-tooling-api --json \
      --query "SELECT Id FROM WorkSkillRouting WHERE DeveloperName = '$developer_name' LIMIT 1" 2>/dev/null) \
      || emit_blocked "Failed to check for an existing attribute-routing rule."
    existing_id=$(jq -r '.result.records[0].Id // empty' <<<"$existing_query")
    if [ -n "$existing_id" ]; then
      request GET "$BASE/sobjects/WorkSkillRouting/$existing_id"
      existing="$REQUEST_OUTPUT"
      existing_label=$(jq -r '.Metadata.masterLabel // .MasterLabel // empty' <<<"$existing")
      existing_entity=$(jq -r '.Metadata.relatedEntity // .RelatedEntity // empty' <<<"$existing")
      existing_active=$(jq -r '.Metadata.isActive // .IsActive // false' <<<"$existing")
      [ "$existing_label" = "$label" ] && [ "$existing_entity" = "$entity" ] && [ "$existing_active" = "false" ] \
        || emit_blocked "A routing rule named '$developer_name' already exists with different label, entity, or activation state."
      jq -n --argjson record "$existing" \
        '{skill:"service-omni-attribute-routing-configure",status:"reused",operation:"create",result:{record:$record},blocking_issue:null}'
      exit 0
    fi
    safe_to_write
    body=$(jq -cn --arg fullName "$developer_name" --arg label "$label" --arg entity "$entity" \
      '{FullName:$fullName,Metadata:{masterLabel:$label,relatedEntity:$entity,isActive:false}}')
    request POST "$BASE/sobjects/WorkSkillRouting" "$body"
    created="$REQUEST_OUTPUT"
    id=$(jq -r '.id // empty' <<<"$created")
    [ -n "$id" ] || emit_blocked "The Tooling API did not return the created routing-rule Id."
    request GET "$BASE/sobjects/WorkSkillRouting/$id"
    verified="$REQUEST_OUTPUT"
    jq -n --argjson create "$created" --argjson record "$verified" \
      '{skill:"service-omni-attribute-routing-configure",status:"created",operation:"create",result:{create:$create,record:$record},blocking_issue:null}'
    ;;
  add-attribute)
    [ $# -ge 6 ] && [ $# -le 8 ] || emit_blocked "add-attribute requires rule-id, field, value, skill-id, level, related-entity, and optional additional/priority."
    rule_id="$1"; field="$2"; value="$3"; skill_id="$4"; level="$5"; entity="$6"; additional="${7:-false}"; priority="${8:-}"
    valid_id "$rule_id" && valid_id "$skill_id" || emit_blocked "Rule Id and Skill Id must be valid Salesforce record Ids."
    [[ "$field" =~ ^[A-Za-z][A-Za-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*$ ]] || emit_blocked "Field must be entity-qualified, for example Case.Priority."
    jq -en --arg level "$level" '($level|tonumber) >= 0 and ($level|tonumber) <= 10' >/dev/null 2>&1 \
      || emit_blocked "Skill level must be between 0 and 10."
    valid_entity "$entity" || emit_blocked "Unsupported related entity '$entity'."
    field_entity="${field%%.*}"; field_name="${field#*.}"
    [ "$field_entity" = "$entity" ] || emit_blocked "Field '$field' does not belong to related entity '$entity'."
    [ "$additional" = "true" ] || [ "$additional" = "false" ] || emit_blocked "additional must be true or false."
    if [ -n "$priority" ]; then
      [ "$additional" = "true" ] || emit_blocked "Skill priority is valid only for an additional skill."
      [[ "$priority" =~ ^[0-4]$ ]] || emit_blocked "Skill priority must be between 0 and 4."
    fi
    ensure_available
    request GET "$BASE/sobjects/WorkSkillRoutingAttribute/describe"
    [ "$(jq -r '.createable // false' <<<"$REQUEST_OUTPUT")" = "true" ] \
      || emit_blocked "WorkSkillRoutingAttribute is unavailable or read-only on this org."
    safe_to_write
    request GET "$BASE/sobjects/WorkSkillRouting/$rule_id"
    existing="$REQUEST_OUTPUT"
    parent_entity=$(jq -r '.Metadata.relatedEntity // empty' <<<"$existing")
    [ "$parent_entity" = "$entity" ] || emit_blocked "Related entity '$entity' does not match the parent rule ('$parent_entity')."
    request GET "/services/data/v${API_VERSION}/sobjects/${entity}/describe"
    field_describe="$REQUEST_OUTPUT"
    field_type=$(jq -r --arg field "$field_name" '.fields[] | select(.name==$field) | .type' <<<"$field_describe" | head -1)
    case "$field_type" in picklist|boolean|reference|id) ;; *) emit_blocked "Field '$field' is not an eligible picklist, boolean, reference, or id field." ;; esac
    if [ "$field_type" = "picklist" ]; then
      jq -e --arg field "$field_name" --arg value "$value" \
        '.fields[] | select(.name==$field) | [.picklistValues[]? | select(.active==true and .value==$value)] | length > 0' \
        <<<"$field_describe" >/dev/null || emit_blocked "Value '$value' is not an active value for '$field'."
    elif [ "$field_type" = "boolean" ]; then
      [ "$value" = "true" ] || [ "$value" = "false" ] || emit_blocked "Boolean field '$field' requires value true or false."
    fi
    distinct_fields=$(jq '[.Metadata.workSkillRoutingAttributes[]?.field] | unique | length' <<<"$existing")
    field_already_used=$(jq --arg field "$field" '[.Metadata.workSkillRoutingAttributes[]? | select(.field==$field)] | length' <<<"$existing")
    [ "$distinct_fields" -lt 10 ] || [ "$field_already_used" -gt 0 ] \
      || emit_blocked "A routing rule supports at most 10 distinct fields."
    existing_count=$(jq --arg field "$field" --arg value "$value" --arg skill "$skill_id" \
      '[.Metadata.workSkillRoutingAttributes[]? | select(.field==$field and .value==$value and ((.skillId // .skill) == $skill))] | length' <<<"$existing")
    if [ "$existing_count" -gt 0 ]; then
      jq -n --argjson record "$existing" \
        '{skill:"service-omni-attribute-routing-configure",status:"reused",operation:"add-attribute",result:{record:$record},blocking_issue:null}'
      exit 0
    fi
    body=$(jq -cn --arg rule "$rule_id" --arg field "$field" --arg value "$value" --arg skill "$skill_id" \
      --arg entity "$entity" --arg level "$level" --arg additional "$additional" --arg priority "$priority" \
      '{WorkSkillRoutingId:$rule,Field:$field,Value:$value,SkillId:$skill,SkillLevel:($level|tonumber),RelatedEntity:$entity,IsAdditionalSkill:($additional=="true")}
       + (if $priority=="" then {} else {SkillPriority:($priority|tonumber)} end)')
    request POST "$BASE/sobjects/WorkSkillRoutingAttribute" "$body"
    created="$REQUEST_OUTPUT"
    attribute_id=$(jq -r '.id // empty' <<<"$created")
    [ -n "$attribute_id" ] || emit_blocked "The Tooling API did not return the created attribute Id."
    request GET "$BASE/sobjects/WorkSkillRoutingAttribute/$attribute_id"
    verified="$REQUEST_OUTPUT"
    jq -n --argjson create "$created" --argjson record "$verified" \
      '{skill:"service-omni-attribute-routing-configure",status:"created",operation:"add-attribute",result:{create:$create,record:$record},blocking_issue:null}'
    ;;
  set-active)
    [ $# -eq 2 ] && valid_id "$1" || emit_blocked "set-active requires a valid rule Id and true or false."
    [ "$2" = "true" ] || [ "$2" = "false" ] || emit_blocked "set-active value must be true or false."
    ensure_available
    safe_to_write
    request GET "$BASE/sobjects/WorkSkillRouting/$1"
    current="$REQUEST_OUTPUT"
    metadata=$(jq -c --argjson active "$2" '.Metadata | del(.urls) | .isActive=$active' <<<"$current")
    [ "$2" = "false" ] || [ "$(jq '.workSkillRoutingAttributes // [] | length' <<<"$metadata")" -gt 0 ] \
      || emit_blocked "Refusing to activate a routing rule without attribute mappings."
    request PATCH "$BASE/sobjects/WorkSkillRouting/$1" "$(jq -cn --argjson metadata "$metadata" '{Metadata:$metadata}')"
    request GET "$BASE/sobjects/WorkSkillRouting/$1"
    verified="$REQUEST_OUTPUT"
    [ "$(jq -r '.Metadata.isActive' <<<"$verified")" = "$2" ] || emit_blocked "Activation verification did not match the requested state."
    jq -n --argjson record "$verified" \
      '{skill:"service-omni-attribute-routing-configure",status:"updated",operation:"set-active",result:{record:$record},blocking_issue:null}'
    ;;
  delete-attribute|delete-rule)
    [ $# -eq 1 ] && valid_id "$1" || emit_blocked "$OPERATION requires a valid Salesforce record Id."
    [ "${CONFIRM_DELETE:-0}" = "1" ] || emit_blocked "Deletion requires explicit CONFIRM_DELETE=1."
    ensure_available
    safe_to_write
    object="WorkSkillRoutingAttribute"; [ "$OPERATION" = "delete-rule" ] && object="WorkSkillRouting"
    delete_tooling_record "$object" "$1"
    jq -n --arg operation "$OPERATION" --arg id "$1" \
      '{skill:"service-omni-attribute-routing-configure",status:"deleted",operation:$operation,result:{id:$id},blocking_issue:null}'
    ;;
  *) usage; exit 2 ;;
esac
