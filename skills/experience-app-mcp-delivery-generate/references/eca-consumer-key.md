# ECA client ID lookup

This delivery skill owns consumer-key retrieval. Run its helper from the selected SFDX project root; `<skill-dir>` is this skill's absolute directory.

```bash
node "<skill-dir>/scripts/retrieve_eca_consumer_key.mjs" <target-org-alias> <ECA_DEV_NAME> --json
```

The helper reads the project's `sourceApiVersion`, queries `ExternalClientApplication` by exact `DeveloperName`, and requests only the public key using GET `/services/data/v<version>/apps/oauth/credentials/<ECA-record-id>?part=key`. Do not query a `ConsumerKey` sObject field or retrieve a consumer secret.

Default successful output is the public consumer key. With `--json`, the response contains `apiVersion`, `ecaDeveloperName`, `ecaId`, `oauthConsumerId`, and `clientId`. Only `clientId` is the public OAuth client ID; the other IDs identify Salesforce records. Reuse a successful same-session lookup for the same selected org and ECA. Never copy access or refresh tokens into an output.

### Consumer-key retrieval

| Exit | Meaning | Next step |
|---|---|---|
| `2` | Lookup, API, or response validation failed | Resolve the reported failure; it doesn't establish that the ECA or consumer is missing |
| `3` | The query succeeded and no ECA matched the DeveloperName | Confirm the exact ECA name and deployment; allow for propagation before retrying |
| `4` | An OAuth consumer must be selected | Show the returned consumer names and IDs and ask the user which is intended |

After the user selects an OAuth consumer, rerun the helper owned by `experience-app-mcp-delivery-generate` with that ID. Run it from the selected SFDX project root:
```bash
node "<skill-dir>/scripts/retrieve_eca_consumer_key.mjs" <target-org-alias> <ECA_DEV_NAME> <oauth-consumer-id>
```

For a permission error, report that the authenticated user needs `View External Client App Consumer Secrets in Metadata` and point the user to the ECA OAuth consumer details in Setup. Retry only `retrieve_eca_consumer_key.mjs` after resolving the failure, or have the user read the consumer key from that screen. Never retrieve the consumer secret. Use the lookup command and output contract above.
