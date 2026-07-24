#!/bin/bash

# Add an AI field-update suggestion for an Opportunity text field.
#
# WHEN to use this: to add a field AFTER initial setup. Greenfield setup is
# field-selection-driven — run setup-all.sh with --fields "<...>" to build the
# flow with the desired field set from the start (setup-all.sh calls this script
# internally with --skip-flow to create/activate each selected field's template,
# then wires the whole set via shared/flow-builder.sh build_field_collection). Reach
# for this script directly only to add a NEW field to an already-configured org:
# it creates/activates the template AND wires the field into the live flow.
#
# WHAT this does (the three things a field needs to produce suggestions):
#   1. Creates + ACTIVATES a field-completion (type einstein_gpt__fieldCompletion)
#      GenAiPromptTemplate for the field, from the canonical asset
#      assets/field-completion-template.genAiPromptTemplate-meta.xml.
#   2. Adds the field's API name to the ACTIVE suggestion flow's
#      OpportunityFields collection (Process_Field_Update_Suggestions),
#      idempotently, so getOrExecFieldUpdtSuggestion asks for it.
#   3. Verifies the field is accessible (FLS) — warns if not.
#
# WHY this is hardened (no retry loops — the failures this AVOIDS):
#   - Template activation is DETERMINISTIC. GenAiPromptTemplate IS retrievable
#     via CLI for user-created templates, so we deploy (Published, no version
#     identifiers), RETRIEVE the platform-generated <versionIdentifier>, set it
#     as <activeVersionIdentifier>, and redeploy. We never guess the identifier.
#   - The flow edit is XML-aware (python3 ElementTree, namespace-registered),
#     not sed. It inserts a <assignmentItems> block ONLY if the field is absent
#     (idempotent), preserves every sales_pipe_mgmt__* namespace reference, and
#     keeps <status>Active</status> so the running schedule is never deactivated.
#   - Verification uses the SYNCHRONOUS /generations endpoint (proves the
#     template resolves + grounds now), not the async AiGenActionItem schedule
#     path. The scheduled suggestions land in AiGenActionItem (~2-3 min after
#     the daily run; poll >=240s); that guidance is printed, not blocked on.
#
# Usage:
#   ./add-field-suggestion.sh <org-alias> <FieldApiName> [options]
#
# Options:
#   --label "<text>"        Field label for prompt text (default: from describe)
#   --instruction "<text>"  One-line field-specific extraction guidance
#   --goal "<text>"         One phrase for "You must think about <goal>"
#   --name <DevName>        GenAiPromptTemplate developerName (default: Recommend<Field>forOpp)
#   --verify-with-note      Seed a ContentNote on a sample opp + run /generations
#   --note "<text>"         Body of the seeded verification note (used with
#                           --verify-with-note). Pass a note tailored to this
#                           field's goal/instruction so generation exercises the
#                           customized prompt. Default: a generic multi-signal note.
#   --opp <OppId>           Opportunity to use for --verify-with-note (default: first open opp)
#   --skip-flow             Create/activate the template only; do not edit the flow
#   --force                 Regenerate + redeploy the template even if it is
#                           already active (mints a new template version)
#
# OOTB fields (currently only NextStep): two modes
#   The flow no longer ships every OOTB field — a field only generates suggestions
#   once it is wired into the flow's OpportunityFields collection. For a field that
#   ships with a managed field-completion prompt, this script has two modes:
#
#   1. WIRE-ONLY (no --goal/--instruction): keep the curated OOTB prompt exactly as
#      shipped and just wire the field into the flow. Nothing is deployed under a
#      custom template name; Steps 2-3 are skipped. This is the common way to add
#      NextStep post-setup when it was not selected during initial setup.
#   2. OVERRIDE (with --goal and/or --instruction): deploy an OVERRIDE of the managed
#      template (<overrideSource>), which the platform records as a NEW VERSION of
#      that managed template — not a separate prompt. This is the only supported way
#      to customize the OOTB goal/instruction.
#
#   Either way Step 4 runs its idempotent flow wiring to guarantee the field is in
#   OpportunityFields. Passing --skip-flow with an OOTB field and no --goal/
#   --instruction is a no-op and is rejected. StageName is a picklist and is not
#   eligible for either mode.
#
# Re-run safety: the flow edit (Step 4) is fully idempotent. The template
# deploy (Steps 2-3) is NOT — a redeploy mints a NEW template version each run.
# To avoid churning versions on an already-configured field, this script
# SKIPS Steps 2-3 when the template already exists and is active, unless
# --force is passed. The flow wiring and verification still run.

