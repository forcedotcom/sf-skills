#!/usr/bin/env python3
"""
Send data to Data Cloud through the Ingestion API.

Prerequisites:
  pip install PyJWT cryptography requests

Usage:
  1. Copy .env.example to .env and fill in your values
  2. python3 send-data.py

See README.md in this folder for setup notes.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import jwt
import requests


def load_env_file() -> None:
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


load_env_file()

CONSUMER_KEY = os.environ["CONSUMER_KEY"]
SF_USERNAME = os.environ["SF_USERNAME"]
SF_LOGIN_URL = os.environ.get("SF_LOGIN_URL", "https://login.salesforce.com")
TENANT_URL = os.environ["TENANT_URL"]
PRIVATE_KEY_FILE = os.environ["PRIVATE_KEY_FILE"]
CONNECTOR_NAME = os.environ["CONNECTOR_NAME"]
OBJECT_NAME = os.environ["OBJECT_NAME"]


def get_cdp_token() -> str:
    """Authenticate: JWT -> Salesforce access token -> Data Cloud token."""
    private_key = Path(PRIVATE_KEY_FILE).read_text()

    claim = {
        "iss": CONSUMER_KEY,
        "sub": SF_USERNAME,
        "aud": SF_LOGIN_URL,
        "exp": int(time.time()) + 300,
    }
    assertion = jwt.encode(claim, private_key, algorithm="RS256")

    token_data = requests.post(
        f"{SF_LOGIN_URL}/services/oauth2/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        timeout=60,
    ).json()

    if "access_token" not in token_data:
        raise RuntimeError(f"Salesforce auth failed: {token_data}")

    cdp_data = requests.post(
        f"{token_data['instance_url']}/services/a360/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:salesforce:grant-type:external:cdp",
            "subject_token": token_data["access_token"],
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        },
        timeout=60,
    ).json()

    if "access_token" not in cdp_data:
        raise RuntimeError(f"Data Cloud token exchange failed: {cdp_data}")

    return cdp_data["access_token"]


def send_records(cdp_token: str, records: list[dict[str, str]]) -> tuple[int, str]:
    """Send records to the Ingestion API."""
    url = f"{TENANT_URL}/api/v1/ingest/sources/{CONNECTOR_NAME}/{OBJECT_NAME}"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {cdp_token}",
            "Content-Type": "application/json",
        },
        json={"data": records},
        timeout=60,
    )
    return response.status_code, response.text


if __name__ == "__main__":
    print("Authenticating...")
    token = get_cdp_token()
    print("Data Cloud token acquired")

    records = [
        {
            "ScanId": str(uuid.uuid4()),
            "EventId": "EVT-001",
            "AttendeeId": "ATT-001",
            "Scantime": datetime.now(timezone.utc).isoformat(),
            "Room": "Main Hall",
        },
        {
            "ScanId": str(uuid.uuid4()),
            "EventId": "EVT-001",
            "AttendeeId": "ATT-002",
            "Scantime": datetime.now(timezone.utc).isoformat(),
            "Room": "Workshop A",
        },
        {
            "ScanId": str(uuid.uuid4()),
            "EventId": "EVT-001",
            "AttendeeId": "ATT-003",
            "Scantime": datetime.now(timezone.utc).isoformat(),
            "Room": "Workshop B",
        },
    ]

    print(f"Sending {len(records)} records to {CONNECTOR_NAME}/{OBJECT_NAME}...")
    status, body = send_records(token, records)
    print(f"Response: {status} {body}")

    if status == 202:
        print("\nData accepted. Records typically appear in Data Cloud within a few minutes.")
        print(
            "Query with: sf data360 query sql -o <org> --sql 'SELECT * FROM \"<DLO_NAME>__dll\" LIMIT 10'"
        )
    else:
        print("\nIngestion failed. Check the response above for details.")
