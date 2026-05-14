---
name: configuring-connected-apps
description: "Salesforce Connected Apps and External Client Apps OAuth configuration with 120-point scoring. Use this skill to configure OAuth flows, JWT bearer auth, Connected Apps, and External Client Apps in Salesforce. TRIGGER when: user configures OAuth flows, JWT bearer auth, Connected Apps, ECAs, or touches .connectedApp-meta.xml / .eca-meta.xml files. DO NOT TRIGGER when: configuring Named Credentials for callouts (use building-sf-integrations), reviewing permission policies (use deploying-sf-metadata), or writing Apex token-handling code (use generating-apex)."
license: LICENSE.txt has complete terms
allowed-tools: Bash Read Write Edit Glob Grep WebFetch AskUserQuestion TodoWrite
metadata:
  version: "1.1"
---

# configuring-connected-apps: Salesforce Connected Apps & External Client Apps

Use this skill when the user needs **OAuth app configuration** in Salesforce: Connected Apps, External Client Apps (ECAs), JWT bearer setup, PKCE decisions, scope design, or migration from older Connected App patterns to newer ECA patterns.

## Scope

**In scope:**
- `.connectedApp-meta.xml` or `.eca-meta.xml` files
- OAuth flow selection and callback / scope setup
- JWT bearer auth, device flow, client credentials, or auth-code decisions
- Connected App vs External Client App architecture choices
- Consumer key / secret / certificate handling strategy

**Out of scope — delegate elsewhere:**
- Configuring Named Credentials or runtime callouts → [building-sf-integrations](../building-sf-integrations/SKILL.md)
- Deploying metadata to orgs → [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md)
- Writing Apex token-handling code → [generating-apex](../generating-apex/SKILL.md)

---

## First Decision: Connected App or External Client App

| If the need is... | Prefer |
|---|---|
| simple single-org OAuth app | Connected App |
| new development with better secret handling | External Client App |
| multi-org / packaging / stronger operational controls | External Client App |
| straightforward legacy compatibility | Connected App |

Default guidance:
- Choose **ECA** for new regulated, packageable, or automation-heavy solutions.
- Choose **Connected App** when simplicity and legacy compatibility matter more.
- Spring '26 note: creation of new Connected Apps is disabled by default in orgs. For new integrations, prefer External Client Apps unless Connected App compatibility is explicitly required.

---

## Required Inputs

Ask for or infer:
- App type: Connected App or ECA
- OAuth flow: auth code, PKCE, JWT bearer, device, client credentials
- Client type: confidential vs public
- Callback URLs / redirect surfaces
- Required scopes
- Distribution model: local org only vs packageable / multi-org
- Whether certificates or secret rotation are required

---

## Workflow

### 1. Choose the app model
Decide whether a Connected App or ECA is the better long-term fit using the decision table above.

### 2. Choose the OAuth flow

| Use case | Default flow |
|---|---|
| backend web app | Authorization Code |
| SPA / mobile / public client | Authorization Code + PKCE |
| server-to-server / CI/CD | JWT Bearer |
| device / CLI auth | Device Flow |
| service account style app | Client Credentials (typically ECA) |

### 3. Start from the right template
Read the appropriate template before generating — do not build from scratch:

| Template | Use case |
|---|---|
| `assets/connected-app-basic.xml` | Simple API integration, minimal OAuth |
| `assets/connected-app-oauth.xml` | Web app with full OAuth 2.0 configuration |
| `assets/connected-app-jwt.xml` | JWT bearer / server-to-server |
| `assets/connected-app-canvas.xml` | Embedding external apps in Salesforce UI (Canvas) |
| `assets/external-client-app.xml` | ECA header file — all new ECA builds start here |
| `assets/eca-global-oauth.xml` | ECA global OAuth settings (scopes, PKCE, rotation) |
| `assets/eca-oauth-settings.xml` | ECA per-app OAuth settings |
| `assets/eca-policies.xml` | ECA configurable policies |

If you need source-controlled ECA OAuth security metadata, retrieve it from an org first and treat the retrieved file as the schema source of truth:
```
sf project retrieve start --metadata ExtlClntAppOauthSecuritySettings:<AppName> --target-org <alias>
```

### 4. Apply security hardening
Read `references/security-checklist.md` for the full 120-point security checklist. Favor:
- Least-privilege scopes
- Explicit callback URLs
- PKCE for public clients
- Certificate-based auth where appropriate
- Rotation-ready secret / key handling
- IP restrictions when realistic and maintainable

### 5. Validate deployment readiness
Read `references/testing-validation-guide.md` before handoff. Confirm:
- Metadata file naming is correct (see Gotchas below)
- Scopes are justified
- Callback and auth model match the real client type
- Secrets are not embedded in source

### 6. Handle errors
If deployment fails, check the error output for:
- `DUPLICATE_VALUE` — a Connected App or ECA with this name already exists; rename or retrieve-then-update instead
- `INVALID_CROSS_REFERENCE_KEY` — the `externalClientApplication` name in an ECA settings file doesn't match the `.eca-meta.xml` filename exactly
- `INSUFFICIENT_ACCESS_OR_READONLY` — user lacks the "Manage Connected Apps" permission
- If any step fails, do not proceed to the next step — surface the error to the user with the specific message above