set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSET_TEMPLATE="$SCRIPT_DIR/../assets/field-completion-template.genAiPromptTemplate-meta.xml"
FLOW_API_NAME="Process_Field_Update_Suggestions"
TEMPLATE_DIR="force-app/main/default/genAiPromptTemplates"
FLOW_DIR="force-app/main/default/flows"
# Metadata is authored at 67.0 (see sfdx-project.json below), but the Einstein
# prompt-template REST endpoints are pinned to v64.0 — the version verified to
# return the /generations and /prompt-templates shapes this script parses, and
# the version the sibling setup scripts use. Deliberate split; do not "upgrade".
API_VERSION="v64.0"
# Hard cap on the number of Opportunity fields the suggestion flow may manage,
# OOTB fields (NextStep, StageName) inclusive. Pipeline Management supports at
# most this many managed fields; the flow-wiring step below refuses to exceed it.
MAX_SUGGESTION_FIELDS=5

# OOTB fields that already ship with a MANAGED field-completion prompt template
# (sales_pipe_mgmt namespace). You cannot edit a managed template, so customizing
# one of these fields' goal/instruction is done by deploying an OVERRIDE — a
# fieldCompletion template whose <overrideSource> points at the managed template.
# The platform records the override as a NEW VERSION of the managed template
# (verified on a live org), NOT as a separate prompt. Overriding only happens when
# the caller explicitly passes --goal/--instruction; otherwise the OOTB prompt is
# left untouched. Only NextStep is listed: StageName is a picklist and is rejected
# by the eligibility gate below, so it is intentionally NOT overridable here.
declare -A OOTB_MANAGED_TEMPLATE=(
  [NextStep]="sales_pipe_mgmt__RecommendNextStepforOpp"
)

# --- Helpers (mirror setup-all.sh / define-agent-access.sh conventions) ---
log_pass() { echo "  [PASS] $1"; }
log_warn() { echo "  [WARN] $1"; }
log_fail() { echo "  [FAIL] $1"; }
log_info() { echo "  [....] $1"; }
log_try()  { echo "  [TRY ] $1"; }

die() { log_fail "$1"; exit 1; }

# --- Arg parsing ---
ORG_ALIAS="${1:-}"
FIELD_API="${2:-}"
FIELD_LABEL=""
FIELD_INSTRUCTION=""
FIELD_GOAL=""
DEV_NAME=""
VERIFY_WITH_NOTE=false
OPP_ID=""
NOTE_TEXT=""   # --note "<text>": caller-supplied verification note body (used with --verify-with-note)
SKIP_FLOW=false
FORCE=false

if [[ -z "$ORG_ALIAS" || -z "$FIELD_API" ]]; then
  echo "Usage: $0 <org-alias> <FieldApiName> [--label TEXT] [--instruction TEXT] [--goal TEXT] [--name DevName] [--verify-with-note] [--note TEXT] [--opp OppId] [--skip-flow] [--force]"
  exit 1
fi

shift 2 || true
# Require a value for value-taking flags (else a trailing bare flag would make
# `shift 2` fail and abort under `set -e` with no message).
need_val() { [[ $# -ge 2 ]] || die "Option '$1' requires a value."; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --label)          need_val "$@"; FIELD_LABEL="$2"; shift 2 ;;
    --instruction)    need_val "$@"; FIELD_INSTRUCTION="$2"; shift 2 ;;
    --goal)           need_val "$@"; FIELD_GOAL="$2"; shift 2 ;;
    --name)           need_val "$@"; DEV_NAME="$2"; shift 2 ;;
    --opp)            need_val "$@"; OPP_ID="$2"; shift 2 ;;
    --note)           need_val "$@"; NOTE_TEXT="$2"; shift 2 ;;
    --verify-with-note) VERIFY_WITH_NOTE=true; shift ;;
    --skip-flow)      SKIP_FLOW=true; shift ;;
    --force)          FORCE=true; shift ;;
    *) die "Unknown option: $1" ;;
  esac
done

command -v python3 >/dev/null 2>&1 || die "python3 is required for the XML-aware flow edit."
[[ -f "$ASSET_TEMPLATE" ]] || die "Canonical template asset not found: $ASSET_TEMPLATE"

# Ensure a project context exists for deploy/retrieve.
if [[ ! -f "sfdx-project.json" ]]; then
  cat > sfdx-project.json << 'EOF'
{"packageDirectories": [{"path": "force-app", "default": true}], "sourceApiVersion": "67.0"}
EOF
fi

echo "Add Field Suggestion: $FIELD_API  (org: $ORG_ALIAS)"
echo ""

# ============================================================
# Step 1 — Validate field eligibility (describe)
# ============================================================
echo "Step 1: Validate field eligibility"

DESCRIBE=$(sf sobject describe --sobject Opportunity --target-org "$ORG_ALIAS" --json 2>/dev/null) \
  || die "Could not describe Opportunity on org '$ORG_ALIAS'. Check auth."

