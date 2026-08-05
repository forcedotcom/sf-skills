# Creating Scratch Orgs

Detailed workflow for creating Salesforce scratch orgs using `sf org create scratch`. Supports four creation methods: definition file, edition flag, snapshot, and org shape.

---

## Required Inputs

Gather or infer before proceeding:

- **Dev Hub org**: Username or alias of authenticated Dev Hub (or use default from `target-dev-hub` config)
- **Creation method**: Which approach to use (see Workflow step 1)
- **Alias**: Optional but recommended for easy reference

Optional but commonly used:
- **Duration**: Days before org expires (default: 7, max: 30)
- **Set as default**: Whether to make this the default org
- **Source tracking**: Whether to enable (default: yes, disable for CI/CD performance)

---

## Workflow

### 1. Identify creation method

Determine which approach based on user request:

| Method | When to use | Required flags |
|--------|-------------|----------------|
| Definition file | User provides config file or needs org features/settings | `--definition-file <path>` |
| Edition only | Quick simple org, no special config needed | `--edition <edition>` |
| Snapshot | Clone from existing snapshot | `--snapshot <name>` |
| Org shape | Mimic another org's structure | `--source-org <id>` |

**Mutually exclusive**: `--edition`, `--snapshot`, and `--source-org` cannot be combined.

### 2. Verify Dev Hub authentication

Check if Dev Hub is authenticated:
- If `--target-dev-hub` not provided, check `sf config get target-dev-hub`
- If no Dev Hub configured, prompt user to authenticate: `sf org login web --set-default-dev-hub`

### 3. Build the command

Construct based on creation method:

**Definition file approach:**
```bash
sf org create scratch --definition-file <path> --target-dev-hub <alias> --alias <name> --json
```

**Edition-only approach:**
```bash
sf org create scratch --edition developer --target-dev-hub <alias> --alias <name> --json
```

**Snapshot approach:**
```bash
sf org create scratch --snapshot <name> --target-dev-hub <alias> --alias <name> --json
```

**Org shape approach:**
```bash
sf org create scratch --source-org <id> --target-dev-hub <alias> --alias <name> --json
```

**Common optional flags:**
- `--duration-days <days>` — Set expiration (default 7, max 30)
- `--set-default` — Make this the default org
- `--no-track-source` — Disable source tracking for CI/CD performance
- `--wait <minutes>` — Wait for completion (default 5 minutes, min 2)
- `--async` — Return immediately, don't wait for completion

**⚠️ CRITICAL: This is a BLOCKING command**
- The command **WAITS** until the scratch org is fully created (or times out)
- When the command returns success, the org is **READY TO USE** — do NOT poll with `sf org list` waiting for it to become ready
- The JSON response with `username` and `orgId` means creation is **COMPLETE**
- Only use `--async` if you want to check status later with `sf org resume scratch`
- **Note**: SKILL.md Step 4 requires running `sf org list --json` once after creation for artifact collection (not for polling status)

**Before executing, verify:**
- [ ] `--json` flag is present in the command
- [ ] At least ONE of `--edition`, `--snapshot`, `--source-org`, or `--definition-file` is specified (flags can override definition file values)
- [ ] `--snapshot` and `--source-org` are not combined (mutually exclusive)
- [ ] `--target-dev-hub` is resolved (either in command or from config)

### 4. Handle async creation

If `--async` or `--wait` timeout occurs:
- CLI displays: "The scratch org did not complete within your wait time."
- CLI automatically shows the resume command with Request ID
- Timeout exits with code 69
- User can resume with the displayed command: `sf org resume scratch --job-id <request-id> --json`

### 5. Report result

When the command returns, check JSON response. If it contains `username` and `orgId`, the org is **COMPLETE and READY**. Do NOT run additional commands to verify completion.

Successful creation returns:
```json
{
   "username": "test-...@example.com",
   "orgId": "00D...",
   "scratchOrgInfo": {
      "Id": "2SR...",
      "ScratchOrg": "00D...",
      "SignupUsername": "test-...@example.com"
   }
}
```

This JSON response means: org is created, authenticated, and ready for `sf org open`, `sf project deploy`, or any other commands.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Always include `--json` flag | Returns structured output for parsing success/failure |
| **Command blocks until completion — do NOT poll for status** | The command waits until the org is created (or times out). When it returns with `username` and `orgId` in JSON, the org is ready. Do NOT poll repeatedly with `sf org list` waiting for it to become ready — the command already waited for you. Only exception: if using `--async` flag or command timed out (exit code 69), then use `sf org resume scratch` to check status. **Note**: SKILL.md Step 4 requires a single `sf org list --json` call after creation for artifact collection (not polling) |
| Dev Hub must be authenticated | Scratch org creation requires Dev Hub access |
| `--edition`, `--snapshot`, `--source-org` are mutually exclusive | Only one creation source allowed per command |
| Definition file overrides can use flags | Flags like `--edition`, `--name`, `--username`, `--release`, `--admin-email` override definition file values |
| Snapshot requires same Dev Hub | Snapshot must be created in the same Dev Hub you're using |
| Duration max is 30 days | Platform limit for scratch org expiration |
| Source tracking enabled by default | Disable with `--no-track-source` only for CI/CD or performance needs |

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `No default Dev Hub org found` | Authenticate Dev Hub with `sf org login web --set-default-dev-hub` or specify `--target-dev-hub` |
| `NamedOrgNotFoundError` on Dev Hub | Dev Hub org is not authenticated — run `sf org login web` |
| `edition value must be one of` | Invalid edition specified — use developer, enterprise, group, professional, or partner variants |
| `Snapshot not found` | Snapshot doesn't exist in this Dev Hub — run `sf org list snapshot` to see available |
| `sourceOrg value must be 15 or 18 characters` | Org shape ID format incorrect — use output from `sf org list shape` |
| `The org could not be created` | Generic creation failure — check Dev Hub limits, licensing, or try again |
| Timeout during creation (exit code 69) | Command timed out waiting for org. CLI displays the resume command with Request ID. User can run the displayed command or increase `--wait` time (min 2 minutes) for next attempt |
| `Definition file not found` | Path to definition file is incorrect — verify file exists |
| Partner editions unavailable | Partner editions only work if Dev Hub is a Partner Business Org |

---

## Output Expectations

Deliverables:
- **Created scratch org**: Authenticated and ready to use
- **JSON response**: Contains `username`, `orgId`, `scratchOrgInfo` with Request ID
- **Local auth info**: Stored in `.sf/` directory for future CLI commands

If `--async` used or timeout occurs:
- **Request ID**: Returned in `scratchOrgInfo.Id` (format: `2SR...`)
- **Resume command**: `sf org resume scratch --job-id <request-id> --json`
- **Timeout exit code**: 69

---

## Additional Resources

- See `definition_file_options.md` for org features, settings, and configuration templates
- See `edition_types.md` for available edition types and when to use each
