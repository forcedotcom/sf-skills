# Examples Directory

This directory contains example outputs for the three workflows supported by the `dx-org-manage` skill.

## Structure

```text
examples/
├── README.md                          # This file
├── scratch-orgs/                      # Scratch org creation examples
│   ├── success_definition_file.json
│   ├── success_edition.json
│   ├── error_no_devhub.json
│   └── error_timeout.json
└── snapshots/                         # Snapshot creation examples
    ├── success_output.json
    └── error_output.json
```

## scratch-orgs/

Examples of `sf org create scratch` command outputs for all four creation methods.

- **success_definition_file.json** - Successful creation using `--definition-file`
- **success_edition.json** - Successful creation using `--edition developer`
- **success_snapshot.json** - Successful creation using `--snapshot`
- **error_no_devhub.json** - Error when Dev Hub not authenticated
- **error_timeout.json** - Timeout error (exit code 69)

## snapshots/

Examples of `sf org create snapshot` command outputs.

- **success_output.json** - Successful snapshot creation
- **error_output.json** - Common error scenarios (NOT_FOUND, duplicate name, etc.)

## Usage

These examples help illustrate:
1. Expected JSON/text response formats
2. Common error patterns
3. How to parse success indicators (`username`, `orgId`, etc.)
4. Async operation handling (snapshot creation, timeout scenarios)

Reference these when building eval datasets or troubleshooting command outputs.
