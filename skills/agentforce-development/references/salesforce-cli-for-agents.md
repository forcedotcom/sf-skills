# Salesforce CLI for Agents Reference

Command-by-command reference for Salesforce CLI `sf` commands covering agent generation, validation, preview, deployment, publishing, activationt/deactivation, testing, and Einstein Agent User setup.

---

## 1. Global Rules

Always include `--json` as the FIRST flag after the base command. This ensures machine-readable output and prevents mid-tier LLMs from dropping the flag.

```bash
# CORRECT — --json first
sf agent validate authoring-bundle --json --api-name Local_Info_Agent

# WRONG — --json at the end or missing
sf agent validate authoring-bundle --api-name Local_Info_Agent --json
sf agent validate authoring-bundle --api-name Local_Info_Agent
```

Multiple metadata types in `--metadata` are space-separated arguments, NOT comma-separated. Wildcard patterns must be quoted.

```bash
# CORRECT
sf project deploy start --json --metadata ApexClass Flow
sf project retrieve start --json --metadata "AiAuthoringBundle:Local_Info_Agent_*"

# WRONG
sf project deploy start --json --metadata ApexClass,Flow
sf project retrieve start --json --metadata AiAuthoringBundle:Local_Info_Agent_*
```

---

## 2. Generate

Create a new AiAuthoringBundle directory with boilerplate `.agent` and `.bundle-meta.xml` files.

```bash
sf agent generate authoring-bundle --json --no-spec --name "Agent Label" --api-name Agent_API_Name
```

- `--name`: Human-readable label (quoted if it contains spaces).
- `--api-name`: Developer name. Must be a valid Salesforce API name (letters, numbers, underscores). This becomes the directory name under `aiAuthoringBundles/`.
- `--no-spec`: Skip interactive agent spec generation. Always include this flag — the interactive spec generator cannot be used programmatically.

The generated directory is placed at `<default_package_directory>/main/default/aiAuthoringBundles/<api-name>/`. Read `sfdx-project.json` to find the default package directory path.

- `--force-overwrite`: Overwrites an existing bundle without interactive confirmation. DO NOT use unless intending to overwrite an existing authoring bundle.

### Generated Output

The generate command creates this structure:

```
force-app/main/default/aiAuthoringBundles/
└── Agent_API_Name/
    ├── Agent_API_Name.agent            # Agent Script file
    └── Agent_API_Name.bundle-meta.xml  # Metadata XML
```

**Naming rules:** The folder name, `.agent` filename, and `.bundle-meta.xml` filename must always match `--api-name` exactly (case-sensitive).

---

## 3. Validate

Check Agent Script for syntax errors, structural issues, and missing declarations. Always validate before deploying.

```bash
sf agent validate authoring-bundle --json --api-name Agent_API_Name
```

- `--api-name`: The AiAuthoringBundle directory name (same as `config.developer_name` in the `.agent` file).
- Validates against local files only. Does not contact the org.

---

## 4. Deploy

### Deploy Apex, Flow, or other backing logic

```bash
sf project deploy start --json --metadata ApexClass:ClassName
```

Deploy backing logic BEFORE deploying the AiAuthoringBundle. The bundle's action targets reference these components, and the platform validates they exist during bundle deploy.

ALWAYS deploy each stub class IMMEDIATELY after customizing it. ALWAYS fix deploy errors BEFORE generating and deploying the next stub.

### Deploy the AiAuthoringBundle

```bash
sf project deploy start --json --metadata AiAuthoringBundle:Agent_API_Name
```

This deploys ONLY the AiAuthoringBundle. A bare `sf project deploy start` (no `--metadata`) deploys ALL changed metadata in the project, which can inadvertently deploy agent metadata during routine development. Always scope deploys explicitly.

### Safe routine deploy (non-agent metadata)

```bash
sf project deploy start --json --metadata ApexClass Flow
```

Explicitly list the metadata types to deploy. This avoids accidentally deploying AiAuthoringBundle changes.

---

## 5. Publish

Convert a deployed AiAuthoringBundle into a running agent. Publishing creates the runtime entity graph (Bot, BotVersion, GenAiPlannerBundle) from the authoring bundle.

```bash
sf agent publish authoring-bundle --json --api-name Agent_API_Name
```

- `--api-name`: The AiAuthoringBundle directory name.
- The agent must be deployed before it can be published.
- The `default_agent_user` in the `.agent` file must exist in the target org and have the Einstein Agent license. An invalid user produces a misleading "Internal Error, try again later" message. See Section 12 for creation steps and [Agent User Setup & Permissions](agent-user-setup.md) for required permissions.
- **Publishing does NOT activate.** Agents are published as `Inactive`. Tests, preview using `--api-name`, and access by end users continue using the previously active version until you explicitly run `sf agent activate`.

