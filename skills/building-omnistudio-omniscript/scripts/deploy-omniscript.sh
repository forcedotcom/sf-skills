#!/bin/bash
# Deploy an OmniScript and verify activation.
# Usage: ./deploy-omniscript.sh <Name> <Type> <SubType> <org>
# Example: ./deploy-omniscript.sh ServiceRequest_NewCase_English ServiceRequest NewCase myOrg
# Run AFTER deploying all dependencies (DataRaptors, Integration Procedures).

NAME="${1:?Usage: $0 <Name> <Type> <SubType> <org>}"
TYPE="${2:?}"
SUBTYPE="${3:?}"
ORG="${4:?}"

echo "Step 1: Verify prerequisites — check org auth"
sf org display -o "${ORG}" || { echo "ERROR: Org '${ORG}' is not authenticated. Run: sf org login web --alias ${ORG}"; exit 1; }

echo "Step 2: Deploy OmniScript metadata"
sf project deploy start -m "OmniScript:${NAME}" -o "${ORG}"
if [ $? -ne 0 ]; then
  echo "ERROR: Deployment failed. To recover:"
  echo "  1. Check the error message above for the specific cause."
  echo "  2. If a partial OmniProcess record was created, deactivate and delete it:"
  echo "     sf data delete record -s OmniProcess -w \"Name='${NAME}'\" -o ${ORG}"
  echo "  3. Fix the issue and re-run this script."
  exit 1
fi

echo "Step 3: Verify activation"
sf data query \
  -q "SELECT Id,Name,Type,SubType,Language,IsActive,VersionNumber FROM OmniProcess WHERE Type='${TYPE}' AND SubType='${SUBTYPE}' AND OmniProcessType='OmniScript' AND IsActive=true LIMIT 5" \
  -o "${ORG}"
