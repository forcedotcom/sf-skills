# CLI Flags Reference

Complete reference for `sf project retrieve start` command flags.

## Target Org Flag (Optional When Default Is Set)

**Note:** `--target-org` is omitted when a default org is set via `sf config set target-org`. Only include this flag when the user specifies a non-default org or no default is configured.

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--target-org` | `-o` | Username or alias of target org (omit if using default) | `--target-org my-org` |

## Retrieval Mode Flags (Mutually Exclusive Groups)

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--source-dir` | `-d` | File paths to retrieve from org | `--source-dir force-app` |
| `--metadata` | `-m` | Metadata component names (wildcards supported) | `--metadata ApexClass:MyClass*` |
| `--manifest` | `-x` | Path to manifest (package.xml) file | `--manifest config/package.xml` |
| `--package-name` | `-n` | Package names to retrieve (reference only) | `--package-name MyPackage` |

**Note:** Cannot combine `--manifest` with `--metadata` or `--source-dir`. Choose one retrieval mode.

## Optional Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--api-version` | `-a` | Target API version for retrieve | `--api-version 66.0` |
| `--ignore-conflicts` | `-c` | Ignore conflicts and overwrite local files | `--ignore-conflicts` |
| `--output-dir` | `-r` | Directory root for retrieved source files | `--output-dir retrieved` |
| `--wait` | `-w` | Minutes to wait for completion (default: 33) | `--wait 60` |

## Metadata API Format Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--target-metadata-dir` | Directory for metadata format files or ZIP | `--target-metadata-dir output` |
| `--unzip` | Extract files from retrieved ZIP | `--unzip` |
| `--single-package` | ZIP points to single package directory | `--single-package` |
| `--zip-file-name` | Filename for retrieved ZIP | `--zip-file-name metadata.zip` |

## Usage Patterns

### Basic Retrieve All Changes

```bash
sf project retrieve start --json
```

### Retrieve by Source Directory

```bash
sf project retrieve start --source-dir force-app --target-org my-org --json
```

### Retrieve Multiple Directories

```bash
sf project retrieve start --source-dir force-app/main/default/classes --source-dir force-app/main/default/objects --json
```

### Retrieve by Metadata Type

```bash
sf project retrieve start --metadata ApexClass --target-org my-org --json
```

### Retrieve Specific Component

```bash
sf project retrieve start --metadata ApexClass:AccountService --target-org my-org --json
```

### Retrieve with Wildcard

```bash
sf project retrieve start --metadata 'ApexClass:Account*' --target-org my-org --json
```

### Retrieve Multiple Metadata Types

```bash
sf project retrieve start --metadata CustomObject --metadata ApexClass --target-org my-org --json
```

### Retrieve by Manifest

```bash
sf project retrieve start --manifest config/package.xml --target-org my-org --json
```

### Retrieve by Package Name

```bash
sf project retrieve start --package-name MyPackage --target-org my-org --json
```

### Retrieve Multiple Packages

```bash
sf project retrieve start --package-name Package1 --package-name "Package With Spaces" --target-org my-org --json
```

### Retrieve to Metadata Format

```bash
sf project retrieve start --source-dir force-app --target-metadata-dir output --target-org my-org --json
```

### Retrieve and Extract ZIP

```bash
sf project retrieve start --source-dir force-app --target-metadata-dir output --unzip --target-org my-org --json
```

### Ignore Conflicts

```bash
sf project retrieve start --source-dir force-app --ignore-conflicts --target-org my-org --json
```

### Custom Output Directory

```bash
sf project retrieve start --source-dir force-app --output-dir retrieved --target-org my-org --json
```

### Override Wait Time

```bash
sf project retrieve start --manifest config/package.xml --wait 60 --target-org my-org --json
```

### Override API Version

```bash
sf project retrieve start --source-dir force-app --api-version 66.0 --target-org my-org --json
```