---

## 6. Activate and Deactivate

Activation makes a published agent available for conversations and test execution.

```bash
sf agent activate --json --api-name Bot_API_Name
```

```bash
sf agent deactivate --json --api-name Bot_API_Name
```

- `--api-name` here is the Bot API name (same as the agent's `config.developer_name`).
- Only published agents can be activated. DRAFT-only agents cannot be activated.
- Agent tests require an activated agent.

---

## 7. Retrieve

### Retrieve the authoring bundle (editable source)

```bash
sf project retrieve start --json --metadata AiAuthoringBundle:Agent_API_Name
```

### Retrieve all version-suffixed snapshots (read-only)

```bash
sf project retrieve start --json --metadata "AiAuthoringBundle:Agent_API_Name_*"
```

Wildcard must be quoted. Version-suffixed bundles (e.g., `Local_Info_Agent_v1`) are immutable snapshots of published versions. They are read-only reference copies.

### Retrieve the runtime entity graph

```bash
sf project retrieve start --json --metadata Agent:Agent_API_Name
```

The `Agent:` pseudo-type retrieves the runtime entities (Bot, BotVersion, GenAiPlannerBundle) created by publish. This does NOT include AiAuthoringBundle — use `AiAuthoringBundle:` for that.

#### Caution! Metadata types are NOT sObjects

`GenAiPlannerBundle`, `AiAuthoringBundle`, and `GenAiFunction` are **metadata types**. SOQL queries against them return `INVALID_TYPE`. Always use `sf project retrieve start --metadata` instead.

```bash
# WRONG — these are not sObjects
sf data query --json -q "SELECT Id FROM GenAiPlannerBundle"
sf data query --json -q "SELECT Id FROM AiAuthoringBundle"

# CORRECT — use the Metadata API
sf project retrieve start --json --metadata "GenAiPlannerBundle:AgentName"
sf project retrieve start --json --metadata "AiAuthoringBundle:AgentName"
```

---

## 8. Delete

```bash
sf project delete source --json --metadata AiAuthoringBundle:Agent_API_Name
```

- Deletes the AiAuthoringBundle from the org AND removes local source files.
- Published agents cannot be fully deleted via CLI. The platform returns dependency errors. Use Salesforce Setup UI for published agent deletion.

---

## 9. Preview

Preview runs the agent in a simulated or live environment for testing behavior before publishing.

### Start a preview session

```bash
sf agent preview start --json --authoring-bundle Agent_API_Name
```

Returns a `sessionId` for subsequent send/end commands.

### Send a message

```bash
sf agent preview send --json --authoring-bundle Agent_API_Name --session-id SESSION_ID -u "User message here"
```

- `--session-id`: From the `start` response.
- `-u`: The user utterance (quoted).

### End a preview session

```bash
sf agent preview end --json --authoring-bundle Agent_API_Name --session-id SESSION_ID
```

### Live preview (with real action execution)

```bash
sf agent preview start --json --authoring-bundle Agent_API_Name --use-live-actions
```

Add `--use-live-actions` to execute real backing logic instead of simulated responses. Live preview executes real Apex, Flows, and Prompt Templates in the org.

### Anti-pattern: bare preview command

```bash
# WRONG — interactive REPL, hangs in automation
sf agent preview --authoring-bundle Agent_API_Name

# CORRECT — programmatic start/send/end
sf agent preview start --json --authoring-bundle Agent_API_Name
```

The bare `sf agent preview` command is an interactive REPL designed for humans. It cannot be used programmatically because automation cannot send the ESC key to exit.

### Anti-pattern: context variable injection in preview

`sf agent preview` does NOT support context or session variable injection. There are no `--context`, `--session-var`, or `--variables` flags.

---

## 10. Test

### Create a test from a spec

```bash
sf agent test create --json --spec specs/Agent_API_Name-testSpec.yaml --api-name Test_Definition_Name --force-overwrite
```

- `--spec`: Path to the local YAML test spec file.
- `--api-name`: The name for the AiEvaluationDefinition in the org.
- `--force-overwrite`: Prevents interactive mode if the AiEvaluationDefinition already exists. Always include this flag.
- This command automatically deploys the AiEvaluationDefinition to the org. Use `--preview` to generate locally without deploying.

### Run a test

```bash
sf agent test run --json --api-name Test_Definition_Name --wait 5
```

- `--api-name`: The AiEvaluationDefinition name (set by `--api-name` during `test create`). NOT the Bot name.
- `--wait 5`: Synchronous execution with 5-minute timeout. Without `--wait`, returns a job ID immediately.
- Tests run against activated published agents only.

### Check test results (async fallback)

```bash
sf agent test results --json --job-id JOB_ID
```

Only needed if `--wait` was not used or timed out.

### Generate a test spec from existing metadata

```bash
sf agent generate test-spec --from-definition path/to/AiEvaluationDefinition-meta.xml --output-file specs/Agent_API_Name-testSpec.yaml
```

Reverse-engineers a YAML test spec from an existing AiEvaluationDefinition. Do NOT use `sf agent generate test-spec` without `--from-definition` — the bare command is interactive and cannot be used programmatically.

---

## 11. Open in Browser

These commands open Agentforce Studio in the user's default browser. Do NOT use `--json` with these commands — JSON mode outputs the target URL but does not open the browser.

### View all authoring bundles

```bash
sf org open authoring-bundle
```

### View a specific published agent

```bash
sf org open agent --api-name Bot_API_Name
```

Only works for published agents. DRAFT-only bundles must be opened via `sf org open authoring-bundle`.

---

## 12. Einstein Agent User Setup

**⚠️ This section applies only to `AgentforceServiceAgent`. Employee agents (`AgentforceEmployeeAgent`) must NOT have `default_agent_user` set.**

### Check for an Existing Einstein Agent User

```bash
sf data query --json -q "SELECT Username, Name, IsActive FROM User WHERE Profile.UserLicense.Name = 'Einstein Agent' AND IsActive = true LIMIT 5"
```

If results are returned, confirm the correct username with the human before using it in the agent's config block.

### Check Einstein Agent License Availability

If no users are found, check whether the org has Einstein Agent licenses available:

```bash
sf data query --json -q "SELECT TotalLicenses, UsedLicenses FROM UserLicense WHERE Name = 'Einstein Agent'"
```

If `TotalLicenses` is 0, the org does not have the Einstein Agent add-on. **Stop and inform the human.**

If `TotalLicenses > UsedLicenses`, a license is available and a new Einstein Agent User can be created.

### Creating an Einstein Agent User

#### Step 1: Query for the Einstein Agent User profile ID

```bash
sf data query --json -q "SELECT Id FROM Profile WHERE Name = 'Einstein Agent User'"
```

#### Step 2: Create a User import JSON file (e.g., `data-import/User.json`)

```json
{
    "records": [
        {
            "attributes": {
                "type": "User",
                "referenceId": "AgentUserRef1"
            },
            "ProfileId": "<PROFILE_ID_FROM_STEP_1>",
            "Username": "<UNIQUE_USERNAME>",
            "Alias": "AgntUsr",
            "CommunityNickname": "Agent User<UNIQUE_STRING>",
            "Email": "noreply@example.com",
            "FirstName": "Agent",
            "LastName": "User",
            "IsActive": true,
            "ForecastEnabled": false,
            "EmailEncodingKey": "UTF-8",
            "LanguageLocaleKey": "en_US",
            "LocaleSidKey": "en_US",
            "TimeZoneSidKey": "America/Los_Angeles"
        }
    ]
}
```

#### Step 3: Import the user record

```bash
sf data import tree --json --files data-import/User.json
```

#### Step 4: Verify the user was created

```bash
sf data query --json -q "SELECT Username FROM User WHERE Profile.UserLicense.Name = 'Einstein Agent' AND IsActive = true LIMIT 5"
```

After creating the user, continue with permission setup in [Agent User Setup & Permissions](agent-user-setup.md).

---

## 13. CI/CD Pipeline

The individual commands in this guide compose into a standard deployment pipeline:

1. **Retrieve from Sandbox** — `sf project retrieve start --json --metadata AiAuthoringBundle:AgentName`
2. **Validate Syntax** — `sf agent validate authoring-bundle --json --api-name AgentName`
3. **Run Tests** — `sf agent test run --json --api-name TestDefName --wait 5`
4. **Code Review** — Review `.agent` file changes in version control
5. **Deploy to Production** — `sf project deploy start --json --metadata AiAuthoringBundle:AgentName`
6. **Publish** — `sf agent publish authoring-bundle --json --api-name AgentName`
7. **Activate** — `sf agent activate --json --api-name AgentName`
8. **Verify Active Agent** — `sf agent preview start --json --api-name AgentName`
