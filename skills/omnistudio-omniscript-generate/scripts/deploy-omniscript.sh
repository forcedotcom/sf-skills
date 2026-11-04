#!/bin/bash
# Deploy an OmniScript and verify activation.
# Usage: ./deploy-omniscript.sh <Type> <SubType> <Language> <Version> <org>
# Example: ./deploy-omniscript.sh ServiceRequest NewCase English 1 myOrg
# Metadata member name is <Type>_<SubType>_<Language>_<Version> (e.g. ServiceRequest_NewCase_English_1).
# Run AFTER deploying all dependencies (DataRaptors, Integration Procedures).

TYPE="${1:?Usage: $0 <Type> <SubType> <Language> <Version> <org>}"
SUBTYPE="${2:?}"
LANGUAGE="${3:?}"
VERSION="${4:?}"
ORG="${5:?}"
NAME="${TYPE}_${SUBTYPE}_${LANGUAGE}_${VERSION}"

# Validate inputs to prevent SOQL injection
for var in "$TYPE" "$SUBTYPE" "$LANGUAGE" "$VERSION"; do
  if [[ ! "$var" =~ ^[a-zA-Z0-9_\ ]+$ ]]; then
    echo "ERROR: Invalid input '$var'. Only alphanumeric, underscores, and spaces allowed." >&2
    exit 1
  fi
done

echo "Step 1: Verify prerequisites — check org auth"
sf org display -o "${ORG}" || { echo "ERROR: Org '${ORG}' is not authenticated. Run: sf org login web --alias ${ORG}"; exit 1; }

echo "Step 2: Deploy OmniScript metadata"
sf project deploy start -m "OmniScript:${NAME}" -o "${ORG}"
if [ $? -ne 0 ]; then
  echo "ERROR: Deployment failed. To recover:"
  echo "  1. Check the error message above for the specific cause."
  echo "  2. Metadata API deploys are transactional, so a failed deploy does not leave a partial OmniProcess record."
  echo "     If a stray record exists, check it with:"
  echo "     sf data query -q \"SELECT Id,Name,IsActive,VersionNumber FROM OmniProcess WHERE Type='${TYPE}' AND SubType='${SUBTYPE}' AND Language='${LANGUAGE}' AND IsIntegrationProcedure=false\" -o ${ORG}"
  echo "     and review it before deleting anything."
  echo "  3. Fix the issue and re-run this script."
  exit 1
fi

echo "Step 3: Verify activation"
sf data query \
  -q "SELECT Id,Name,Type,SubType,Language,IsActive,VersionNumber FROM OmniProcess WHERE Type='${TYPE}' AND SubType='${SUBTYPE}' AND Language='${LANGUAGE}' AND IsIntegrationProcedure=false AND IsActive=true LIMIT 5" \
  -o "${ORG}"
