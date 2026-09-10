---
name: manage-api-version
description: Read, check for updates, and change the version of one or more API dependencies in a Mule project — the same values the Anypoint Studio Project Properties → API Specs tab sets, stored as <{artifactId}.version> properties in pom.xml. Use when the user asks to "get API version", "show API version", "display version info", "check what version an API is on", "any new versions", "any updates available", "check for updates", "update API version", "change API version", "bump API version", "set API version", or any request to read, check, or modify an API dependency version in a Mule project.
metadata:
  author: mule-dx-tooling
  version: "1.4.0"
license: Apache-2.0
compatibility: Requires Anypoint CLI v4 (`anypoint-cli-v4 exchange asset list` command)
allowed-tools: Bash Read Write Edit AskUserQuestion
---

# manage-api-version

Read and change the version of one or more API dependencies in a Mule project — the same values the Anypoint Studio **Project Properties → API Specs tab** sets. Each API dependency in the project gets its own version property in `pom.xml`, named by combining the dependency's `artifactId` with `.version`:

```xml
<properties>
  <order-api.version>1.0.0</order-api.version>
  <customer-api.version>2.1.0</customer-api.version>
</properties>
```

---

## Overview

This skill reads and updates `<{artifactId}.version>` properties in `pom.xml`. A Mule project can have one or more API dependencies, each with its own version property. The property name is always `{artifactId}.version` where `artifactId` is the Maven artifact ID of the API dependency.

**What you'll do:** Display all API versions or specific ones by name, check whether newer versions are available (for all APIs or specific ones), or update the version for one or more API dependencies in a single operation and rescaffold the project once all changes are applied.

---

## Prerequisites

Before starting, verify these tools are available:

```bash
anypoint-cli-v4 --version   # must be v4; needs exchange asset list
mvn --version               # Maven 3.6+ for rescaffold (CHANGE path only)
```

If `anypoint-cli-v4` is missing:
```bash
npm install -g @mulesoft/anypoint-cli-v4
anypoint-cli-v4 conf username <username>
anypoint-cli-v4 conf password <password>
```

The CHECK and CHANGE paths query Exchange. If the CLI is not authenticated or network is unavailable, display-only operations (DISPLAY ALL, DISPLAY SPECIFIC) still work — they read from `pom.xml` only.

---

## Bundled Scripts

This skill ships one shell helper in its own `scripts/` directory:

| Script | Purpose |
|---|---|
| `scripts/fetch_versions.sh <groupId>:<artifactId>:<currentVersion> [...]` | Resolves the full published-version list for one or more API dependencies in a single invocation, firing one Exchange lookup per API **in parallel** instead of the agent looping and calling `anypoint-cli-v4` once per API sequentially. See **Version Discovery** under Step 7b for full usage and output shape. |

Invoke it with the `Bash` tool at the **absolute path** you were given in the "skill is now active" message (the directory containing this `SKILL.md`) — e.g. `<skill-dir>/scripts/fetch_versions.sh ...`. Do **not** construct a relative `../scripts/...` path; the working directory shifts across turns and relative paths break.

---

## Execution Paths

| User intent | Path |
|---|---|
| display/check current version — all APIs or no specific one named | → **DISPLAY ALL** (Steps 1 → 2 → 3) |
| display/check current version — one or more specific APIs named | → **DISPLAY SPECIFIC** (Steps 1 → 2 → 4) |
| any new/updated versions available — no specific API named | → **CHECK ALL** (Steps 1 → 2 → 5) |
| any new/updated versions available — one or more specific APIs named | → **CHECK SPECIFIC** (Steps 1 → 2 → 6) |
| set, change, adjust, update, bump, switch version | → **CHANGE** (Steps 1 → 2 → 7 → 8 → 9) |

---

## Step 1: Resolve Project Directory

Resolve the project root using the best available signal, in this order:

