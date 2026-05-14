# Ingestion API example

This folder contains a minimal, public-safe example for sending records into Salesforce Data Cloud through the Ingestion API.

## What this example assumes

Before running `send-data.py`, complete the connect/prepare setup steps:

1. create an Ingestion API connector
2. upload the schema with `sf data360 connection schema-upsert`
3. create the corresponding data stream in the UI if your org requires that step

Related connector definitions live in:
- [../../../connecting-datacloud/examples/connections/ingest-api-connection.json](../../../connecting-datacloud/examples/connections/ingest-api-connection.json)
- [../../../connecting-datacloud/examples/connections/ingest-api-schema.json](../../../connecting-datacloud/examples/connections/ingest-api-schema.json)

## Prerequisites

```bash
pip install PyJWT cryptography requests
```

## Setup

```bash
cd skills/preparing-datacloud/examples/ingestion-api
cp .env.example .env
# edit .env with your values
python3 send-data.py
```

## Environment variables

- `CONSUMER_KEY` — external client app consumer key
- `CONSUMER_SECRET` — external client app consumer secret if your auth flow needs it
- `SF_USERNAME` — Salesforce username used for JWT auth
- `SF_LOGIN_URL` — login host such as `https://login.salesforce.com`
- `TENANT_URL` — Data Cloud tenant URL such as `https://<tenant>.c360a.salesforce.com`
- `PRIVATE_KEY_FILE` — path to the JWT private key
- `CONNECTOR_NAME` — Ingestion API connector name
- `OBJECT_NAME` — uploaded schema object name

## Notes

- auth is a staged flow: JWT → Salesforce token → Data Cloud token
- the ingestion endpoint uses the Data Cloud tenant URL, not the Salesforce instance URL
- `202` means the payload was accepted for processing
- validation failures often appear in the Problem Records DLO family
