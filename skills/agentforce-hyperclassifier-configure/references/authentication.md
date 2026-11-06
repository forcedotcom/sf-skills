# Customer-org ECA authentication

Follow the current [Models API authentication guide](https://developer.salesforce.com/docs/ai/agentforce/guide/models-api-authentication.html). The org needs Einstein/Models API availability, permission to use the requested models, and an External Client App configured for OAuth client credentials and JWT access tokens for named users.

Start with [CLI/ECA onboarding](onboarding.md). The CLI's org-alias session token is for searching/configuring the ECA through customer org APIs; it is never the gateway inference credential. The setup helper can prepare and deploy a dedicated ECA, import supplied credentials, and save an org-bound profile for subsequent `--target-org` runs.

Configure the ECA in the customer's org:

1. Enable OAuth. Select **Manage user data via APIs (`api`)**, **Perform requests at any time (`refresh_token`, `offline_access`)**, and **Access the Salesforce API Platform (`sfap_api`)**, as specified by the Models API guide.
2. Enable **Client Credentials Flow** and **Issue JSON Web Token (JWT)-based access tokens for named users**.
3. Configure the app's policy, permitted users and **Run As** user. Assign the app and necessary model access to that user using the org's normal permission process. Do not broaden object permissions merely to fix authentication.
4. Retrieve the Consumer Key and Consumer Secret privately. The code uses client credentials; it does not use user-agent, hybrid user-agent, username/password, or browser session tokens.

Copy `assets/customer-org.env.example` to a private location **outside the skill and source repository**, restrict it to the user (`chmod 600 /private/path/customer-org.env` on macOS/Linux), and populate it locally. Values are literal; the parser never executes the file, expands shell variables, or performs command substitution. Only the three documented keys are accepted; whole-line comments and quoted values are allowed. Alternatively set those keys securely in the process environment. An explicit file overrides environment values.

The token request is a form POST to the supplied HTTPS Salesforce My Domain:

```text
/services/oauth2/token
grant_type=client_credentials
client_id=<consumer key>
client_secret=<consumer secret>
```

The implementation permits exact HTTPS My Domain origins: `<name>.my.salesforce.com` and `<name>.<partition>.my.salesforce.com`, where partition is `sandbox`, `develop`, `scratch`, `demo`, `trailblaze` or `patch`. It rejects extra labels, paths, ports, user information, query strings and fragments, validates TLS, and refuses redirects. No API key or credentials are sent to third-party services. Tokens are kept only in memory, refreshed before expiry, and refreshed once after HTTP 401. JWT claims are decoded to check token shape/expiry; Salesforce verifies the signature when accepting the API call.

Common failures:

- OAuth HTTP 400/401: verify the key/secret, enabled client credentials flow, Run As user and preauthorization.
- Token is not a signed JWT: enable the named-user JWT option; a Salesforce CLI session token alone does not establish gateway access.
- Inference HTTP 401/403: check `sfap_api`, effective user/model permissions, ECA policy and org availability.
- Inference HTTP 404 or an incompatible response: the full-description contract may not be available. Stop and report that limitation; do not substitute a different classifier.
- HTTP 429/5xx: bounded retry applies. Retry count defaults to one and can be set to zero. Both numeric and HTTP-date `Retry-After` values are honored up to a 30-second wait; a longer cooldown stops the call with a retry-later diagnostic instead of retrying early. Connection and HTTP protocol/read failures use the same sanitized service-error path. Timed-out inference may already have consumed credits.

Inference can consume the customer's model credits. Dry runs make no calls. The budget counts logical inference calls; retries, a possible 401 replay, and OAuth add HTTP attempts. At most `2 * (retries + 1)` inference HTTP attempts are possible per logical inference call. The runtime timeout applies per HTTP attempt. Authentication failures are not routing errors.
