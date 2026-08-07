# Authentication — SFAP Access Token

The ApexGuru SFAP Scan API authenticates with an **SFAP access token (JWT)
carrying the `sfap_api` scope**. There is **no org id parameter** — the target
org, and the environment (prod/stage/dev) the request is routed to, are both
derived from the token's `tnk` claim, formatted `core/<instance>/<orgId>`.
Customers authenticate a production org (`tnk core/prod/<orgId>`), so their
requests always go to production.

## Where the JWT comes from (Tharun's interim guide)

The token is derived from an **authenticated `sf` CLI org**. `resolve-token.sh`
obtains the org's live session id and exchanges it for the SFAP JWT by calling
`<instanceUrl>/ide/auth`, which returns `{ "jwt": "...", "message": "..." }`.

This is Tharun's **interim** approach — the Code Analyzer team may provide a cleaner
path later. `resolve-token.sh` is the **single place** that changes when it does;
everything downstream consumes the token opaquely.

### How the session id is obtained (important)

`sf org display --json` **redacts** `accessToken` on recent CLI versions
(≈2.14x+) — it returns a `[REDACTED]…` placeholder, not a usable token. Sending
that to `/ide/auth` yields a bare `401 "No session ID sent"`. So the resolver does
**not** use `sf org display`'s access token. Instead it:

1. reads the (non-redacted) `instanceUrl` from `sf org display --json`,
2. gets a frontdoor URL from `sf org open --url-only --json`,
3. follows that URL with `curl` to mint the real `sid` session cookie, and
4. sends the `sid` as `Authorization: Bearer` to `<instanceUrl>/ide/auth`.

The `sid` is a secret: it lives only in a `0600` temp cookie jar that the script
deletes on exit, and is never echoed.

## How `resolve-token.sh` resolves the token

In priority order (first hit wins):

1. **`APEXGURU_SFAP_TOKEN`** environment variable — the raw JWT. Most portable;
   works headless and in CI. Use this in environments where `sf org open` can't
   run (no browser session), supplying a production `sfap_api` JWT directly.
2. **`APEXGURU_SFAP_TOKEN_FILE`** environment variable — a path to a file containing
   the JWT (whitespace trimmed). Keeps the token out of shell history.
3. **`sf` CLI → frontdoor `sid` → `<instanceUrl>/ide/auth`** — derives the JWT from
   an authenticated **production** org. Requires `sf`, `jq`, and `curl`. Org
   selection: `--org <alias>` flag, else the `APEXGURU_SF_ORG` env var, else the
   CLI's default/target org. The user just needs to be logged in
   (`sf org login web`).

If none succeed, the script returns:

```json
{"error":"no SFAP token found","hint":"Sign in to an authorized Salesforce org to run an ApexGuru scan and compare your code against production performance data."}
```

### Setting up the `sf` CLI path

```bash
# Log in once to a PRODUCTION org (My Domain or internal login host):
sf org login web --instance-url "https://<your-prod-host>" --alias <your-alias>

# Then the skill derives the JWT automatically. To target a specific org:
bash run-scan.sh <zip> <raw-out.json> --org <your-alias>
```

The `/ide/auth` response also carries a `message` field; only `jwt` is consumed.
Treat the derived JWT as a secret — the scripts never echo it (see the mandatory
script rules in SKILL.md). `resolve-token.sh` never prints the token to stdout:
it writes the JWT to a `0600` temp file and returns only the path in a
`tokenFile` field; `run-scan.sh` reads that file into memory and deletes it
immediately.

> **Note:** some orgs gate `/ide/auth` behind MFA enrollment — the exchange then
> returns an HTML redirect to a two-factor setup page instead of a JWT. If that
> happens, either complete MFA enrollment for that org or supply a production
> `sfap_api` JWT directly via `APEXGURU_SFAP_TOKEN`.

## Local pre-flight token check (no network)

Once a token is found, `resolve-token.sh` pipes it to `validate-token.js`, which
decodes the JWT's freely-readable header/body claims (it does **not** verify the
signature — only the server can) to catch the two things behind almost every
`401` **before** we zip and upload, and to detect the token's environment:

1. **Missing scope** — the `scp`/`scope` claim doesn't include `sfap_api`.
2. **Expired** — `exp` is in the past.

It also reads the environment from the `tnk` instance segment (and `iss` host) —
`core/prod/...` → prod, `core/stagecomstg2/...` → stage, `core/falcondeva/...` →
dev — and reports it as `detectedEnv` so `resolve-token.sh` routes to the
matching host. This is **not** a block: a stage/dev token routes to the stage/dev
endpoint instead of being rejected.

Only **provable** failures block (exit 1 with a clear `error`/`hint`). Anything the
script can't read — an opaque non-JWT token, or a missing claim — is a non-fatal
warning, so this never blocks a valid token it simply can't introspect. The token
is passed on **stdin**, never as a command-line argument, so it stays out of the
process list.

Example fail-fast message (instead of a bare HTTP 401 deep in the poll loop):

```json
{"ok":false,"error":"token scope does not include sfap_api","hint":"Re-mint the token with the sfap_api scope. See references/authentication.md."}
```

## Setup for the user

```bash
# Normal path: just log in to a production org with the sf CLI
# (the JWT is derived automatically).
sf org login web --instance-url "https://<your-prod-host>" --alias <your-alias>

# Override A: env var for the session (CI/headless, or to bypass sf CLI)
export APEXGURU_SFAP_TOKEN="eyJ...<production sfap_api JWT>..."

# Override B: token file (not echoed into history)
export APEXGURU_SFAP_TOKEN_FILE="$HOME/.apexguru/sfap-token"
```

## Endpoint routing

The base URL is chosen from the token's detected environment, so the request
always lands where the token was issued:

| Env   | Host                        | Base URL                                                        |
|-------|-----------------------------|-----------------------------------------------------------------|
| prod  | `api.salesforce.com`        | `https://api.salesforce.com/platform/scale/v1-beta.1/apex-guru`       |
| stage | `stage.api.salesforce.com`  | `https://stage.api.salesforce.com/platform/scale/v1-beta.1/apex-guru` |
| dev   | `dev.api.salesforce.com`    | `https://dev.api.salesforce.com/platform/scale/v1-beta.1/apex-guru`   |

There is no `--env` flag: routing is automatic from the `tnk` claim, and an
undetectable environment defaults to prod. Customers authenticate a production
org, so they always hit `api.salesforce.com`; the stage/dev hosts exist for
internal testing against non-prod orgs.
