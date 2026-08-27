# Error Handling — All Modes

Never expose raw API error messages, stack traces, or JSON payloads to the user. Map response status codes to plain-language messages.

## Mode A — Configure a test provider

| Status | User-facing message |
|---|---|
| 400 | "The request was invalid. Check that the provider ID and pipeline ID are correct." |
| 403 | "You don't have permission to configure test providers on this pipeline." |
| 404 | "The pipeline or test provider was not found." |
| 409 | "That provider appears to already be configured on this pipeline. To pick up new suites, re-sync it instead." |
| 500 | "A server error occurred. Try again in a few minutes." |

## Mode B — Sync a configured provider

| Status | User-facing message |
|---|---|
| 400 | "The sync request was invalid. Check that the provider ID and pipeline ID are correct." |
| 403 | "You don't have permission to sync test providers on this pipeline." |
| 404 | "The pipeline or test provider was not found." |
| 500 | "A server error occurred. Try again in a few minutes." |

## Mode C — Configure a quality gate

| Status | User-facing message |
|---|---|
| 400 | "The quality gate configuration is invalid. Check that all rule types and thresholds are correct." |
| 403 | "You don't have permission to configure quality gates on this org." |
| 500 | "A server error occurred. Try again in a few minutes." |

## Prerequisite / environment errors

| Error condition | Response |
|---|---|
| `sf org list` fails entirely | "Could not reach the Salesforce CLI. Make sure `sf` is installed and on your PATH." |
| `sf org display` returns auth error | Surface plain-language re-auth instructions. Do not expose the raw error. |
| `DevopsPipeline` query fails with 5xx | "The DevOps Center org is returning a server error. Try again in a few minutes." |
| Any check throws unexpectedly | "Something went wrong checking prerequisites. Error: [plain summary]. Let's try again — or resolve it manually and let me know when ready." |
