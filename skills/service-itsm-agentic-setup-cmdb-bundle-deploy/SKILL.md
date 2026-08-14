---
name: service-itsm-agentic-setup-cmdb-bundle-deploy
description: "Deploy (install) the CMDB Foundation base content bundle in Service Cloud ITSM against a production or sandbox org, after the CMDB feature is enabled. Use when the user asks to install the CMDB bundle, deploy CMDB Foundation, set up the CMDB base content, install CMDB out-of-the-box content, or finish CMDB setup with the base bundle. Triggers on: install CMDB bundle, deploy CMDB Foundation, CMDB base content, CMDB content bundle, bundleInstallation, finish CMDB setup. DO NOT TRIGGER when: the user wants to enable the CMDB feature for the org (that is the CMDB feature-enable skill), assign CMDB permission sets to a user (that is the CMDB access-assign skill), install optional non-base add-on bundles, deploy general (non-CMDB) metadata or packages, or work with CMDB records directly."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-agentic-setup-cmdb-access-assign"
    - "service-itsm-agentic-setup-cmdb-configure"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  accessCheck:
    - type: "orgPerm"
      value: "ITSrvcsCnfgMgmnt"
    - type: "orgPref"
      value: "CMDBEnabled"
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Deploy the CMDB Foundation Bundle (Service Cloud ITSM)

Installs the **CMDB Foundation (base)** content bundle — the out-of-the-box configuration-item types,
schema, and content that make CMDB usable. This is **Layer 4**, the final layer of the CMDB setup
stack, and it requires the CMDB feature to already be enabled (Layer 2). Every call runs through the
**Salesforce-hosted Headless-360 MCP server** (server key `headless-360`) via its four meta-tools
(`discover`, `describe`, `dispatch_readonly`, `dispatch`). The org is derived from the OAuth JWT bound
to the current MCP session — the skill never handles an org id, alias, or credentials — so this works
identically against **production** and sandbox with no per-user MCP install.

## Scope

- **In scope**: confirming CMDB is enabled, reading the live bundle catalog, resolving the exact
  version of the base bundle, installing the **base** (`CMDB Foundation`) bundle, and verifying.
- **Out of scope**: enabling the CMDB feature / provisioning the ITOM tenant (Layers 0–2 —
  `service-itsm-agentic-setup-cmdb-configure`), assigning permission sets (Layer 3 —
  `service-itsm-agentic-setup-cmdb-access-assign`), installing **optional add-on** bundles (e.g.
  Component Identification Rules), CMDB record CRUD, or Discovery.

This skill installs the **base bundle only**. Optional add-ons are intentionally out of scope.

## Why order matters

The bundle Connect APIs (`bundleListView`, `bundles/details`, `bundleInstallation`) are gated by
`orgHasCMDBEnabled`. Until the CMDB feature is enabled they return `403 FUNCTIONALITY_NOT_ENABLED`, so
this skill **must** run after the CMDB feature-enable skill has turned the feature on.

On top of the org gate, these reads also enforce the **running user's own CMDB access**, so a
`403 FUNCTIONALITY_NOT_ENABLED` here has two distinct causes — feature-off **or** user-has-no-access.
Step 1 disambiguates them via the feature status before sending the user anywhere; never assume a 403
means the feature is off.

## Mechanism

All operations dispatch through **headless-360** MCP tools. Reads go through
`mcp__headless-360__dispatch_readonly`, writes through `mcp__headless-360__dispatch` — both take raw
HTTP: `{"url": "<path>", "method": "GET|POST", "body"?: {...}, "queryParams"?: {...}}` — **not**
`{operation_id, arguments}`. See `references/mcp-invocation.md` for the exact `url` / `method` / `body`
of every call. The four tools:

- `mcp__headless-360__discover` — semantic search over the indexed operation catalog (discovery /
  confirmation only).
- `mcp__headless-360__describe` — pull the full input schema and canonical route before the install POST.
- `mcp__headless-360__dispatch_readonly` — the dispatcher for every read (GET).
- `mcp__headless-360__dispatch` — the dispatcher for every write (POST/PATCH).

The skill never handles credentials — the org is bound to the current OAuth session. If a `dispatch*`
call returns an auth error, tell the user to re-authenticate the headless-360 MCP connection (and
confirm the session points at the intended org), then stop.

