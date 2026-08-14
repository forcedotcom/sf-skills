# Opening Orgs

Opens a Salesforce org or specific metadata artifact in a browser using `sf org open`. Handles all variants: default org, alias or username, browser selection, incognito mode, path navigation, metadata file → Builder, and URL-only output.

---

## Required Inputs

Infer from the user's request:

- **Target org**: Use default org unless a specific alias/username is mentioned
- **What to open**: Path, file, or org home
- **Browser**: Only include if explicitly requested (chrome, firefox, edge)
- **Incognito**: Only if user says "private" or "incognito"
- **URL only**: the skill must **never run `--url-only`**. It returns a credential-equivalent frontdoor token (`/secur/frontdoor.jsp?otp=`/`sid=`) that must not enter agent context or an artifact. If the user explicitly asks for the URL and not a browser — e.g. "URL only", "just give me the link", "don't open a/the browser", or a headless/remote context — tell them to run `sf org open --url-only` themselves in their own terminal (same as `sf org display --verbose`). Always open the browser otherwise; plain `sf org open` never prints a login URL.

Do not ask for clarification - infer and execute immediately.

---

## Workflow

1. **Match user request** to command in table below
2. **Execute via Bash tool**: `sf org open` with appropriate flags
3. **Return result**

If error occurs:
- "no target org" → advise: `sf config set target-org <alias>`
- auth error → advise: `sf org login web --alias <alias>`

### Command Decision Table

| User intent | Execute via Bash tool |
|-------------|---------|
| Open default org | `sf org open` |
| Open specific org | `sf org open --target-org <alias>` |
| Open in specific browser | `sf org open --browser chrome` (or firefox, edge) |
| Private/incognito mode | `sf org open --private` |
| Navigate to path | `sf org open --path '<path>'` |
| Open local file | `sf org open --source-file <file-path>` |
| Get URL only | **Do not run from the skill** — tell the user to run `sf org open --url-only` locally (it returns a live login token). |

**Note:** Flags `--private`, `--url-only`, `--browser` are mutually exclusive. The skill never runs `--url-only`; if the user needs the raw URL (optionally with `--path`/`--source-file`), direct them to run it themselves in their terminal.

---

## Common Paths

### Setup Pages
```bash
# Setup home
sf org open --path '/lightning/setup/SetupOneHome/home'

# Object Manager
sf org open --path '/lightning/setup/ObjectManager/home'

# Users
sf org open --path '/lightning/setup/ManageUsers/home'

# Permission Sets
sf org open --path '/lightning/setup/PermSets/home'

# Flows
sf org open --path '/lightning/setup/Flows/home'

# Custom Metadata Types
sf org open --path '/lightning/setup/CustomMetadata/home'
```

### App Pages
```bash
# App Launcher
sf org open --path '/lightning/setup/NavigationMenus/home'

# Reports
sf org open --path '/lightning/o/Report/home'

# Dashboards
sf org open --path '/lightning/o/Dashboard/home'
```

---

## Opening Metadata Files

### Supported Metadata Types

`--source-file` works with these metadata types:
- **FlexiPage** (Lightning pages) → Lightning App Builder
- **Flow** → Flow Builder
- **ApexPage** (Visualforce) → Visualforce Page Editor
- **ApexClass** → Apex Class detail page
- **CustomObject** → Object Manager

### Important Constraints

| Constraint | Behavior |
|-----------|----------|
| Metadata must be deployed in the org | CLI queries org for record ID; undeployed metadata causes error or fallback |
| FlexiPage fallback | Silently falls back to `/lightning/setup/FlexiPageList/home` if not found |
| Flow error | Throws `FlowIdNotFound` if Flow not deployed |
| ApexClass error | Throws `ApexClassIdNotFound` if class not deployed |
| CustomObject error | Throws `CustomObjectIdNotFound` if object not deployed |

### Example Commands

```bash
# Open Lightning page in App Builder
sf org open --source-file force-app/main/default/flexipages/Account_Record_Page.flexipage-meta.xml

# Open Flow in Flow Builder
sf org open --source-file force-app/main/default/flows/MyFlow.flow-meta.xml

# Open Apex class
sf org open --source-file force-app/main/default/classes/MyController.cls
```

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| `--path` and `--source-file` are mutually exclusive | Both control navigation destination; choose one |
| `--source-file` supported types: FlexiPage, Flow, ApexPage, ApexClass, CustomObject | CLI queries the org for the record ID; unsupported types or undeployed metadata fall back silently (FlexiPage) or throw a named error (Flow/ApexClass/CustomObject) |
| Do not hardcode `force-app/main/default/` for `--source-file` | Project package paths vary; use the path the user provides or read `sfdx-project.json` |
| Must use Bash tool, not MCP tools | MCP tools like `list_all_orgs` cannot open orgs in browser |

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| No target org found | Set default: `sf config set target-org <alias>` or specify `--target-org <alias>` |
| Auth error | Re-authenticate: `sf org login web --alias <alias>` |
| `--source-file` opens wrong page or throws `FlowIdNotFound` / `ApexClassIdNotFound` / `CustomObjectIdNotFound` | Metadata is not deployed in the org. Run `sf project deploy start --source-file <path> --target-org <alias>` first. FlexiPage silently falls back to org home; Flow/ApexClass/CustomObject throw an error. |
| Metadata file opens wrong Builder | Verify the file extension matches the metadata type (e.g. `.flow-meta.xml` for Flow Builder) |
| User wants the raw login URL | The skill never runs `--url-only` (it returns a live login token). Tell the user to run `sf org open --url-only` in their own terminal. |
| Path not found / 404 | Verify the path is correct; some paths require specific permissions or licenses |

---

## Output Expectations

### Default behavior
- Opens the specified org/path in the system's default browser
- No console output on success (plain `sf org open`)
- **No artifact.** Open is the one operation in this skill that writes no file. Report to the user that the org/path was opened; do not write `org-url-result.json`.

### Never use `--json` for open
`sf org open --json` returns a **live login URL** in `result.url`: `https://<host>/secur/frontdoor.jsp?otp=<token>` (or `?sid=<token>`). That token is credential-equivalent — the same reason `--url-only` is banned — and pulling it into agent context (even to redact it before writing a file) is the exact S1 leak the plain command avoids. The skill therefore runs plain `sf org open` (browser launch), never `--json`, and writes no artifact. The working login is delivered by the browser launch — never through agent context or a written file.

### `--url-only` (skill does not run this)
`sf org open --url-only` returns a frontdoor login URL (`/secur/frontdoor.jsp?` with an `otp=`/`sid=` token) that is **credential-equivalent** — anyone holding it is logged into the org. Because that would place a live auth token into agent context and the written artifact, the skill **must not run or serialize `--url-only`**. When the user needs the raw URL (headless/remote, or an explicit "just the link"), instruct them to run `sf org open --url-only` themselves in their terminal — the same way `sf org display --verbose` is left to the user. Always open the browser from the skill; plain `sf org open` never emits this URL.

### With `--source-file`
- Opens the metadata in its appropriate Builder/Editor
- Example: FlexiPage → Lightning App Builder, Flow → Flow Builder
