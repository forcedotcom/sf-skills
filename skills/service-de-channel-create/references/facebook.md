# Facebook Messenger — OAuth, page selection, request body, gotchas

`MESSAGE_TYPE=Facebook`. Platform key is the **Facebook Page ID** (numeric, ~15 digits). Unlike the
other types, Facebook resolves its platform key via a browser-based OAuth flow when `{PAGE_ID}` isn't
supplied.

## Inputs

- `{PAGE_ID}` — **optional.** If absent, run OAuth → fetch pages → prompt for selection.
- `{CHANNEL_NAME}` — **optional.** If absent, prompt after page selection.

Most callers will NOT provide `PAGE_ID` upfront.

## Stage 1 preflight caveat

Only run the Stage 1 preflight if `{PAGE_ID}` was provided. If not, skip it — the page id isn't known
until OAuth + page selection completes. Run the preflight (two-query FK form) after the page is chosen,
before the insert.

## Stage 2-3: browser-based OAuth + page selection

Facebook requires OAuth authorization to access the customer's pages. This is an interactive,
browser-based flow — but it **is** headless-driveable end to end: the skill hands the admin the
exact authorize URL and fetches the page list over Connect REST. It is **not** UI-bootstrap-only.

**Step 1 — get `{AUTH_PROVIDER_ID}` AND the kickoff URL in one query.** The `OauthKickoffUrl` field
on the AuthProvider is the load-bearing piece — it is the feature-specific Facebook OAuth entry
point:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, OauthKickoffUrl FROM AuthProvider WHERE DeveloperName = 'LiveMessageSetup' AND ProviderType = 'Facebook' ORDER BY CreatedDate DESC LIMIT 1" \
  --json > "${SCRATCH_DIR}/fb-authprovider.json"
```
Record `{AUTH_PROVIDER_ID}` = `records[0].Id` and `{OAUTH_KICKOFF_URL}` = `records[0].OauthKickoffUrl`
(e.g. `https://<myDomain>/services/auth/oauth/LiveMessageSetup`). If no record →
`{ok:false, kind:"missing-authprovider", hint:"LiveMessageSetup AuthProvider not found — org may not have Facebook Messenger enabled"}`.

> **Use `OauthKickoffUrl`, NOT the generic `/services/auth/sso/<orgId>/LiveMessageSetup` SSO URL.**
> That SSO door runs the AuthProvider's Apex *registration handler* to log a user in; `LiveMessageSetup`
> has no registration handler (`RegistrationHandlerId=000000000000000`), so the SSO URL dead-ends at
> `NO_REGISTRATION_HANDLER` — "authentication error." The `/services/auth/oauth/...` kickoff URL is the
> service-token flow and is the only one that works here. (Verified live on sdb6, 2026-08-26.)

**Step 2 — best-effort token probe / page fetch (same endpoint).** A GET returns the page list when
the token is valid:
```bash
sf api request rest \
  "/services/data/v{API_VERSION}/connect/livemessage/channels?messageType=Facebook&authProviderId={AUTH_PROVIDER_ID}" \
  --target-org '{ORG_ALIAS}' > "${SCRATCH_DIR}/fb-pages.json"
```
- Body has a `channels[]` array → token *appears* valid; you already have the page list.
- Body has `errorCode:"AUTH_PROVIDER_NEEDS_AUTH"` → token missing/expired; go to Step 3.

