#!/bin/bash
# Verify no duplicate Type/SubType/Language exists before creating a new OmniScript.
# Usage: ./check-duplicate-omniscript.sh <Type> <SubType> <Language> <org>
# Example: ./check-duplicate-omniscript.sh ServiceRequest NewCase English myOrg

TYPE="${1:?Usage: $0 <Type> <SubType> <Language> <org>}"
SUBTYPE="${2:?}"
LANGUAGE="${3:?}"
ORG="${4:?}"

sf data query \
  -q "SELECT Id,Name,Type,SubType,Language,IsActive,VersionNumber FROM OmniProcess WHERE Type='${TYPE}' AND SubType='${SUBTYPE}' AND Language='${LANGUAGE}' AND OmniProcessType='OmniScript' LIMIT 10" \
  -o "${ORG}"
