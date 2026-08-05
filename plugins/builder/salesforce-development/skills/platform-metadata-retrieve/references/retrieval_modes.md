# Retrieval Modes

Complete guide to the five retrieval modes supported by `sf project retrieve start`.

## Mode 1: Retrieve All Remote Changes

**When to use:** Sync all org changes to local project (most common workflow)

```bash
sf project retrieve start --json
```

- Retrieves all metadata that changed in the org since last sync
- Only works with orgs that allow source tracking (scratch/sandbox)
- Does not work with production orgs
- Most common command for daily development workflow

## Mode 2: Retrieve by Source Directory

**When to use:** Pull specific directory/file from org

```bash
sf project retrieve start --source-dir force-app --target-org my-org --json
sf project retrieve start --source-dir force-app/main/default/classes --target-org my-org --json
sf project retrieve start --source-dir force-app/main/default/classes/AccountService.cls --target-org my-org --json
```

- Can target entire directory or single file
- Retrieves directory contents recursively
- Multiple `--source-dir` flags supported
- Works with all org types (scratch, sandbox, production)

**Multiple directories:**

```bash
sf project retrieve start --source-dir force-app/main/default/classes --source-dir force-app/main/default/objects --json
```

## Mode 3: Retrieve by Metadata Type

**When to use:** Pull specific metadata types or components

```bash
sf project retrieve start --metadata ApexClass --json
sf project retrieve start --metadata ApexClass:AccountService --json
sf project retrieve start --metadata 'ApexClass:Account*' --json
```

- Retrieve all components of a type: `--metadata ApexClass`
- Retrieve specific component: `--metadata ApexClass:AccountService`
- Retrieve with wildcard pattern: `--metadata 'ApexClass:Account*'` (requires quotes)
- Multiple `--metadata` flags supported
- Works with all org types

**Wildcards:**

```bash
sf project retrieve start --metadata 'CustomObject:SBQQ__*' --json
sf project retrieve start --metadata 'ListView:Case*' --json
```

**Multiple types:**

```bash
sf project retrieve start --metadata CustomObject --metadata ApexClass --json
```

## Mode 4: Retrieve by Manifest (package.xml)

**When to use:** Pull metadata listed in package.xml

```bash
sf project retrieve start --manifest path/to/package.xml --json
```

- Retrieves all components specified in the manifest file
- Cannot be combined with `--metadata` or `--source-dir`
- Works with all org types
- Useful for CI/CD pipelines and release management

## Mode 5: Retrieve by Package Name

**When to use:** Extract package metadata for reference only

```bash
sf project retrieve start --package-name MyPackageName --json
sf project retrieve start --package-name "Package With Spaces" --json
```

- Retrieves metadata into child directory matching package name
    - Cannot be used with the `--output-dir` flag 
- Retrieved metadata is **for reference only** — not for development/deployment
- Do not add to source control
- For package development, use manifest or source-dir modes instead
- Works with all org types

**Multiple packages:**

```bash
sf project retrieve start --package-name Package1 --package-name "Package With Spaces" --package-name Package3 --json
```

## Output Format Options

### Source Format (Default)

```bash
sf project retrieve start --source-dir force-app --json
```

- Retrieves in Salesforce DX source format
- Files written to package directories defined in `sfdx-project.json`
- Default behavior

### Metadata Format (ZIP)

```bash
sf project retrieve start --source-dir force-app --target-metadata-dir output --json
```

- Retrieves as ZIP file in metadata format
- Use `--unzip` to automatically extract contents
- Use `--zip-file-name` to specify ZIP filename
- Use `--single-package` for single package directory structure

**Extract automatically:**

```bash
sf project retrieve start --source-dir force-app --target-metadata-dir output --unzip --json
```

## Conflict Handling

### Ignore Conflicts (Scratch/Sandbox Only)

**⚠️ Warning:** Do not use `--ignore-conflicts` flag without confirming with the user first. This flag overwrites local changes and may result in lost work.

```bash
sf project retrieve start --source-dir force-app --ignore-conflicts --json
```

- Overwrites local files even if they have uncommitted changes
- Only works on orgs that allow source tracking (scratch/sandbox)
- No effect on production orgs

### Retrieve to Separate Directory

```bash
sf project retrieve start --source-dir force-app --output-dir retrieved-backup --json
```

- Retrieves to custom directory instead of default package directory
- Cannot use directory that matches `sfdx-project.json` packageDirectories
- Useful for comparing org state with local state
- Running multiple times adds/overwrites files in target directory

## Common Patterns

### Retrieve Specific Apex Class

```bash
sf project retrieve start --metadata ApexClass:MyApexClass --ignore-conflicts --json
```

### Retrieve All Custom Objects with Namespace

```bash
sf project retrieve start --metadata 'CustomObject:SBQQ__*' --json
```

### Retrieve All List Views for Standard Object

```bash
sf project retrieve start --metadata 'ListView:Case*' --json
```

### Retrieve to Metadata Format and Extract

```bash
sf project retrieve start --source-dir force-app --target-metadata-dir output --unzip --json
```
