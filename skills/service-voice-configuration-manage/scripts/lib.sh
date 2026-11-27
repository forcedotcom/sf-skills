#!/usr/bin/env bash
# Shared constants/helpers for the voice-config scripts (sourced, not run directly).
# Connect calls use `sf api request rest`; never extract the access token.

set -euo pipefail

API_VERSION="v68.0"
# Base path for the Voice Configuration Connect API (native Contact Center voice-config API).
VC_BASE="services/data/${API_VERSION}/connect/thb-voice-config/v1"

# Percent-encode a value for safe use in a URL (unreserved chars stay literal).
urlenc() {
  local s="$1" i c out=""
  for (( i=0; i<${#s}; i++ )); do
    c="${s:i:1}"
    case "$c" in
      [a-zA-Z0-9.~_-]) out+="$c" ;;
      *) printf -v c '%%%02X' "'$c"; out+="$c" ;;
    esac
  done
  printf '%s' "$out"
}
