#!/usr/bin/env bash
# Preflight: is this org entitled for Agentforce Email-to-Case (the BotEmailDefinition type)?
#
# describeMetadata gates BotEmailDefinition on BOTH orgAccess=orgHasAgentforceServiceAgentEmail
# (the composite ASA-email entitlement) AND API version >= 68. Neither is SOQL-queryable, but a
# read-only metadata describe surfaces the type only when both hold — so this single call subsumes
# the entitlement check and the v68 version gate, and needs no agent to exist yet.
#
# Exit 0  -> org is entitled; safe to delegate agent creation + channel wiring.
# Exit 3  -> type absent (not entitled, or below API v68); caller must STOP before creating an agent.
# Exit !=0/3 -> the org could not be reached/described; treat as inconclusive, not "not entitled".
set -euo pipefail

ORG="${1:?usage: check-agent-email-capability.sh <target-org-alias>}"

# Resolve the org's TRUE max supported API version and pin the describe to it. describeMetadata
# filters types by the request's API version (isInContextVersion), so running below v68 would filter
# BotEmailDefinition out even on an entitled org. Do NOT use `sf org display`'s apiVersion here: that
# is a cached instanceApiVersion that can lag the org's real max (and is not overridden by
# --api-version), so an upgraded-but-not-re-authed org could resolve low and yield a false "not
# entitled". Query /services/data (the live version list) and take the highest.
API=$(sf api request rest --target-org "$ORG" "/services/data" \
  | python3 -c "import sys, json; print(max((v['version'] for v in json.load(sys.stdin)), key=float))")

sf org list metadata-types --target-org "$ORG" --api-version "$API" --json \
  | python3 -c "import sys, json; types = {m['xmlName'] for m in json.load(sys.stdin)['result']['metadataObjects']}; sys.exit(0 if 'BotEmailDefinition' in types else 3)"