---

## Clarifying questions

Ask only what you cannot infer from conversation:

- **Which org?** Confirm the target org and state plainly that **content will be installed into this
  org** (a write). For production, get explicit confirmation.

Do not re-ask for anything the user already provided; pre-populate and note "(from conversation)".

---

## Workflow

Sequential. **Always read before you write** — read the catalog and resolve the exact version before
installing. Never guess a version string.

### Step 1 — Confirm CMDB is enabled (read, gate)

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/cmdb/bundleListView", "method": "GET" })
```

- `200` → CMDB is enabled; the response lists available bundles and their install status. Proceed.
- `403 FUNCTIONALITY_NOT_ENABLED` → **ambiguous — disambiguate before telling the user CMDB is off.**
  This read enforces **both** the org gate **and** the running user's own CMDB access, so a 403 has
  two possible causes. Check the feature status to tell them apart:
  ```text
  dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/status", "method": "GET" })
  ```
  - `status != ENABLED` → the **CMDB feature isn't enabled**. STOP and route the user to the CMDB
    feature-enable skill (`service-itsm-agentic-setup-cmdb-configure`) first.
  - `status == ENABLED` → the feature **is** enabled; the running user simply **lacks CMDB permission
    sets**. STOP and route the user to the CMDB access-assign skill
    (`service-itsm-agentic-setup-cmdb-access-assign`) to grant themselves CMDB access — at minimum the
    read set, plus **Type Manager** for bundle management — then retry. Do NOT send them to the
    feature-enable skill; CMDB is already enabled.

From the `bundleListView` response, identify the base bundle (CMDB Foundation) and note its
`currentInstalledVersion`. If it is already installed at the latest version, tell the user there is
nothing to do.

### Step 2 — Resolve the exact base version (read)

Do NOT guess or hard-code the version. Read the authoritative version from bundle details:

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/cmdb/bundles/details", "method": "GET", "queryParams": { "bundleIdentifier": "base" } })
```

Read `latestVersion` from the catalog and use that string **verbatim** for the install — do NOT strip,
add, or reformat any characters (including a leading `v`). The install endpoint matches the version by
exact string equality against the registry, and the registry stores versions exactly as the catalog
reports them (e.g. `"v3.0"`), so the value must be passed through unchanged.

**You may only install the latest version.** The install endpoint rejects any non-latest version
(`"Target version <x> is not the latest available version"`) — it does not support installing or
rolling back to an older version, so always resolve `latestVersion` and install exactly that. If
`installedVersion` already equals `latestVersion`, stop — the base bundle is up to date.

> **If `bundles/details` returns `403 FUNCTIONALITY_NOT_ENABLED`** while `bundleListView` (Step 1)
> returned `200`: the org gate is fine, but the running user lacks the bundle-management permission.
> `bundles/details` requires the **Type Manager** role — the Reader / Owner / Type Reader sets are not
> sufficient. Route the user to the CMDB access-assign skill to grant Type Manager, then retry. As a
> fallback, `bundleListView` already returns the base bundle's `currentInstalledVersion` and
> `latestVersion`, so you can resolve the version from Step 1's response if Type Manager cannot be
> assigned.

### Step 3 — Confirm with the user (before the write)

Show the base bundle name, the version to be installed, and the target org. Get explicit confirmation
before the write. State plainly that this installs out-of-the-box CMDB content into the org.

### Step 4 — Install the base bundle (write)

Call `discover(query="cmdb bundle installation")` then `describe(id=<bundleInstallation operation id>)`
to confirm the input schema, then install:

```text
dispatch({ "url": "/services/data/v67.0/connect/cmdb/bundleInstallation", "method": "POST", "body": { "bundleIdentifier": "base", "version": "<latestVersion from Step 2, verbatim>" } })
```

Both `bundleIdentifier` and `version` are required, and `version` must be the catalog's `latestVersion`
string passed through unchanged. A `success: true` response means the installation was **initiated** —
it may complete asynchronously.

### Step 5 — Verify (read — do NOT trust the install response alone)