> **The GET is NOT authoritative (gotcha #5).** It serves a *cached* page-list snapshot that can
> survive the underlying Facebook token expiring — a green GET does not guarantee the Stage 4 POST
> will succeed. Only the POST validates the token at submit time. If Stage 4 returns
> `AUTH_PROVIDER_NEEDS_AUTH` despite a passing GET, re-run Step 3 (don't blame the SF session).

**Step 3 — open the authorize URL in a browser.** Append the window-close callback so the flow ends
on a clean blank page rather than a confusing redirect:
```bash
OAUTH_URL="${OAUTH_KICKOFF_URL}?startURL=%2Fpage%2Fwindowclose.jsp"
case "$(uname -s)" in
  Darwin) open "${OAUTH_URL}" ;;
  Linux)  xdg-open "${OAUTH_URL}" ;;
  MINGW*|MSYS*|CYGWIN*) start "" "${OAUTH_URL}" ;;
  *) echo "Open this URL to authorize Facebook: ${OAUTH_URL}" ;;
esac
```
Open it automatically; only fall back to printing the URL if no opener exists. Tell the admin: log
in to the Facebook account that administers the target Page(s), grant access, and **a blank white
page means success** — close that tab. Then wait for their confirmation (or poll the Step-2 GET
until `channels[]` appears; ~60 × 3s).

**Step 4 — fetch the page list** (re-run the Step-2 GET now that the token is fresh). Each entry has
`developerName`, `masterLabel`, `messageType`, `messagingPlatformKey`; entries whose page is already
wired to a channel **also** carry `id` and `isActive`.

Failure kinds from this stage: `oauth-not-complete` (authorization missing/expired),
`oauth-failed` (authorization failed or cancelled), `missing-authprovider` (no LiveMessageSetup FB
AuthProvider on the org).

**Page selection (if `{PAGE_ID}` not supplied):** render **every** page — sorted alphabetically by
`masterLabel`, annotated with already-connected status, **never truncated** (real orgs have 56+
pages). Use the write-to-file-plus-render-inline strategy to defeat Bash stdout collapse. Read the
reply, trim, record `{PAGE_ID}`.

**Channel name (if not supplied):** prompt `Enter a display name for this channel (e.g., "Customer
Support")`. Empty after trim → re-prompt once; second empty →
`{ok:false, kind:"missing-input", hint:"CHANNEL_NAME is required"}`.

Failure kinds from this stage: `oauth-not-complete` (authorization missing/expired),
`oauth-failed` (authorization failed or cancelled).

## Stage 4.2: request body

```bash
jq -n --arg pageId "${PAGE_ID}" --arg channelName "${CHANNEL_NAME}" \
  '{messageType:"Facebook", platformType:"Enhanced",
    messagingPlatformKey:$pageId, messagingChannelName:$channelName, authDetails:{}}' \
  > "${SCRATCH_DIR}/body.json"
```

(`${SCRATCH_DIR}` is the per-run scratch dir established in SKILL.md Stage 0.2 — under
`${outputDir}`/`${TMPDIR}`, never a bare `/tmp` path.)

`authDetails: {}` — empty; the OAuth token lives in the AuthProvider, not the body. `authProviderId`
is a URL query parameter, never a body field.

**Response classification — classify by `errorCode` first, status second.** The Connect endpoint is
inconsistent about which HTTP status it pairs with `AUTH_PROVIDER_NEEDS_AUTH` (observed at 401, docs
imply 400). Always inspect `response[0].errorCode` (or `.errorCode` if the body is an object) before
status-based classification:

| `errorCode` (any status) | Handling |
| --- | --- |
| `AUTH_PROVIDER_NEEDS_AUTH` | `{ok:false, kind:"oauth-not-complete", hint:"Facebook OAuth authorization is missing or expired — re-run Stage 2 to refresh the FB token"}`. |
| `DUPLICATE_VALUE` | Re-run Stage 1 preflight; emit success `created:false, path:"connect-duplicate"`. |

Then the two 401 flavors (disambiguate by errorCode, NOT status):
- `AUTH_PROVIDER_NEEDS_AUTH` → `oauth-not-complete` (re-run OAuth; SF session is fine).
- empty body / `INVALID_SESSION_ID` → `{ok:false, kind:"auth", hint:"SF session token invalid — run 'sf org login web'"}`.

Telling the user to run `sf org login web` when the FB token is the problem sends them down a dead
end — the errorCode is what distinguishes the two.

## Gotchas

1. **The 401 is usually NOT an SF token problem.** `AUTH_PROVIDER_NEEDS_AUTH` at 401 means the
   AuthProvider's stored Facebook token is stale — re-run OAuth, not `sf org login web`. Classify by
   errorCode first.
2. **Never truncate the page list.** 56+ pages is normal; write-to-file-plus-render-inline defeats
   Bash stdout collapse.
3. **MCU lands as `DeploymentStatus=New` for Facebook** (WhatsApp lands as `Disabled`). Both are
   valid `→ Provisioning` sources — don't assert a specific starting status in Stage 5. (Verified:
   fresh FB insert → `MessagingChannelUsage.DeploymentStatus=New`, `DeploymentType=Conversation`.)
4. **POST-response projection is not authoritative** for `masterLabel` / `developerName` — trust the
   Stage 5 verify SOQL. Verified: POST returned `developerName:"Facebook_988507654355940"` /
   `masterLabel:"988507654355940"`, but SOQL showed `FACEBOOK_US_988507654355940` (uppercase +
   country-code suffix) / the real `messagingChannelName` as `MasterLabel`.
5. **The page-list GET is a cached snapshot, not a live token check.** `GET
   /connect/livemessage/channels?messageType=Facebook&authProviderId=...` can return 200 with the
   full page list even after the underlying Facebook token has expired; only the Stage 4 POST
   validates the token at submit time. Use the GET for the page list, never as proof the POST will
   succeed. If the POST returns `AUTH_PROVIDER_NEEDS_AUTH`, re-open `OauthKickoffUrl` (Stage 2-3),
   don't run `sf org login web`.
6. **Consent is auto-seeded on insert — do NOT assume the channel lands consent-blank.** A fresh
   Connect insert comes back with `ConsentType=ImplicitOptIn` already set and a default `en_US`
   `MsgChannelLanguageKeyword` already created (opt-out keywords `cancel,stopall,stop,unsubscribe,
   end,quit` + a canned confirmation, plus a `help` keyword). The downstream consent step is
   therefore often a **no-op** on a fresh channel (or an *upgrade* if the caller wants
   Explicit/DoubleOptIn), not a guaranteed write. (Verified live on sdb6, 2026-08-26, channel
   `0MjSG000000TXdJ0AW`.)
