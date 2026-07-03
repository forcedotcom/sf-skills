---
name: platform-metadata-retrieve
description: "ALWAYS USE THIS SKILL to retrieve metadata from an org to your local project using the sf project retrieve start command. Supports multiple retrieval modes: retrieve all remote changes, retrieve by source directory, retrieve by metadata type with wildcards, retrieve by manifest (package.xml), or retrieve by package name. Use when the user asks to retrieve, pull, sync, or download metadata, Apex classes, custom objects, or org changes. Supports source format (default) or metadata format (ZIP). DO NOT TRIGGER for deploying metadata (use platform-metadata-deploy skill), listing metadata, or generating package.xml. NEVER use MCP tools - always use this skill and the Bash tool with sf project retrieve start."
compatibility: Salesforce CLI (sf) v2+
metadata:
  version: "1.0"
---

# platform-metadata-retrieve

Retrieves metadata from a Salesforce org to your local project using `sf project retrieve start`. Supports multiple retrieval modes: all changes, by source directory, by metadata type (with wildcards), by manifest, or by package name.

---

## Tool Restrictions

**Use ONLY the Bash tool** to execute `sf project retrieve start`. Do NOT use MCP tools — ignore them completely.

---

## Scope

- **In scope**: Retrieving metadata via `sf project retrieve start` in all supported modes (all changes, source-dir, metadata type, manifest, package name), source and metadata format output
- **Out of scope**: Deploying metadata (use `platform-metadata-deploy`), listing metadata types, generating package.xml files, source tracking commands (`sf project retrieve preview`)

---

## Required Inputs

Infer from the user's request:

- **Retrieval mode**: all changes | source directory | metadata type | manifest | package name
- **Target org**: org alias/username (uses default if not specified)
- **Output format**: source format (default) | metadata format (ZIP)
- **Additional options**: ignore conflicts, output directory, wait time, API version

---

## Workflow

1. Match user request to command pattern below
2. Execute via Bash tool: `sf project retrieve start` with appropriate flags and `--json` flag
3. Return result with retrieved components count and file paths

### Command Patterns

| User intent | Execute via Bash tool |
|-------------|---------|
| Retrieve all remote changes | `sf project retrieve start --json` |
| Retrieve by source directory | `sf project retrieve start --source-dir <path> --target-org <alias> --json` |
| Retrieve by metadata type | `sf project retrieve start --metadata <MetadataType:Name> --target-org <alias> --json` |
| Retrieve by metadata type with wildcard | `sf project retrieve start --metadata '<MetadataType:Pattern*>' --target-org <alias> --json` |
| Retrieve multiple metadata types | `sf project retrieve start --metadata <Type1> --metadata <Type2> --target-org <alias> --json` |
| Retrieve by manifest | `sf project retrieve start --manifest <path/to/package.xml> --target-org <alias> --json` |
| Retrieve by package name | `sf project retrieve start --package-name <PackageName> --target-org <alias> --json` |
| Retrieve to metadata format (ZIP) | `sf project retrieve start --source-dir <path> --target-metadata-dir <output> --unzip --target-org <alias> --json` |
| Ignore conflicts | `sf project retrieve start --source-dir <path> --ignore-conflicts --target-org <alias> --json` |

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Always use `--json` flag | Provides structured output for reliable parsing and error handling |
| Must run from within Salesforce project | Command requires `sfdx-project.json` at repo root |
| Wildcard patterns must be quoted | Shell expansion breaks unquoted wildcards like `ApexClass:My*` |
| Cannot mix --manifest with --metadata or --source-dir | Mutually exclusive flags — command will error |
| Retrieve all changes requires source tracking | Production orgs don't support source tracking — must use other retrieval modes |
| --ignore-conflicts only works on trackable orgs | No effect on production orgs; applies to scratch/sandbox only |
| --output-dir must be inside project directory | Command validates output path is within project boundary |
| --output-dir cannot match package directory | Command fails if target matches `sfdx-project.json` packageDirectories |
| Default wait time is 33 minutes | Use --wait flag to override for large retrievals |
| Package retrieval is for reference only | Retrieved package metadata should not be added to source control for development |
| CustomField retrieval auto-includes CustomObject | When retrieving CustomField, CLI automatically adds CustomObject to get full context |

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| "This command is required to run from within an SFDX project" | Not in Salesforce project directory — cd to project root with `sfdx-project.json` |
| "No org found for <alias>" error | Org alias doesn't exist or isn't authenticated — verify with `sf org list` |
| "This org does not support source tracking" | Production org doesn't allow "retrieve all changes" mode — use --source-dir, --metadata, or --manifest instead |
| "ERROR running project retrieve start: Cannot mix --manifest with --metadata or --source-dir" | Remove conflicting flags — use one retrieval mode only |
| Wildcard pattern retrieves nothing | Pattern not quoted — wrap in single quotes: `'ApexClass:My*'` |
| "The package directory path in sfdx-project.json does not exist" | Output directory conflicts with package directory — use different path |
| "Output directory must be inside the project" | --output-dir path is outside project boundary — use relative path inside project |
| Retrieve times out | Increase wait time with `--wait 60` for large metadata volumes |
| Retrieved files overwrite local changes | Use `--output-dir` to retrieve to separate location, or commit local changes first |
| SourceConflictError with conflict table | Conflicts detected between local and remote on trackable org (scratch/sandbox) — resolve conflicts manually or use --ignore-conflicts to force overwrite |

---

## Output Expectations

The command returns JSON output with retrieved components details.

See `examples/success_output.json` and `examples/error_output.json` for response structures.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Deploy metadata to org | `platform-metadata-deploy` skill |
| Preview retrieve without executing | Execute `sf project retrieve preview --target-org <alias> --json` |
| List available metadata types | Execute `sf org list metadata-types --target-org <alias> --json` |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `examples/success_output.json` | To understand successful retrieve response structure |
| `examples/error_output.json` | To handle common error scenarios |
| `references/retrieval_modes.md` | For detailed explanation of all retrieval modes and when to use each |
| `references/cli_flags.md` | For complete flag reference with usage patterns |