FIELD_JSON=$(echo "$DESCRIBE" | jq -c --arg f "$FIELD_API" '.result.fields[] | select(.name == $f)')
if [[ -z "$FIELD_JSON" ]]; then
  # `describe` only returns fields the running user can SEE. A freshly created
  # custom field has NO field-level security, so it exists but is invisible here.
  # Distinguish "doesn't exist" from "no FLS" via the Tooling API, and tell the
  # user the exact fix — so this never turns into blind retries.
  EXISTS=$(sf data query -q "SELECT QualifiedApiName FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName='Opportunity' AND QualifiedApiName='${FIELD_API}'" \
    --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null | jq -r '.result.records[0].QualifiedApiName // empty')
  if [[ -n "$EXISTS" ]]; then
    ADMIN_PS=$(sf data query -q "SELECT Id FROM PermissionSet WHERE IsOwnedByProfile=true AND Profile.Name='System Administrator' LIMIT 1" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty')
    echo ""
    log_fail "Field '$FIELD_API' exists but is not visible to you — it has no field-level security yet."
    echo "  A newly created custom field is invisible to 'describe' until FLS is granted."
    echo "  Grant read/edit to your admin permission set, then re-run this script:"
    echo ""
    echo "    sf data create record --sobject FieldPermissions \\"
    echo "      --values \"ParentId='${ADMIN_PS:-<AdminPermSetId>}' SobjectType='Opportunity' Field='Opportunity.${FIELD_API}' PermissionsRead=true PermissionsEdit=true\" \\"
    echo "      --target-org $ORG_ALIAS"
    echo ""
    exit 1
  fi
  die "Field '$FIELD_API' not found on Opportunity (no such field in FieldDefinition)."
fi

F_TYPE=$(echo "$FIELD_JSON" | jq -r '.type')
F_LEN=$(echo "$FIELD_JSON" | jq -r '.length')
F_UPDATEABLE=$(echo "$FIELD_JSON" | jq -r '.updateable')
F_CALCULATED=$(echo "$FIELD_JSON" | jq -r '.calculated')
F_HTML=$(echo "$FIELD_JSON" | jq -r '.htmlFormatted')
F_LABEL_DESCRIBED=$(echo "$FIELD_JSON" | jq -r '.label')

# Eligibility: plain Text (type=string) or Text Area <=255 (type=textarea), updateable,
# not calculated, not rich text (htmlFormatted), length <= 255.
#   - Text Area (255)   -> type=textarea, htmlFormatted=false, length<=255  ✅
#   - Long Text Area    -> type=textarea, length>255                        ❌ (length gate)
#   - Rich Text Area    -> type=textarea, htmlFormatted=true                ❌ (html gate)
if [[ "$F_TYPE" != "string" && "$F_TYPE" != "textarea" ]]; then
  die "Field '$FIELD_API' is type '$F_TYPE'. Only plain Text (type=string) or Text Area <=255 (type=textarea) fields are supported (not richtext/longtextarea/picklist/formula/date). Suggestions are capped at the field length."
fi
[[ "$F_HTML" == "true" ]] && die "Field '$FIELD_API' is a Rich Text Area (htmlFormatted). Not supported — use a plain Text or Text Area (<=255) field."
[[ "$F_UPDATEABLE" == "true" ]] || die "Field '$FIELD_API' is not updateable."
[[ "$F_CALCULATED" == "false" ]] || die "Field '$FIELD_API' is calculated (formula). Not supported."
if [[ "$F_LEN" -gt 255 ]]; then
  die "Field '$FIELD_API' length is $F_LEN (>255 — Long Text Area). Not supported; use a Text or Text Area field of 255 or fewer characters."
fi
log_pass "Eligible: type=$F_TYPE, length=$F_LEN, updateable=$F_UPDATEABLE"

# OOTB field detection. If this field already ships with a managed field-completion
# template (only NextStep today), we NEVER author a fresh standalone template. Two
# modes, decided by whether the caller passed --goal/--instruction:
#   * WIRE_ONLY (no --goal/--instruction): keep the curated OOTB prompt untouched and
#     just wire the field into the flow. The flow no longer ships every OOTB field, so
#     wiring NextStep post-setup is a legitimate, common action. Nothing is deployed.
#   * OVERRIDE (--goal/--instruction given): author an OVERRIDE of the managed template
#     (<overrideSource>), which the platform records as a NEW VERSION of the managed
#     template. This is the ONLY supported way to change the OOTB goal/instruction.
# We require an explicit --goal/--instruction before overriding: doing it with the
# generic defaults would silently replace a curated OOTB prompt with something weaker.
OVERRIDE_SOURCE=""
WIRE_ONLY=false
if [[ -n "${OOTB_MANAGED_TEMPLATE[$FIELD_API]:-}" ]]; then
  if [[ -z "$FIELD_GOAL" && -z "$FIELD_INSTRUCTION" ]]; then
    if [[ "$SKIP_FLOW" == "true" ]]; then
      die "'$FIELD_API' ships with a curated OOTB managed prompt and no --goal/--instruction was given, so there is no template to deploy — and --skip-flow means there is nothing to wire either. Nothing to do. To customize the prompt pass --goal/--instruction; to wire the field into the flow drop --skip-flow."
    fi
    WIRE_ONLY=true
    log_info "OOTB wire-only mode: '$FIELD_API' keeps its curated OOTB prompt; wiring it into the flow (idempotent). Pass --goal/--instruction to also customize the prompt."
  else
    OVERRIDE_SOURCE="${OOTB_MANAGED_TEMPLATE[$FIELD_API]}"
    log_info "OOTB override mode: '$FIELD_API' overrides managed template '$OVERRIDE_SOURCE' (deploys as a new version)."
  fi
fi

# Defaults derived from describe.
[[ -z "$FIELD_LABEL" ]] && FIELD_LABEL="$F_LABEL_DESCRIBED"
[[ -z "$DEV_NAME" ]] && DEV_NAME="Recommend$(echo "$FIELD_API" | sed 's/__c$//' | sed 's/[^A-Za-z0-9]//g')forOpp"
# developerName must start with a letter and be alphanumeric (Recommend<...>forOpp
# always satisfies this, but a custom --name could not).
[[ "$DEV_NAME" =~ ^[A-Za-z][A-Za-z0-9]*$ ]] || die "Template dev name '$DEV_NAME' is invalid (must start with a letter, alphanumeric only). Pass a valid --name."
[[ -z "$FIELD_GOAL" ]] && FIELD_GOAL="what the most appropriate value of this field is, based on the latest conversation signals."
[[ -z "$FIELD_INSTRUCTION" ]] && FIELD_INSTRUCTION="Extract only what is explicitly supported by the data sources."
CHAR_CAP="$F_LEN"

# FLS check for the agent user (non-blocking warn).
AGENT_USER=$(sf data query -q "SELECT Username FROM User WHERE Username LIKE 'salesmanagementagentuser@%'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Username // empty')
if [[ -n "$AGENT_USER" ]]; then
  log_info "Agent user: $AGENT_USER (ensure it has edit FLS on $FIELD_API for autonomous updates)"
else
  log_warn "Could not resolve the agent user; verify $FIELD_API is accessible to the agent's PSG."
fi
echo ""

# ============================================================
# Pre-check — is the template already active? (idempotency guard for #7)
# A redeploy round-trip (Steps 2-3) mints a NEW template version every run, so
# skip it when the template is already active and --force was not passed. Uses
# the same prompt-templates discovery endpoint Step 3 uses to confirm activation.
# ============================================================
# The name to look up in the /einstein/prompt-templates endpoint. An OVERRIDE folds
# into the managed template's record, so its own (un-namespaced) DeveloperName never
# appears there — the managed name does. Use the managed name for active-state reads
# in override mode, and the template's own name otherwise.
# WIRE_ONLY keeps the managed OOTB template (nothing deployed under DEV_NAME), so
# active-state reads and /generations must target the managed template's name.
if [[ "$WIRE_ONLY" == "true" ]]; then
  TEMPLATE_QUERY_NAME="${OOTB_MANAGED_TEMPLATE[$FIELD_API]}"
else
  TEMPLATE_QUERY_NAME="${OVERRIDE_SOURCE:-$DEV_NAME}"
fi

TEMPLATE_ALREADY_ACTIVE=false
# Skip the idempotency shortcut in override mode: the managed template is ALWAYS
# active OOTB, so a query would always read "active" and wrongly skip the override
# deploy. An override is an explicit, opt-in action (--goal/--instruction), so always
# (re)deploy it when requested; --force is only meaningful for standalone templates.
if [[ "$FORCE" != "true" && -z "$OVERRIDE_SOURCE" && "$WIRE_ONLY" != "true" ]]; then
  EXISTING_ACTIVE=$(sf api request rest "/services/data/${API_VERSION}/einstein/prompt-templates" --target-org "$ORG_ALIAS" 2>/dev/null \
    | jq -r --arg n "$DEV_NAME" '.promptRecords[]? | select(.fields.DeveloperName.value==$n) | .fields.IsActive.value' 2>/dev/null | head -1)
  if [[ "$EXISTING_ACTIVE" == "true" ]]; then
    TEMPLATE_ALREADY_ACTIVE=true
  fi
fi

if [[ "$WIRE_ONLY" == "true" ]]; then
  echo "Steps 2-3: SKIPPED — '$FIELD_API' keeps its curated OOTB managed prompt (wire-only mode)."
  log_info "No template deployed. Pass --goal/--instruction to deploy an override of the managed prompt."
  echo ""
elif [[ "$TEMPLATE_ALREADY_ACTIVE" == "true" ]]; then
  echo "Steps 2-3: SKIPPED — template '$DEV_NAME' already exists and is ACTIVE."
  log_info "Not redeploying (would mint a new version). Pass --force to regenerate + redeploy."
  echo ""
else

# ============================================================
# Step 2 — Generate template XML from canonical asset
# ============================================================
echo "Step 2: Generate template XML ($DEV_NAME)"
mkdir -p "$TEMPLATE_DIR"
TEMPLATE_FILE="$TEMPLATE_DIR/${DEV_NAME}.genAiPromptTemplate-meta.xml"
MASTER_LABEL="Recommend ${FIELD_LABEL} for Opportunity"

# Substitute placeholders with python3 (safe with arbitrary text; no sed-escaping traps).
FIELD_API="$FIELD_API" FIELD_LABEL="$FIELD_LABEL" DEV_NAME="$DEV_NAME" \
MASTER_LABEL="$MASTER_LABEL" CHAR_CAP="$CHAR_CAP" FIELD_GOAL="$FIELD_GOAL" \
FIELD_INSTRUCTION="$FIELD_INSTRUCTION" OVERRIDE_SOURCE="$OVERRIDE_SOURCE" \
ASSET="$ASSET_TEMPLATE" OUT="$TEMPLATE_FILE" \
python3 - << 'PYEOF'
import os, re, xml.sax.saxutils as sx
src = open(os.environ["ASSET"], encoding="utf-8").read()
# Drop the leading XML comment (guidance only) so the deployed file is clean.
src = re.sub(r"<!--.*?-->\s*", "", src, count=1, flags=re.DOTALL)
repl = {
    "@@DEVNAME@@":           os.environ["DEV_NAME"],
    "@@MASTERLABEL@@":       os.environ["MASTER_LABEL"],
    "@@FIELD@@":             os.environ["FIELD_API"],
    "@@FIELDLABEL@@":        os.environ["FIELD_LABEL"],
    "@@CHARCAP@@":           os.environ["CHAR_CAP"],
    "@@FIELD_GOAL@@":        os.environ["FIELD_GOAL"],
    "@@FIELD_INSTRUCTION@@": os.environ["FIELD_INSTRUCTION"],
}
for k, v in repl.items():
    # Escape XML special chars in substituted values (they live inside element text).
    src = src.replace(k, sx.escape(v))
# OOTB override mode: the canonical asset ships <overridable>false</overridable>.
# To register as an override of a managed template, replace that element with
# <overrideSource>NAMESPACE__ManagedTemplate</overrideSource>. The platform then
# treats this deploy as a new version of that managed template rather than a new
# standalone prompt (verified on a live org).
ovr = os.environ.get("OVERRIDE_SOURCE", "")
if ovr:
    new_src, n = re.subn(
        r"<overridable>[^<]*</overridable>",
        "<overrideSource>%s</overrideSource>" % sx.escape(ovr),
        src, count=1)
    if n != 1:
        raise SystemExit("expected exactly one <overridable> element to replace for override mode; found %d" % n)
    src = new_src
open(os.environ["OUT"], "w", encoding="utf-8").write(src)
print("  wrote " + os.environ["OUT"] + ((" (override of %s)" % ovr) if ovr else ""))
PYEOF

grep -q "@@" "$TEMPLATE_FILE" && die "Unsubstituted placeholder remains in $TEMPLATE_FILE"
log_pass "Template XML generated (SuggestedNewValue cap = $CHAR_CAP chars)"
echo ""

# ============================================================
# Step 3 — Deterministic deploy + activate (retrieve round-trip)
# ============================================================
echo "Step 3: Deploy and activate template (deterministic round-trip)"

log_try "Deploy (status=Published, no version identifiers)"
DEPLOY1=$(sf project deploy start --source-dir "$TEMPLATE_FILE" --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')
if ! echo "$DEPLOY1" | jq -e '.status == 0' >/dev/null 2>&1; then
  ERR=$(echo "$DEPLOY1" | jq -r '.result.details.componentFailures[0].problem // .message // "unknown"' 2>/dev/null)
  die "Initial template deploy failed: $ERR"
fi
log_pass "Deployed (inactive — no active version yet)"

log_try "Retrieve platform-generated versionIdentifier"
sf project retrieve start --metadata "GenAiPromptTemplate:${DEV_NAME}" --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null \
  || die "Retrieve failed — cannot read versionIdentifier."

# Parse the versionIdentifier as the direct child of <templateVersions> (not a
# file-wide grep) so a future multi-version template can't hand us the wrong id.
# A freshly created template has exactly one version; assert that.
VERSION_ID=$(python3 - "$TEMPLATE_FILE" << 'PYEOF'
import sys, xml.etree.ElementTree as ET
NS = "http://soap.sforce.com/2006/04/metadata"; q = lambda t: "{%s}%s" % (NS, t)
root = ET.parse(sys.argv[1]).getroot()
ids = [tv.findtext(q("versionIdentifier")) for tv in root.findall(q("templateVersions"))]
ids = [i for i in ids if i]
if len(ids) == 1:
    print(ids[0])
elif len(ids) > 1:
    # Unexpected for a new template; take the last (newest) and note it on stderr.
    sys.stderr.write("multiple versionIdentifiers found; using the last\n"); print(ids[-1])
PYEOF
)
[[ -n "$VERSION_ID" ]] || die "No <versionIdentifier> found after retrieve. Template may not have deployed as a version."
log_pass "versionIdentifier = $VERSION_ID"

# Set activeVersionIdentifier (idempotent: replace if present, else insert after <overridable>).
if grep -q "<activeVersionIdentifier>" "$TEMPLATE_FILE"; then
  VERSION_ID="$VERSION_ID" python3 - "$TEMPLATE_FILE" << 'PYEOF'
import os, re, sys
p = sys.argv[1]; s = open(p).read()
s = re.sub(r"<activeVersionIdentifier>[^<]*</activeVersionIdentifier>",
           "<activeVersionIdentifier>%s</activeVersionIdentifier>" % os.environ["VERSION_ID"], s)
open(p, "w").write(s)
PYEOF
else
  VERSION_ID="$VERSION_ID" python3 - "$TEMPLATE_FILE" << 'PYEOF'
import os, re, sys
p = sys.argv[1]; s = open(p).read()
tag = "    <activeVersionIdentifier>%s</activeVersionIdentifier>\n" % os.environ["VERSION_ID"]
# Insert right after the opening <GenAiPromptTemplate ...> line.
s = re.sub(r"(<GenAiPromptTemplate[^>]*>\n)", r"\1" + tag, s, count=1)
open(p, "w").write(s)
PYEOF
fi

log_try "Redeploy to activate"
DEPLOY2=$(sf project deploy start --source-dir "$TEMPLATE_FILE" --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')
if ! echo "$DEPLOY2" | jq -e '.status == 0' >/dev/null 2>&1; then
  ERR=$(echo "$DEPLOY2" | jq -r '.result.details.componentFailures[0].problem // .message // "unknown"' 2>/dev/null)
  die "Activation redeploy failed: $ERR"
fi

# Confirm active via the prompt-templates discovery endpoint. In override mode this
# reads the MANAGED template's record (the override folds into it), which is expected
# to stay active — the successful redeploy above is the real proof the override took.
IS_ACTIVE=$(sf api request rest "/services/data/${API_VERSION}/einstein/prompt-templates" --target-org "$ORG_ALIAS" 2>/dev/null \
  | jq -r --arg n "$TEMPLATE_QUERY_NAME" '.promptRecords[]? | select(.fields.DeveloperName.value==$n) | .fields.IsActive.value' 2>/dev/null | head -1)
if [[ "$IS_ACTIVE" == "true" ]]; then
  if [[ -n "$OVERRIDE_SOURCE" ]]; then
    log_pass "Override deployed — '$OVERRIDE_SOURCE' is ACTIVE with the new version"
  else
    log_pass "Template '$DEV_NAME' is ACTIVE"
  fi
else
  log_warn "Template deployed but active-state read returned '$IS_ACTIVE'. Verify in Prompt Builder."
fi
echo ""

fi  # end template deploy/activate block (skipped when already active without --force)

# ============================================================
# Step 4 — Register the field in the active flow (idempotent, XML-aware)
# ============================================================
if [[ "$SKIP_FLOW" == "true" ]]; then
  log_info "Skipping flow edit (--skip-flow). Field will NOT generate scheduled suggestions until added to $FLOW_API_NAME."
  echo ""
else
  echo "Step 4: Register field in the active suggestion flow"

  FLOW_STATE=$(sf data query -q "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE ApiName='${FLOW_API_NAME}'" --target-org "$ORG_ALIAS" --json 2>/dev/null)
  FLOW_EXISTS=$(echo "$FLOW_STATE" | jq -r '.result.records[0].ApiName // empty')
  FLOW_ACTIVE=$(echo "$FLOW_STATE" | jq -r '.result.records[0].IsActive // empty')

  if [[ -z "$FLOW_EXISTS" ]]; then
    log_warn "Flow '$FLOW_API_NAME' not found. Run create-flow.sh first, then re-run with --skip-flow already applied."
  else
    if [[ "$FLOW_ACTIVE" != "true" ]]; then
      log_warn "Flow '$FLOW_API_NAME' is INACTIVE. It must be Active for suggestions to run (create-flow.sh)."
    fi

    log_try "Retrieve flow"
    mkdir -p "$FLOW_DIR"
    sf project retrieve start --metadata "Flow:${FLOW_API_NAME}" --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null \
      || die "Could not retrieve flow '$FLOW_API_NAME'."
    FLOW_FILE="${FLOW_DIR}/${FLOW_API_NAME}.flow-meta.xml"
    [[ -f "$FLOW_FILE" ]] || die "Flow file not present after retrieve: $FLOW_FILE"

    # Enforce the field cap BEFORE wiring. Count the fields currently wired in the
    # AddOppFieldsToCollection assignment. If the field is already present, adding is
    # a no-op (handled below) and does not count against the cap. If it is new and the
    # flow is already at MAX_SUGGESTION_FIELDS, refuse — the flow can manage no more.
    CAP_RC=0
    CAP_OUT=$(FIELD_API="$FIELD_API" MAX_FIELDS="$MAX_SUGGESTION_FIELDS" python3 - "$FLOW_FILE" << 'PYEOF'
import os, sys
import xml.etree.ElementTree as ET

NS = "http://soap.sforce.com/2006/04/metadata"
q = lambda t: "{%s}%s" % (NS, t)

path = sys.argv[1]
field = os.environ["FIELD_API"]
cap = int(os.environ["MAX_FIELDS"])
root = ET.parse(path).getroot()

target = None
for a in root.findall(q("assignments")):
    name = a.find(q("name"))
    if name is not None and name.text == "AddOppFieldsToCollection":
        target = a
        break
if target is None:
    sys.stderr.write("AddOppFieldsToCollection assignment not found\n")
    sys.exit(3)

fields = []
for item in target.findall(q("assignmentItems")):
    sv = item.find(q("value") + "/" + q("stringValue"))
    if sv is not None and sv.text:
        fields.append(sv.text)

# Field already wired -> adding it is idempotent, never breaches the cap.
if field in fields:
    sys.exit(0)
# New field would push past the cap -> block. Print the wired set for the message.
if len(fields) >= cap:
    sys.stdout.write(", ".join(fields))
    sys.exit(4)
sys.exit(0)
PYEOF
) || CAP_RC=$?
    if [[ "$CAP_RC" == "4" ]]; then
      die "Field cap reached: the suggestion flow already wires $MAX_SUGGESTION_FIELDS fields (${CAP_OUT}). Pipeline Management supports at most $MAX_SUGGESTION_FIELDS managed Opportunity fields. Remove one before adding '$FIELD_API'."
    elif [[ "$CAP_RC" == "3" ]]; then
      die "Could not locate AddOppFieldsToCollection in flow '$FLOW_API_NAME' — cannot verify the field cap."
    fi

    # XML-aware idempotent insert: add a <assignmentItems> for the field into the
    # AddOppFieldsToCollection assignment ONLY if not already present. Preserves
    # namespace + all other content. Exits 2 = already present (no-op).
    RC=0
    FIELD_API="$FIELD_API" python3 - "$FLOW_FILE" << 'PYEOF' || RC=$?
import os, sys
import xml.etree.ElementTree as ET

NS = "http://soap.sforce.com/2006/04/metadata"
ET.register_namespace("", NS)  # keep default namespace, no ns0: prefixes
q = lambda t: "{%s}%s" % (NS, t)

path = sys.argv[1]
field = os.environ["FIELD_API"]
tree = ET.parse(path)
root = tree.getroot()

# Find the AddOppFieldsToCollection assignment.
target = None
for a in root.findall(q("assignments")):
    name = a.find(q("name"))
    if name is not None and name.text == "AddOppFieldsToCollection":
        target = a
        break
if target is None:
    sys.stderr.write("AddOppFieldsToCollection assignment not found\n")
    sys.exit(3)

# Already present? (idempotent)
for item in target.findall(q("assignmentItems")):
    sv = item.find(q("value") + "/" + q("stringValue"))
    if sv is not None and sv.text == field:
        print("  already present: %s" % field)
        sys.exit(2)

# Build a new <assignmentItems> matching the existing shape.
item = ET.SubElement(target, q("assignmentItems"))
ET.SubElement(item, q("assignToReference")).text = "OpportunityFields"
ET.SubElement(item, q("operator")).text = "Add"
val = ET.SubElement(item, q("value"))
ET.SubElement(val, q("stringValue")).text = field

# assignmentItems must precede <connector>; move the new one before it if needed.
children = list(target)
conn = target.find(q("connector"))
if conn is not None:
    target.remove(item)
    idx = children.index(conn)
    target.insert(idx, item)

tree.write(path, encoding="UTF-8", xml_declaration=True)
print("  inserted: %s" % field)
sys.exit(0)
PYEOF
    if [[ "$RC" == "2" ]]; then
      log_pass "Field already in flow collection — no change (idempotent)"
    elif [[ "$RC" == "0" ]]; then
      log_try "Deploy updated flow (status preserved)"
      DEPLOYF=$(sf project deploy start --metadata "Flow:${FLOW_API_NAME}" --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')
      if echo "$DEPLOYF" | jq -e '.status == 0' >/dev/null 2>&1; then
        log_pass "Flow updated — '$FIELD_API' added to OpportunityFields"
      else
        ERR=$(echo "$DEPLOYF" | jq -r '.result.details.componentFailures[0].problem // .message // "unknown"' 2>/dev/null)
        die "Flow deploy failed: $ERR (existing suggestions unaffected — flow not changed on failure)"
      fi
    else
      die "Flow edit helper failed (rc=$RC)."
    fi
  fi
  echo ""
fi

# ============================================================
# Step 5 — Optional synchronous verification via /generations
# ============================================================
if [[ "$VERIFY_WITH_NOTE" == "true" ]]; then
  echo "Step 5: Verify with a seeded note (synchronous /generations)"

  if [[ -z "$OPP_ID" ]]; then
    # Match the pipeline's own eligibility filter (IsClosed=false AND CloseDate
    # within +90 days) so we don't verify against an opp the scheduled flow would
    # skip — that would surface a misleading "no generation" false negative.
    OPP_ID=$(sf data query -q "SELECT Id FROM Opportunity WHERE IsClosed=false AND CloseDate>=TODAY AND CloseDate<=NEXT_N_DAYS:90 ORDER BY LastModifiedDate DESC LIMIT 1" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty')
    [[ -n "$OPP_ID" ]] || die "No eligible open Opportunity found (IsClosed=false, CloseDate within +90 days); pass --opp <OppId>."
  fi
  log_info "Opportunity: $OPP_ID"

  # A caller (e.g. the agent-driven prompt tune-loop) can pass --note with a body
  # tailored to THIS field's goal/instruction, so the seeded grounding signal
  # actually exercises the customized prompt. Absent --note, fall back to a generic
  # note that mentions a few common signals.
  if [[ -n "$NOTE_TEXT" ]]; then
    NOTE_BODY="$NOTE_TEXT"
  else
    NOTE_BODY="Verification note for ${FIELD_LABEL}: Customer flagged budget pressure, a competing vendor, and a timeline slip during the last call."
  fi
  # macOS/BSD `base64` line-wraps at 76 cols (embeds newlines); GNU's `-w0` isn't
  # portable. `tr -d '\n'` strips wraps on both so the value stays single-line and
  # doesn't break the --values string below.
  NOTE_B64=$(printf '%s' "$NOTE_BODY" | base64 | tr -d '\n')

  log_try "Create ContentNote + link to opportunity"
  # Note-seeding is best-effort: `|| true` keeps a create failure from tripping
  # `set -e` so it degrades to the log_warn fallback instead of aborting the run.
  NOTE_ID=$(sf data create record --sobject ContentNote --values "Title='FieldSuggestion Verify ${DEV_NAME}' Content='${NOTE_B64}'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.id // empty' || true)
  if [[ -n "$NOTE_ID" ]]; then
    # ContentNote shares the 069 key prefix with ContentDocument — the note Id IS
    # the ContentDocumentId, so link directly. (The ContentVersion→LatestVersionId
    # subquery returns null on some orgs, silently dropping the link.)
    if sf data create record --sobject ContentDocumentLink --values "ContentDocumentId='${NOTE_ID}' LinkedEntityId='${OPP_ID}' ShareType='V' Visibility='AllUsers'" --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null; then
      log_pass "Seeded note $NOTE_ID and linked to $OPP_ID"
    else
      log_warn "Note $NOTE_ID created but linking to $OPP_ID failed; generation will run against existing grounding data only."
    fi
  else
    log_warn "Could not seed note; running generation against existing grounding data."
  fi

  log_try "POST /generations"
  # In override mode, generate against the MANAGED template name — the override
  # deployed as its new active version, so this exercises exactly the prompt the
  # scheduled pipeline will run. The override's own dev name is not a generatable
  # template (it has no standalone record).
  GEN=$(sf api request rest "/services/data/${API_VERSION}/einstein/prompt-templates/${TEMPLATE_QUERY_NAME}/generations" \
    --method POST --target-org "$ORG_ALIAS" \
    --body "{\"isPreview\":false,\"inputParams\":{\"valueMap\":{\"Input:Opportunity\":{\"value\":{\"id\":\"${OPP_ID}\"}}}},\"additionalConfig\":{\"numGenerations\":1,\"temperature\":0,\"applicationName\":\"PromptTemplateGenerationsInvocable\"}}" 2>/dev/null || echo '{}')
  GEN_TEXT=$(echo "$GEN" | jq -r '.generations[0].text // empty')
  if [[ -n "$GEN_TEXT" ]]; then
    log_pass "Generation succeeded:"
    echo "$GEN_TEXT"
  else
    log_warn "No generation text returned. Response:"
    echo "$GEN" | jq -r '.[0].message // .message // .' 2>/dev/null | head -5
  fi
  echo ""
fi

# ============================================================
# Summary
# ============================================================
echo "Done: $FIELD_API"
if [[ "$WIRE_ONLY" == "true" ]]; then
  echo "  Template : ${OOTB_MANAGED_TEMPLATE[$FIELD_API]} (curated OOTB prompt, unchanged)"
elif [[ -n "$OVERRIDE_SOURCE" ]]; then
  echo "  Template : override of $OVERRIDE_SOURCE (new active version; OOTB prompt customized)"
else
  echo "  Template : $DEV_NAME (active)"
fi
if [[ "$SKIP_FLOW" != "true" ]]; then
  echo "  Flow     : $FIELD_API registered in $FLOW_API_NAME OpportunityFields (idempotent)"
fi
echo ""
echo "Scheduled suggestions land in the AiGenActionItem object (async, ~2-3 min after the daily run)."
echo "To confirm the scheduled path (NOT the synchronous test above):"
echo "  1. Baseline:  sf data query -q \"SELECT COUNT() FROM AiGenActionItem WHERE CreatedDate=TODAY\" --target-org $ORG_ALIAS"
echo "  2. Wait >= 240s after the flow's scheduled run (WhatId is not SOQL-queryable — use the COUNT delta)."
echo "  3. Re-count and compare. New rows = suggestions generated."
