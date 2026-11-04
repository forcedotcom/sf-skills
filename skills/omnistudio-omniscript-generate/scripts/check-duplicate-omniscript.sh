#!/bin/bash
# Verify no duplicate Type/SubType/Language exists before creating a new OmniScript.
# Usage: ./check-duplicate-omniscript.sh <Type> <SubType> <Language> <org>
# Example: ./check-duplicate-omniscript.sh ServiceRequest NewCase English myOrg

TYPE="${1:?Usage: $0 <Type> <SubType> <Language> <org>}"
SUBTYPE="${2:?}"
LANGUAGE="${3:?}"
ORG="${4:?}"

# Validate inputs to prevent SOQL injection
for var in "$TYPE" "$SUBTYPE" "$LANGUAGE"; do
  if [[ ! "$var" =~ ^[a-zA-Z0-9_\ ]+$ ]]; then
    echo "ERROR: Invalid input '$var'. Only alphanumeric, underscores, and spaces allowed." >&2
    exit 1
  fi
done

sf data query \
  -q "SELECT Id,Name,Type,SubType,Language,IsActive,VersionNumber FROM OmniProcess WHERE Type='${TYPE}' AND SubType='${SUBTYPE}' AND Language='${LANGUAGE}' AND IsIntegrationProcedure=false LIMIT 10" \
  -o "${ORG}"
