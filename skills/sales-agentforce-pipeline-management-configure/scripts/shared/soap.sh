#!/bin/bash
# Shared library for SOAP Metadata API response parsing
#
# Functions:
#   redact_token <input> - Redacts session IDs and Bearer tokens from error messages
#   parse_soap_response <xml> <field> <http_status> - Classifies SOAP responses
#
# Returns:
#   "true" - field is enabled
#   "false" - field is explicitly disabled or omitted (setting is off)
#   "AUTH_ERROR:<fault>" - authentication/authorization failure
#   "TYPE_UNAVAILABLE:<fault>" - org lacks license/edition for this feature
#   "NETWORK_ERROR" - network/service error (empty response, 5xx, malformed XML)

# Redact session IDs and Bearer tokens from error messages
# Args: $1 = input string
# Returns: string with tokens replaced by [REDACTED]
#
# Salesforce session IDs start with the 15/18-char org id (00D...) followed by
# '!' and a signature segment that contains '.', '=', '-', '+' in addition to
# alphanumerics. Match greedily up to the next whitespace or XML tag boundary
# ('<') so the whole token tail is redacted, not just its leading run.
redact_token() {
  local input="$1"
  printf '%s' "$input" | sed 's/00D[^ <]*/[REDACTED]/g; s/Bearer [^ ]*/Bearer [REDACTED]/g'
}

# Parse SOAP Metadata API response and classify the result
# Args:
#   $1 = raw SOAP XML response
#   $2 = field name to extract (e.g., "enableEinsteinGptPlatform")
#   $3 = HTTP status code (e.g., "200", "503")
# Returns: classification string (see header comments)
parse_soap_response() {
  local xml_response="$1"
  local field_name="$2"
  local http_status="$3"

  # Validate field_name to prevent regex injection in grep patterns below
  if [[ ! "$field_name" =~ ^[A-Za-z0-9_]+$ ]]; then
    echo "NETWORK_ERROR"
    return 0
  fi

  # Disable pipefail locally to allow grep failures without aborting
  local old_opts="$-"
  set +e

  # Check for network/service errors first (non-2xx status or empty response)
  if [[ -z "$xml_response" ]] || [[ "$http_status" != "200" && "$http_status" != "201" ]]; then
    # Restore pipefail before returning
    if [[ "$old_opts" =~ e ]]; then set -e; fi
    echo "NETWORK_ERROR"
    return 0
  fi

  # Check for SOAP Fault (auth, permission, or type errors)
  # Handle both standard and namespace-prefixed faults
  local fault_code=""
  if echo "$xml_response" | grep -q "<soapenv:Fault>\\|<sf:Fault>\\|<Fault>"; then
    # Extract faultcode - try multiple patterns for different namespace conventions
    fault_code=$(echo "$xml_response" | grep -o "<faultcode>[^<]*</faultcode>" | sed 's/<[^>]*>//g' | head -1)
    if [[ -z "$fault_code" ]]; then
      fault_code=$(echo "$xml_response" | grep -o "<sf:faultcode>[^<]*</sf:faultcode>" | sed 's/<[^>]*>//g' | head -1)
    fi
    if [[ -z "$fault_code" ]]; then
      # Handle fully-qualified fault codes like "sf:INVALID_SESSION_ID"
      fault_code=$(echo "$xml_response" | grep -oE "faultcode>[^<]*</.*faultcode" | sed 's/<[^>]*>//g' | sed 's/.*://' | head -1)
    fi

    if [[ -n "$fault_code" ]]; then
      # Extract faultstring for context (will be redacted)
      local fault_string=""
      fault_string=$(echo "$xml_response" | grep -o "<faultstring>[^<]*</faultstring>" | sed 's/<[^>]*>//g' | head -1 || echo "")
      if [[ -z "$fault_string" ]]; then
        fault_string=$(echo "$xml_response" | grep -o "<sf:faultstring>[^<]*</sf:faultstring>" | sed 's/<[^>]*>//g' | head -1 || echo "")
      fi

      # Redact tokens from fault string
      if [[ -n "$fault_string" ]]; then
        fault_string=$(redact_token "$fault_string")
      fi

      # Classify by fault type
      # INVALID_TYPE = org lacks license/edition - distinct from auth failures
      if echo "$fault_code" | grep -qi "INVALID_TYPE"; then
        if [[ "$old_opts" =~ e ]]; then set -e; fi
        echo "TYPE_UNAVAILABLE:${fault_code}${fault_string:+:$fault_string}"
        return 0
      fi

      # All other faults are auth/permission errors
      if [[ "$old_opts" =~ e ]]; then set -e; fi
      echo "AUTH_ERROR:${fault_code}${fault_string:+:$fault_string}"
      return 0
    fi
  fi

  # Check if response is valid XML with the expected structure
  # If it's HTML or malformed XML, treat as network error
  if ! echo "$xml_response" | grep -q "<readMetadataResponse>\\|<updateMetadataResponse>"; then
    if [[ "$old_opts" =~ e ]]; then set -e; fi
    echo "NETWORK_ERROR"
    return 0
  fi

  # Check for closing envelope tag - if missing, XML is truncated
  if ! echo "$xml_response" | grep -q "</soapenv:Envelope>"; then
    if [[ "$old_opts" =~ e ]]; then set -e; fi
    echo "NETWORK_ERROR"
    return 0
  fi

  # Extract field value - try to find <field>true/false</field>
  # head -1 collapses multi-record responses to the first match so two records
  # never produce a two-line value that fails the == comparisons below.
  local field_value=""
  field_value=$(echo "$xml_response" | grep -o "<${field_name}>[^<]*</${field_name}>" | grep -o "true\\|false" | head -1 || echo "")

  if [[ "$field_value" == "true" ]]; then
    if [[ "$old_opts" =~ e ]]; then set -e; fi
    echo "true"
    return 0
  fi

  # If field is explicitly false OR field is omitted entirely, treat as disabled.
  # Salesforce omits boolean settings fields when they're off rather than
  # emitting <field>false</field>, so an absent field inside an otherwise valid
  # readMetadataResponse is the disabled state, not an error.
  if [[ "$field_value" == "false" ]] || [[ -z "$field_value" ]]; then
    if [[ "$old_opts" =~ e ]]; then set -e; fi
    echo "false"
    return 0
  fi

  # Shouldn't reach here, but if we do, treat as network error (unexpected response format)
  if [[ "$old_opts" =~ e ]]; then set -e; fi
  echo "NETWORK_ERROR"
  return 0
}
