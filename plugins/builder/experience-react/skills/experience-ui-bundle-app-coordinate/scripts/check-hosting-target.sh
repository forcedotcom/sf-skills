#!/usr/bin/env bash
# Check which hosting target is configured in .uibundle-meta.xml files

# Find all .uibundle-meta.xml files
META_FILES=$(find . -name "*.uibundle-meta.xml" -type f 2>/dev/null)

if [ -z "$META_FILES" ]; then
  echo "ERROR: No .uibundle-meta.xml files found"
  exit 1
fi

# Check for ExperienceSite target
if echo "$META_FILES" | xargs grep -q '<target>ExperienceSite</target>' 2>/dev/null; then
  echo "ExperienceSite"
  exit 0
fi

# Check for CustomApplication target
if echo "$META_FILES" | xargs grep -q '<target>CustomApplication</target>' 2>/dev/null; then
  echo "CustomApplication"
  exit 0
fi

# No valid target found
echo "ERROR: No valid hosting target found in .uibundle-meta.xml"
exit 1