Re-read bundle details and confirm the base bundle now reports the installed version:

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/cmdb/bundles/details", "method": "GET", "queryParams": { "bundleIdentifier": "base" } })
```

`installedVersion` should equal the version you installed. If installation is async and it has not
updated yet, tell the user it is in progress and how to re-check.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Read `bundleListView` first as the enablement gate | A 403 here means either CMDB isn't enabled or the user lacks CMDB access — disambiguate via feature status before acting |
| Resolve the version from `bundles/details`; never guess; pass `latestVersion` verbatim | The install endpoint matches the version by exact string equality against the registry, which stores it exactly as the catalog reports (e.g. `"v3.0"`) — do not strip or reformat any characters |
| Install only the latest version | The endpoint rejects any non-latest version (`"Target version <x> is not the latest available version"`); it cannot install or roll back to an older version |
| Install `base` only | This skill is scoped to the CMDB Foundation base bundle; optional add-ons are out of scope |
| Confirm the target org and the install with the user | Installing content is a real, hard-to-reverse write on a live org |
| Skip if already installed at latest | Avoid redundant installs; report "already up to date" |
| Treat `success: true` as "initiated"; verify separately | Installation can be asynchronous |
| Never expose internal jargon to the user | Keep record IDs, HTTP status codes (403/400/500), API error codes (`FUNCTIONALITY_NOT_ENABLED`, …), endpoint names (`bundleListView`, `bundles/details`, `bundleInstallation`), developer names, and tooling internals (`dispatch`, `headless-360`) out of user-facing output. Use bundle names and versions and plain language |

---

## Verification checklist

- [ ] `bundleListView` returned `200` (CMDB is enabled and the user has access)?
- [ ] Resolved `latestVersion` for `base` from `bundles/details` (not guessed)?
- [ ] Skipped if already at the latest version?
- [ ] Confirmed the target org + install with the user before writing?
- [ ] `bundleInstallation` returned `success: true`?
- [ ] Verified `installedVersion` matches (or reported async in-progress)?

---

## Output expectations

```text
CMDB Bundle Deploy — Complete (via service-itsm-agentic-setup-cmdb-bundle-deploy)

Target org: <org>

  Bundle:   CMDB Foundation (base)
  Version:  <version>
  Status:   Installation initiated — success

CMDB now has its base content installed. Combined with the enabled feature and assigned user
access, CMDB is ready end-to-end.
```

Keep internal jargon out of user-facing output (no record IDs, HTTP status codes, error codes, or
endpoint names). If any step fails, stop and tell the user — in plain language — what didn't succeed
and what it means for them (e.g. "CMDB isn't turned on for this org yet, so the content can't be
installed" rather than echoing a 403 code), then point to the fix.

---

## Common failures (surface these in plain language)

| Symptom | Likely cause | What to tell the user |
|---------|--------------|-----------------------|
| `403` on the catalog read **and** feature not enabled | CMDB feature not enabled for the org | CMDB must be turned on for the org first; that's a separate setup step — point to the feature-enable skill |
| `403` on the catalog read **but** feature is enabled | Feature is on; the running user lacks CMDB access (this read enforces user-level access too) | Grant the user CMDB access first (a separate setup step), then try again — the feature itself is already on |
| `403` on the version read **but** the catalog read succeeded | The user lacks the CMDB bundle-management role (Type Manager) | Grant the user the CMDB Type Manager role (a separate access step), then retry; the org itself is set up correctly |
| Install rejected — bundle/version doesn't exist | Wrong version string | Re-read the catalog and use the exact latest version it reports |
| Install reported success but the version hasn't changed | Installation is running in the background | It's in progress; check again shortly to confirm it finished |
| Downstream error on install | Temporary platform dependency issue | Try again; if it keeps failing, this needs Salesforce support |
| Connection/authentication error | The org connection isn't set up or has expired | Re-authenticate the org connection and confirm it points at the intended org, then retry |

---

## Cross-skill integration

| When | Skill |
|------|-------|
| The org CMDB feature is not enabled yet (org gate still closed) | `service-itsm-agentic-setup-cmdb-configure` (Layers 0–2 — enable the feature first, then return here) |
| The running user lacks CMDB access, or lacks **Type Manager** for bundle management | `service-itsm-agentic-setup-cmdb-access-assign` (Layer 3 — grant the user CMDB access, including Type Manager, then return here) |

---

## Reference file index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Exact `mcp__headless-360__*` call shapes for the bundle catalog + install calls, response envelopes, the install schema lookup, and the error table |