---

## Rules / Constraints

| Rule | Rationale |
|---|---|
| Never commit consumer secrets to source control | Credential exposure risk |
| Never use `Full` scope by default | Unnecessary privilege; request only what the app needs |
| Always use PKCE for public clients (mobile, SPA) | Prevents auth code interception |
| Never use wildcard or overly broad callback URLs | Token interception risk |
| ECA OAuth security settings must be retrieved from org before editing | File schema is not fully documented; retrieve-first ensures accuracy |
| Use `<alias>` placeholders in CLI commands, never hardcoded org URLs | Org URLs vary per environment |
| Detect actual `packageDirectory` from `sfdx-project.json` before writing files | Projects may not use the default `force-app/main/default/` layout |

---

## Metadata Notes That Matter

### Connected App
Default source location (verify via `sfdx-project.json → packageDirectories`):
- `<packageDir>/connectedApps/`

### External Client App
ECA metadata spans multiple top-level source directories. Default locations (verify via `sfdx-project.json`):

| Directory | Metadata type | File suffix |
|---|---|---|
| `<packageDir>/externalClientApps/` | `ExternalClientApplication` | `.eca-meta.xml` |
| `<packageDir>/extlClntAppGlobalOauthSets/` | `ExtlClntAppGlobalOauthSettings` | `.ecaGlblOauth-meta.xml` |
| `<packageDir>/extlClntAppOauthSettings/` | `ExtlClntAppOauthSettings` | `.ecaOauth-meta.xml` |
| `<packageDir>/extlClntAppOauthSecuritySettings/` | `ExtlClntAppOauthSecuritySettings` | `.ecaOauthSecurity-meta.xml` |
| `<packageDir>/extlClntAppOauthPolicies/` | `ExtlClntAppOauthConfigurablePolicies` | `.ecaOauthPlcy-meta.xml` |
| `<packageDir>/extlClntAppPolicies/` | `ExtlClntAppConfigurablePolicies` | `.ecaPlcy-meta.xml` |

---

## Gotchas

| Gotcha | Detail |
|---|---|
| `.ecaGlblOauth` not `.ecaGlobalOauth` | The global OAuth suffix is abbreviated — using the long form will break deployment |
| `.ecaPlcy` not `.ecaPolicy` | Same abbreviation pattern — the general policy suffix is short form |
| `.ecaOauthSecurity` for security settings | Use `.ecaOauthSecurity`, not `.ecaSecurity` |
| ECA OAuth security settings are retrieve-only | Cannot be created from scratch in source — always retrieve from org first |
| Spring '26: new Connected Apps disabled by default | New orgs block Connected App creation; use ECA unless explicitly required |
| Consumer key is generated post-deploy | You cannot set the consumer key in metadata — retrieve it after first deployment |

---

## Output Expectations

When finishing, confirm and report in this order:

1. **App type chosen** — Connected App or External Client App
2. **OAuth flow chosen**
3. **Files created or updated** — list each metadata file path
4. **Security decisions** — scopes, PKCE, certs, secrets, IP policy
5. **Next deployment / testing step**

Suggested output shape:
```
App: <name>
Type: Connected App | External Client App
Flow: <oauth flow>
Files: <paths>
Security: <scopes, PKCE, certs, secrets, IP policy>
Next step: <deploy, retrieve consumer key, or test auth flow>
Score: <x>/120
```

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| Named Credential / callout runtime config | [building-sf-integrations](../building-sf-integrations/SKILL.md) | runtime integration setup |
| Deploy app metadata | [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md) | org validation and deployment |
| Apex token or refresh handling | [generating-apex](../generating-apex/SKILL.md) | implementation logic |

---

## Score Guide

| Score | Meaning |
|---|---|
| 80+ | production-ready OAuth app config |
| 54–79 | workable but needs hardening review |
| < 54 | block deployment until fixed |

---

## Reference File Index

| File | When to read |
|---|---|
| `assets/connected-app-basic.xml` | Step 3 — template for simple Connected App with minimal OAuth |
| `assets/connected-app-oauth.xml` | Step 3 — template for full OAuth 2.0 Connected App |
| `assets/connected-app-jwt.xml` | Step 3 — template for JWT bearer / server-to-server Connected App |
| `assets/connected-app-canvas.xml` | Step 3 — template for Canvas app embedding in Salesforce UI |
| `assets/external-client-app.xml` | Step 3 — ECA header file template |
| `assets/eca-global-oauth.xml` | Step 3 — ECA global OAuth settings template (PKCE, rotation, callbacks) |
| `assets/eca-oauth-settings.xml` | Step 3 — ECA per-app OAuth settings template |
| `assets/eca-policies.xml` | Step 3 — ECA configurable policies template |
| `references/oauth-flows-reference.md` | Step 2 — detailed OAuth flow comparison and decision guide |
| `references/security-checklist.md` | Step 4 — full 120-point security scoring checklist |
| `references/testing-validation-guide.md` | Step 5 — pre-deployment validation and testing guide |
| `references/migration-guide.md` | When migrating from Connected App to ECA patterns |
| `references/example-usage.md` | Full end-to-end examples for common OAuth scenarios |