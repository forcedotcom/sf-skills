# SF CLI Bot Reference

Essential SF CLI command sequence for Mode A (org-backed retrieval) after inputs are finalized (`--org-alias`, `--bot`, `--bot-version`).

Do not use this reference in Mode B (offline metadata input). In offline mode, skip SF CLI retrieval and continue with extraction/mapping from local XML metadata files.

## 1) Prerequisite checks

```bash
sf --version
sf org display --json --target-org <org-alias>
```

If no orgs are available (no authenticated orgs are found), branch on the effective `--interactive` value:

- **`--interactive=true`**: ask the customer to log in to an org using:

```bash
sf org login web --instance-url <LOGIN_URL> --alias <ALIAS>
```

  When asking, inform the customer about the default values so they can accept them or override:
  - `--instance-url` defaults to `https://login.salesforce.com` when omitted. Tell the customer to use the default for production and Developer Edition orgs, `https://test.salesforce.com` for sandboxes.

- **`--interactive=false`**: do NOT prompt. Halt with an explicit error: `No authenticated org found for the provided --org-alias; run sf org login web and retry.`

## 2) Validate bot and version

`BotVersion.VersionNumber` is a numeric field, but `<bot-version>` is supplied in the `v1`/`v2`/`v3` format. Derive `<version-number>` by stripping the leading `v` from `<bot-version>` (e.g. `v1` -> `1`, `v12` -> `12`) and use that numeric value in the SOQL filter. Keep the original `<bot-version>` (`vN`) form for the metadata retrieval in section 3.

Listing bots:
```bash
sf data query --json --target-org <org-alias> \
  --query "SELECT BotDefinition.MasterLabel FROM BotDefinition WHERE Type = 'Bot'"
```

Listing bot versions:
```bash
sf data query --json --target-org <org-alias> \
  --query "SELECT Id, VersionNumber, Status FROM BotVersion WHERE BotDefinition.Type = 'Bot'"
```

## 3) Retrieve bot metadata

Before retrieval, ensure an SF project directory exists:

1. If no project exists for this migration run (`sfdx-project.json` doesn't exist), create one:
   `sf project generate --name <bot-name>-<bot-version>-agent --template "empty" --output-dir "."`
2. Change into that project directory.
3. Run all remaining sf cli commands from that same project directory.

```bash
sf project retrieve start --target-org <org-alias> \
  --metadata "Bot:<bot-name>" "BotVersion:<bot-name>.<bot-version>"
```

## 4) Retrieve related ML domains (only if referenced)

After bot metadata retrieval, discover referenced ML domains from the retrieved bot XML metadata using the same pattern as the migration script (`relatedMlIntent` entries in `<Domain.Intent>` format), then retrieve each domain.

Bot XML exists at: `force-app/main/default/bots/<bot-name>/<bot-name>.bot-meta.xml` (relative to the generated SFDX project directory from section 3).

Use this sequence:

1. Read the bot metadata XML file.
2. Find all `relatedMlIntent` values.
3. For each value, split on `.` and keep only the domain name prefix.
4. De-duplicate the discovered domain names.
5. For each discovered domain, run:
   `sf project retrieve start --target-org <org-alias> --metadata "MlDomain:<domain_name>"`

If no `relatedMlIntent` entries are found, skip MLDomain retrieval.

## 5) Retrieve invocation dependencies (Apex/Flow)

The pipeline extracts invocation names from bot metadata, then retrieves only those exact classes/flows.

### Apex classes

```bash
sf project retrieve start --target-org <org-alias> --manifest <apex-package.xml>
```

`<apex-package.xml>` should contain only required classes:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>ClassA</members>
    <members>ClassB</members>
    <name>ApexClass</name>
  </types>
  <version>67.0</version>
</Package>
```

### Flows

```bash
sf project retrieve start --target-org <org-alias> --manifest <flow-package.xml>
```

`<flow-package.xml>` should contain only required flows:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>FlowA</members>
    <members>FlowB</members>
    <name>Flow</name>
  </types>
  <version>67.0</version>
</Package>
```
