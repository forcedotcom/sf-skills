# Authentication & Session Handling

This skill mutates a live org. Getting authentication wrong writes to
the wrong place. Follow this recipe exactly.

## Discovering the target org

Before making any API call:

1. If the user supplied a `--target-org <alias>` value, use it verbatim.
2. If they did not, run `sf org list --json` and present the list of
   aliases. Ask the user which to use. Do **not** default to the
   `defaultusername` — the default is frequently a production alias for
   internal users.

## Verifying the session

Once an alias is chosen:

```bash
sf org display --target-org <alias> --json
```

Check the result:

- `result.connectedStatus` should be `Connected`.
- `result.instanceUrl` should be present.
- `result.apiVersion` gives the exact `vXX.0` to substitute into REST
  paths — do not hardcode a version.

If the command exits non-zero, or `connectedStatus` is not
`Connected`, the session has expired. Ask the user to run:

```bash
sf org login web --alias <alias>
```

Do **not** attempt to run `sf org login` on the user's behalf — it
opens a browser and requires user consent. Wait for the user to confirm
they have re-logged in, then re-verify.

## Making the request

Two supported paths:

### Path A — `sf api request rest` (preferred)

```bash
sf api request rest \
  --target-org <alias> \
  --method PATCH \
  "/services/data/vXX.0/tooling/sobjects/RemoteProxy/<Id>" \
  --body '{"EndpointUrl":"https://...","IsActive":true}'
```

The CLI handles the access token — you never touch it directly, so
there is no token-leak surface on this path.

### Path B — `curl` fallback

Only when the CLI is unavailable. Read the access token and instance
URL from the `sf org display` JSON, then:

```bash
curl -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"EndpointUrl":"https://...","IsActive":true}' \
  "$INSTANCE_URL/services/data/vXX.0/tooling/sobjects/RemoteProxy/<Id>"
```

**Token handling rules on the fallback path**:

- Never echo `$TOKEN` to the console or a log file.
- Never include the full `sf org display` output in the summary — the
  `accessToken` field is present.
- Prefer stdin or a temp file with `chmod 600` if the token must be
  materialized.
- Redact `Bearer …` from any error output surfaced to the user.

## Handling 401 mid-run

An access token can expire between phases (common on longer runs). On
HTTP 401 from any entry:

1. Immediately stop dispatching further requests in the current phase.
2. Wait for in-flight requests to complete or timeout.
3. Surface a single 401 message to the user with instructions to
   re-authenticate via `sf org login web --alias <alias>`.
4. Offer to resume from the failing phase (do not re-run completed
   phases — the earlier PATCHes were already applied).

Never silently re-issue the request with a stale token, and never
attempt to refresh the token by hand.
