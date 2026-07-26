"""Salesforce org authentication and credential management.

Provides functions for authenticating to Salesforce orgs and managing
credentials via environment variables.
"""

import json
import os
import subprocess
import sys
from typing import Tuple


def authenticate_to_org(org_alias: str) -> bool:
    """Authenticate to Salesforce org and set environment variables.
    
    Uses Salesforce CLI to authenticate and sets SF_TOKEN and SF_INSTANCE
    environment variables for use by other modules.
    
    Args:
        org_alias: Salesforce org alias (e.g., "GDO_TEST_001")
        
    Returns:
        True if authentication successful, False otherwise
        
    Raises:
        No exceptions raised - errors are printed to stderr and False is returned
    """
    os.environ["SF_ORG"] = org_alias
    display_result = subprocess.run(
        ["sf", "org", "display", "--target-org", org_alias, "--json"],
        capture_output=True,
        text=True,
    )
    if display_result.returncode != 0:
        print(f"✗ Error authenticating to org '{org_alias}': {display_result.stderr}", file=sys.stderr)
        return False

    token_result = subprocess.run(
        ["sf", "org", "auth", "show-access-token", "--target-org", org_alias, "--json"],
        capture_output=True,
        text=True,
    )
    if token_result.returncode != 0:
        print(f"✗ Error retrieving access token for '{org_alias}': {token_result.stderr}", file=sys.stderr)
        return False

    try:
        os.environ["SF_INSTANCE"] = json.loads(display_result.stdout)["result"]["instanceUrl"]
        os.environ["SF_TOKEN"] = json.loads(token_result.stdout)["result"]["accessToken"]
        print(f"✓ Authenticated to org '{org_alias}'")
        return True
    except (json.JSONDecodeError, KeyError) as e:
        print(f"✗ Error parsing org data: {e}", file=sys.stderr)
        return False


def get_org_info(org_alias: str) -> Tuple[str, str]:
    """Get org access token and instance URL without setting environment variables.
    
    Args:
        org_alias: Salesforce org alias
        
    Returns:
        Tuple of (access_token, instance_url)
        
    Raises:
        ValueError: If authentication fails or org data cannot be parsed
    """
    display_result = subprocess.run(
        ["sf", "org", "display", "--target-org", org_alias, "--json"],
        capture_output=True,
        text=True,
    )
    if display_result.returncode != 0:
        raise ValueError(f"Failed to authenticate to org '{org_alias}': {display_result.stderr}")

    token_result = subprocess.run(
        ["sf", "org", "auth", "show-access-token", "--target-org", org_alias, "--json"],
        capture_output=True,
        text=True,
    )
    if token_result.returncode != 0:
        raise ValueError(f"Failed to retrieve access token for '{org_alias}': {token_result.stderr}")

    try:
        instance = json.loads(display_result.stdout)["result"]["instanceUrl"]
        token = json.loads(token_result.stdout)["result"]["accessToken"]
        return token, instance
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse org data: {e}")