1. **Exact path supplied** — use it directly.
2. **Rough location or folder name given** (e.g. "the order-api project", "in my documents", "the one in ~/projects") — use `find` to locate a `pom.xml` matching that hint and confirm with the user if more than one match is found.
3. **Multiple projects open/in scope and an API name was given, but no project hint** (e.g. a multi-root workspace, or more than one `pom.xml` reachable from context) — before falling back to "current/active project," check whether the named API's `<{artifactId}.version>` property (or a matching hardcoded `<dependency>` artifactId) exists in only one of the open projects' `pom.xml` files:
   - **Unique match** — use that project silently. Do not ask; a name that only exists in one place is not actually ambiguous.
   - **Matches multiple projects** — ask which project, the same way as case 5 below.
   - **Matches none of the open projects** — do not ask "which project" (that implies the project is the problem, when it's more likely the API name). Instead say:
     > I couldn't find an API named `<name>` in any of the open projects (`<list the open project names/paths>`). Did you mean a different API name, or is it in a project that isn't open right now?
   This check only applies when 2+ projects are genuinely in scope. With a single open/reachable project, skip straight to case 4 — never ask when there's nothing to disambiguate.
4. **Current working directory implied** (e.g. "this project", "the current one"), or only one project is in scope — check if `pom.xml` exists in the current directory and use it.
5. **Nothing given — no project hint AND no API name to disambiguate by — with multiple projects in scope** — this includes fully generic requests like "update the API version" or "check for updates" when 2+ projects are open and no prior project has been established this conversation. Do not guess a "current directory" in this case, even if one happens to be technically active (e.g. whichever file tab last had focus) — a generic request with no name or path given is exactly the ambiguous case this step exists to catch. Ask:

> What project do you want to work on? You can give me the full path, a folder name, or just tell me it's the current directory.

Confirm `pom.xml` exists at the resolved path before continuing.

**Ask at most once per conversation.** Once the user has stated or confirmed which project they mean, keep using it for subsequent requests in the same conversation — don't re-ask on every turn. If the user later names a different project or a different API that resolves elsewhere, switch silently and confirm the switch in the response (e.g. "Switching to `<project>` for this one.") rather than re-running the full disambiguation question.

**STOP** (only if the project cannot be resolved from context).

---

## Step 2: Route Operation

Parse the user's request for intent keywords:

| Keywords | Operation |
|---|---|
| get, show, find, display, what is, current — **all** / **every** / no specific API named | → **DISPLAY ALL** |
| get, show, find, display, what is, current — **one or more specific APIs named** | → **DISPLAY SPECIFIC** |
| any new, updates, newer, latest, upgrade — **no specific API named** | → **CHECK ALL** |
| any new, updates, newer, latest, upgrade — **one or more specific APIs named** | → **CHECK SPECIFIC** |
| set, change, adjust, update, bump, switch | → **CHANGE** |

If intent is ambiguous, ask:

> Do you want to **display** the current API version(s), or **change** one?

**STOP** (only if operation cannot be determined from the request).

---

## Step 3: Show All API Versions (Display All)

1. Read `pom.xml`. Find all properties inside `<properties>` whose name ends in `.version` and corresponds to an API spec dependency. To identify API spec dependencies, check the matching `<dependency>` block:
   - **Classifier check (preferred):** API spec deps use one of these classifiers: `raml`, `oas`, `graphql`, `protobuf`, `fat-protobuf`, `evented-api`. Connectors use `mule-plugin`. If a classifier is present and matches this list, it is an API spec.
   - **artifactId fallback:** If no classifier is set, check whether the `artifactId` contains the word `api` — this is the common naming convention for API spec artifacts.
   Skip any dependency whose classifier is `mule-plugin` or that matches neither signal.
2. Print all matching ones:

```
API dependency versions (from pom.xml <properties>):

  order-api.version    → 1.0.0
  customer-api.version → 2.1.0
```

3. If none are found, say so clearly and suggest the user check the Project Properties → API Specs tab in Anypoint Studio to confirm APIs are added to the project.

End the skill here for the DISPLAY ALL path.

---

## Step 4: Show Versions for Named APIs (Display Specific)

1. Extract all API names the user specified. If none were named, fall back to DISPLAY ALL.
2. Read `pom.xml`. For each named API, find its `<{artifactId}.version>` property.
3. Print each result:

```
order-api.version    → 1.0.0
customer-api.version → 2.1.0
```

4. If a named API's property is not found, flag it and list the available API version properties so the user can confirm the correct name.

End the skill here for the DISPLAY SPECIFIC path.

---

## Step 5: Check All APIs for Newer Versions (Check All)

1. Read `pom.xml` and identify all API spec dependencies (same classifier/artifactId logic as DISPLAY ALL).
2. For each API, discover its full version list using the **Version Discovery** procedure below.
3. Report results:

   **If newer versions exist for any API:**
   ```
   Newer versions available:

     order-api:    current 1.0.0 → latest 2.0.0
     customer-api: current 1.5.0 → latest 1.6.0

   No updates available:
     billing-api: 3.1.0 (already latest)

   Would you like to update any of these?
   ```
   **STOP** — if the user wants to update, transition to the CHANGE path starting at Step 7 for the APIs they name.

   **If no newer versions exist for any API:**
   ```
   All APIs are on their latest versions:

     order-api:    1.0.0
     customer-api: 2.1.0
     billing-api:  3.1.0

   Would you like to change any version anyway?
   ```
   **STOP** — if yes, transition to CHANGE path at Step 7.

End the skill here if the user does not want to make any changes.

---

## Step 6: Check Named APIs for Newer Versions (Check Specific)

1. Extract the API name(s) the user specified.
2. For each named API, discover its full version list using the **Version Discovery** procedure below, and compare against the current version to determine if a newer one exists.
3. Go through each named API one at a time in the order the user asked:

   **If a newer version exists:**
   ```
   order-api — current: 1.0.0
   A newer version is available: 2.0.0

   Would you like to update it?
   ```
   **STOP** — if yes, proceed with the CHANGE flow for this API (Step 7c onwards). If no, move to the next named API.

   **If already on the latest version:**
   ```
   order-api is already on the latest version: 1.0.0

   Would you like to change it to a different version anyway?
   ```
   **STOP** — if yes, proceed with the CHANGE flow for this API (Step 7c onwards). If no, move to the next named API.

4. After all named APIs have been addressed, if any were queued for change, proceed to Step 8.

---

## Step 7: Identify Target APIs and Fetch Available Versions (Change)

### 7a — Identify which APIs to change

If the user named the API(s) to update, use those. Otherwise:

1. Read `pom.xml` and list all API dependency version properties.
2. Ask which API(s) they want to update.

**STOP** (only if target API(s) not pre-supplied).

### 7b — Fetch available versions from Exchange

Before querying, back up the current pom.xml content in memory so it can be restored if anything fails later.

Read `groupId` and `artifactId` from the `<dependency>` block in `pom.xml` for every target API, then discover all of their version lists in a single call using the **Version Discovery** procedure below — pass all target APIs as separate arguments to the same script invocation, never one invocation per API.

If any row comes back with `"source": "error"` (both `list` and the `describe` fallback failed for that API):
- If no pom.xml changes have been made yet, stop and tell the user, citing the row's `error` field:
  > Failed to fetch versions from Exchange for `<artifactId>`. Check that `anypoint-cli-v4` is authenticated and you have network access, then try again.
- If pom.xml was already partially modified in a prior step, restore it to the backed-up state before stopping with the same message.

---

### Version Discovery (shared procedure — used by Steps 5, 6, 7b)

**Discover versions for ALL target APIs in ONE call to the bundled script — never loop and invoke `anypoint-cli-v4` yourself, one API at a time.** Each direct `anypoint-cli-v4` invocation pays a full Node CLI cold start plus a network round trip; looping that per API serializes N round trips where one script call does them **in parallel** and returns once. This is the single biggest lever for making this skill feel fast, especially on projects with several API dependencies.

Invoke the script with the `Bash` tool at its **absolute path** — `<skill-dir>/scripts/fetch_versions.sh`, where `<skill-dir>` is the absolute path you were given in the "skill is now active" message (the directory containing this `SKILL.md`). Do not construct a relative `../scripts/...` path; the working directory shifts across turns and relative paths break.

Pass one `<groupId>:<artifactId>:<currentVersion>` argument per target API — for Steps 5 and 6 that's every API identified in that step; for Step 7b that's every API in the change set:

```bash
<skill-dir>/scripts/fetch_versions.sh \
  "<groupId1>:<artifactId1>:<currentVersion1>" \
  "<groupId2>:<artifactId2>:<currentVersion2>"
```

The script prints one JSON array to stdout, one object per input API, **in input order**:

```json
[
  {
    "groupId": "org.example", "artifactId": "order-api", "currentVersion": "1.0.0",
    "versions": ["2.0.0", "1.1.0", "1.0.0"],
    "source": "list"
  }
]
```

Read each row's `source` field:
- **`"list"`** — the normal path. Internally this ran `exchange asset list <artifactId> --output json`, filtered to rows matching the exact `groupId`/`assetId`, sorted by semver (highest first). Trust this fully — it is not anchored to any single version, so it doesn't have the false-negative failure mode described below.
- **`"describe-fallback"`** — `list` returned zero matching rows for this asset, so the script fell back to `exchange asset describe <groupId>/<artifactId>/<currentVersion>` and parsed its `otherVersions` field. Surface the row's `warning` field to the user verbatim — `describe`'s version list is anchored to the version you query with and has been observed to come back **empty when that anchor version is not the latest published one**, even when newer versions genuinely exist. Since CHECK/CHANGE always query from whatever version is currently pinned in `pom.xml` (almost never the latest), treat this row's version list as possibly incomplete.
- **`"error"`** — both `list` and the `describe` fallback failed for this asset. Surface the row's `error` field. For Step 7b (CHANGE), treat this the same as an Exchange-fetch failure (see below). For Steps 5/6 (CHECK), report the failure for that specific API and continue processing the others — don't abort the whole check over one API's lookup failure.

(This mirrors the pattern already used by two sibling skills in this repo — `build-mule-integration/scripts/search_templates.sh` and `manage-global-configurations/scripts/get_latest_connector.sh` — which fire multiple `exchange asset list` calls in parallel rather than looping sequentially, for the same latency reason.)

### 7c — Present available versions and handle selection

For each target API, present the available versions **as a single `AskUserQuestion` tool call** — do not narrate the version list as plain chat text first and then also call the tool; that produces two renderings of the same question. The tool call itself is the only presentation. If a newer version than the current one exists, mention it in the question text; list every available version as an option (current version included, labeled), plus a "Keep current version" style option is not needed since the current version already appears in the list:

```
question: "order-api — current: 1.0.0. A newer version is available: 2.0.0. Which version would you like to use?"
options:
  - "2.0.0"
  - "1.1.0"
  - "1.0.0 (current, no change)"
  - "0.9.0"
```

If the current version is already the latest, drop the "newer version available" sentence from the question text but still call the tool the same way:

```
question: "order-api — current: 2.0.0. Which version would you like to use?"
options:
  - "2.0.0 (current, no change)"
  - "1.1.0"
  - "1.0.0"
```

When changing multiple APIs, handle them one at a time: issue one `AskUserQuestion` call for the first API, STOP, get the selection, then move to the next API and repeat with a new `AskUserQuestion` call.

**STOP** — wait for the tool's response for the current API before presenting the next. Never restate the question or option list as a separate chat message before or after the tool call.

### 7d — Handle same-version selection

If the user selects the version already applied for a given API, respond:

> `order-api` is already on version `1.0.0` — no changes made.

Remove that API from the change set. If all APIs in the request were no-ops, end the skill here. Otherwise continue with the remaining APIs that do have a version change.

---

## Step 8: Apply the New Version (Change)

### 8a — Update `pom.xml`

For each API in the change set, determine which case applies:

**Case 1 — Property placeholder already exists** (`<{artifactId}.version>` is in `<properties>`):
Update the value in the `<properties>` block. The dependency itself (`<version>${order-api.version}</version>`) does not need to change.

```bash
ARTIFACT_ID="order-api"
NEW_VERSION="1.1.0"

awk -v key="${ARTIFACT_ID}.version" -v val="$NEW_VERSION" '
  $0 ~ "<" key ">" { sub(/>.*</, ">" val "<") }
  { print }
' pom.xml > pom.xml.tmp && mv pom.xml.tmp pom.xml
```

**Case 2 — Version is hardcoded directly in the dependency** (no `<{artifactId}.version>` property exists, dependency has a literal `<version>1.0.0</version>`):
This means the project is not yet using the placeholder pattern. Do both:
1. Add `<{artifactId}.version>NEW</{artifactId}.version>` to the `<properties>` block.
2. Replace the hardcoded `<version>1.0.0</version>` inside that dependency's block with `<version>${order-api.version}</version>`.

Repeat for each API in the change set, applying all edits before writing the file.

### 8b — Confirm

Print a summary of all changes made:

```
Updated in pom.xml:
  order-api.version:    1.0.0 → 1.1.0
  customer-api.version: 1.5.0 → 2.0.0
```

---

## Step 9: Rescaffold the Project (Change)

After all version properties are updated, trigger APIkit to regenerate flows from the new API spec versions — the same operation Anypoint Studio runs when you save changes in the Project Properties → API Specs tab. If multiple APIs were changed in the same operation, flows for all of them are regenerated in this single pass.

Run the following from the project root, exactly as shown — two commands only, joined with `&&`, nothing else appended:

```bash
cd <projectDir> && mvn clean package -DskipTests
```

- **Never append `2>&1`, `>`, `>>`, or any other redirection to this command, and never pipe it into anything.** The tool invocation already captures stdout and stderr in full, so redirection adds nothing — and it has a real side effect: the host IDE's command layer treats stream-redirection operators as unsafe and forces a manual approval prompt even for an otherwise-trusted command, which is exactly what this step must avoid.
- Do not add flags or bundle it with anything else — only the exact `cd <projectDir> && mvn clean package -DskipTests` shape above.
- **Do not pause for user confirmation before running this.** Rescaffolding after a version change is automatic in the real product — Anypoint Studio runs it the instant `pom.xml` changes, or the instant the user touches the Project Properties → API Specs tab — with no click-through step for the human. This skill mirrors that: run the command as soon as Step 8's edits are written, without asking.
- Wait for the full output before continuing.
- `BUILD SUCCESS` means APIkit has pulled in the updated spec versions and regenerated the corresponding flows. The project is now consistent with all changed API versions.
- If `BUILD FAILURE` occurs: automatically restore `pom.xml` to its pre-change state, then report the Maven error output verbatim so the user can investigate:
  > Build failed — pom.xml has been restored to its previous state. Maven error: [output here]

**One `mvn` invocation per response.** Do not bundle it with any other tool call.

---

## Rules

- **Property name is always `{artifactId}.version`** — derived from the Maven `artifactId` of the API dependency, not a hardcoded tag like `<apiVersion>`.
- **Never touch `<version>`** (the Maven artifact version at the top of `pom.xml`). That is a different field entirely.
- **Always show available versions before applying a change.** Never ask the user to type a version string — always fetch from Exchange and present the list first.
- **Newer version callout only when one exists.** Only show the "a newer version is available" message if the current version is not already the latest. Never show it otherwise.
- **Same version is a no-op, not an error.** If the user picks the already-applied version, say so and exclude that API from the change set. If all selections are no-ops, end without writing any files or running `mvn`.
- **Batch all changes, then rescaffold once.** Apply all pom.xml edits before running `mvn`. Never rescaffold between individual API updates — one `mvn` pass at the end covers all of them.
- **Always back up pom.xml before writing.** Hold the original content in memory at the start of every CHANGE operation. Restore it automatically on any failure — Exchange fetch error, mvn failure, or anything else that prevents successful completion.
- **Rescaffold is mandatory after every CHANGE, and it is automatic — never a user prompt.** Never declare the version updated without running `mvn clean package -DskipTests` and confirming `BUILD SUCCESS`. A version change without rescaffolding leaves the project inconsistent. Run it immediately after Step 8's edits with no confirmation question, matching how Anypoint Studio itself rescaffolds automatically on a pom.xml change or an API Specs tab edit.
- **Never redirect the `mvn` command's output.** No `2>&1`, `>`, `>>`, or pipes — the tool call already captures full stdout/stderr, and redirection operators can trip the host IDE's unsafe-command check and force an unwanted manual approval.
- **One `mvn` invocation per response.** Do not bundle it with file edits or other commands.
- **No Anypoint CLI needed** for pom.xml edits — use bash + Read/Edit tools only.
- **`jq` is required** by `scripts/fetch_versions.sh` for parsing Exchange JSON responses. If `jq` is not available on the machine running the script, it will fail — there is no separate manual fallback path; install `jq` rather than reimplementing the script's parsing inline.
- **Version discovery is always one call to `scripts/fetch_versions.sh` covering every target API, never a per-API loop of raw `anypoint-cli-v4` invocations.** See the **Version Discovery** procedure under Step 7b. The script runs `exchange asset list` (not version-anchored) in parallel across all target APIs, falling back to `exchange asset describe`'s `otherVersions` field only per-API when `list` finds no match for that asset — `describe`'s version list is anchored to the version you query with and has been observed to return empty/incomplete results when that version isn't the latest, which is exactly the situation CHECK and CHANGE query from.
- **Multi-API version selection is one at a time.** Show one API's version list, STOP, get the selection, then proceed to the next. Never show all lists simultaneously.
- **Multi-turn interactive.** At every **STOP** marker: print only the question as plain text, end your response, and wait. Do not run any tools until all required values are in hand.
- **Skip-if-provided.** Before the first STOP, extract any values the user already gave (project path, operation, target API, new version). At each STOP, skip it if the question is already answered.

---

## Troubleshooting

- **No `.version` properties found:** The APIs may not be added to the project yet. Use Anypoint Studio's Project Properties → API Specs tab to add the API dependency first, which will create the property in `pom.xml`.
- **`mvn` fails after version change:** pom.xml is automatically restored. Check the Maven error for the root cause — the selected version may have an incompatible dependency or the Exchange asset may not be fully published.
- **Multiple properties for the same API:** If the same artifactId appears more than once under `<properties>`, update all occurrences to keep the project consistent.
- **`scripts/fetch_versions.sh` rows come back with `"source": "error"` due to an auth error:** Run `anypoint-cli-v4 conf` to verify credentials, or re-authenticate with `anypoint-cli-v4 conf username <user>` / `anypoint-cli-v4 conf password <pass>`. If `ANYPOINT_BEARER` is set in the environment alongside `ANYPOINT_CLIENT_ID`/`ANYPOINT_CLIENT_SECRET`, unset the client-credential vars — the CLI rejects calls when multiple auth methods are simultaneously active.
- **A row comes back with `"source": "describe-fallback"` and a `versions` list that looks too short:** Expected — `exchange asset list` found zero rows for that `groupId`/`assetId`, so the script fell back to the version-anchored `describe` lookup, which can under-report versions newer than the current one (see **Version Discovery**). Confirm the artifactId matches the Exchange `assetId` exactly (case-sensitive) and that the account is authenticated against the correct organization — a private asset published under a different org than the CLI session's selected org will not appear via `list`. As a next step, try `anypoint-cli-v4 exchange asset list <artifactId> --output json` manually (unfiltered) to see whether the asset shows up under a different `groupId` than what's in `pom.xml`.
- **`"source": "error"` with no obvious auth/network cause:** Both `exchange asset list` and the `describe` fallback failed for that specific asset. Re-run just that one API through `scripts/fetch_versions.sh` in isolation to see the underlying CLI error more clearly, or run the two `anypoint-cli-v4` commands by hand to inspect stderr directly.

---

## Related Skills

- **manage-global-configurations** — Set up API AutoDiscovery (`api.id`) and other global elements that pair with these API versions
- **build-mule-integration** — Build and package the Mule project after version changes
