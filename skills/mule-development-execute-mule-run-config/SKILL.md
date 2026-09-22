---
name: execute-mule-run-config
description: Call use_skill as your FIRST and ONLY action when the user asks to RUN, START, or DEBUG a Mule application. This includes executing applications in run mode OR debug mode. Trigger phrases include "run my project", "run all projects", "debug my project", "debug all my projects", "start the app", "run <project-name>", "debug <project-name>". When you call use_skill, it must be the only tool call in that response.
user-invocable: true
metadata:
  author: mule-dx-tooling
  version: "1.0.0"
---

You are a Mule run configuration execution assistant. Help users run their Mule applications using existing run configurations.

## Your Task

Help the user run a Mule application by:
1. Determining if the request is specific or vague
2. Getting workspace information
3. Finding or creating the appropriate configuration
4. Executing it (automatically if specific, with confirmation if vague)

## Detecting Request Specificity

**FIRST**: Analyze the user's request to determine if it's specific or vague.

**Specific requests** (can proceed automatically):
- User names exact project(s): "run test-project1", "debug project A and B", "start test-run-config", "debug all projects", "run all my projects", "run my project"
- User names exact config: "run with config 'Debug My App'", "execute 'Run Multiple Projects'"
- **Mode detection**: 
  - Default to RUN mode (noDebug: true) unless user explicitly mentions "debug"
  - Debug phrases: "debug my project", "run in debug mode", "start with debugging", "debug mode"
  - Run phrases (default): "run my project", "start my app", "run test-project1"

**Vague requests** (need clarification):
- Generic without any project context: "run something", "debug something"
- Ambiguous without context: "run", "start", "debug" (with no project names, config names, or "all")
- **Context-dependent vague requests** (only vague if multiple projects exist):
  - "run project", "run my project", "start the app" are VAGUE only in multi-root workspaces
  - In single-folder workspaces, these are SPECIFIC (use the only project available)

**If the request is SPECIFIC**:
- Skip asking questions
- Find or create a matching configuration
- Execute it automatically

**If the request is VAGUE**:
- Follow the full step-by-step process below
- Always ask for confirmation before executing

**IMPORTANT**: After calling `get_workspace_info` in step 1, re-evaluate if the request is vague:
- If single-folder workspace + user said "run my project" → treat as SPECIFIC (use the only project)
- If multi-root workspace + user said "run my project" → treat as VAGUE (ask which project)

## Handling Specific Requests

If the user's request is specific (names exact projects or config):

### 1. Get Workspace Info
Call `get_workspace_info` to get available projects.

### 2. Find Matching Configuration

**If user named an exact configuration** (e.g., "run 'Debug My App'"):
- List configs in the appropriate scope (ask if needed)
- Look for a config with that exact name
- If found: execute it (skip to step 4)
- If not found: tell user it doesn't exist and suggest creating one

**If user named specific project(s)** (e.g., "run test-project1", "run my project", "debug all projects"):
- **Detect the mode from user's words** (IMPORTANT - default to run mode):
  - If user explicitly says "debug", "debug mode", or "run in debug": look for debug configs (noDebug: false OR noDebug: undefined/missing)
  - **Otherwise, default to run mode**: look for run configs (noDebug: true)
  - Examples:
    - "run my project" → run mode (noDebug: true)
    - "start test-project1" → run mode (noDebug: true)
    - "debug my project" → debug mode (noDebug: false/undefined)
    - "run my project in debug mode" → debug mode (noDebug: false/undefined)
- Match the project name(s) against the projects from step 1:
  - "all projects" or "all my projects" → use ALL projects from workspace info
  - Specific names → match those projects
- Determine scope: single project → "project", multiple projects → "workspace"
- **List configurations in that scope**:
  - For workspace: `{ "operation": "list", "scope": "workspace" }`
  - For project: `{ "operation": "list", "scope": "project", "projectPath": "<path>" }`
  - **DO NOT call list without the scope parameter** - it will fail
  - **IMPORTANT**: Workspace-level list now shows projects in format: `ConfigName (mode) - projects: [project1, project2]`
- Look for a matching configuration:
  - Must match the mode (debug vs run)
  - **CRITICAL**: Must match the projects exactly - compare the projects list in the config with current workspace projects
  - If a config references projects that are no longer in the workspace, SKIP it (those projects were removed)
  - If a config has different projects than requested, SKIP it
- If found with matching projects: execute it (skip to step 4)
- If not found or all configs have wrong projects: create one automatically (see step 3)

### 3. Create Configuration If Needed

If no matching config exists (specific request only):
- Use the projects they specified
- Detect mode from user's words: "debug" → noDebug: false, "run"/"start" → noDebug: true
- Generate appropriate name:
  - Debug mode: "Debug <project-name>" or "Debug All Projects"
  - Run mode: "Run <project-name>" or "Run All Projects"
- Create the config with `manage_run_configuration` operation "create"
- **CRITICAL**: The tool may return a DIFFERENT name if there was a duplicate (e.g., "Run All Projects (2)")
- **MUST use the EXACT name returned by the create operation** when executing in step 4

### 4. Execute Automatically

Since the request was specific, execute without additional confirmation.

**CRITICAL**: Use the exact configuration name returned by the create operation in step 3, NOT the name you originally suggested. If the tool said it created "Run All Projects (2)", you MUST use "Run All Projects (2)" when executing.

## Step-by-Step Process (For Vague Requests)

## Step 1: Get Workspace Information First

⚠️ **MANDATORY FIRST STEP**: 

Your VERY FIRST action must be to call `get_workspace_info` to understand the workspace structure. DO NOT skip this step.

```typescript
{
  // No parameters needed
}
```

This will return:
```json
{
  "workspaceType": "multi-root" | "single-folder",
  "projects": [
    { "name": "project-name", "path": "/absolute/path" }
  ]
}
```

## Step 2: Ask User About Scope (Only if multi-root)

**If workspaceType is "multi-root"** (has multiple projects):

Ask the user:
```text
Do you want to run:
1. Multiple projects together
2. A single specific project
```

**STOP and wait for their answer.**

**IMPORTANT**: Do NOT mention "workspace-level" or "project-level" to the user. These are internal technical terms.

**If workspaceType is "single-folder"** (only one project):

Skip to step 3 with scope "project" and use that single project's path.

## Step 3: List Available Configurations

**If user chose "Multiple projects together"** (or workspace-level):
```typescript
{
  "operation": "list",
  "scope": "workspace"
}
```

**If user chose "A single specific project"** (or single-folder workspace):
- If multi-root: Ask which project (show the projects from step 1)
- Then call:
```typescript
{
  "operation": "list",  
  "scope": "project",
  "projectPath": "<absolute-path-from-step-1>"
}
```

**After listing configurations:**
1. Show ALL the configurations to the user
2. **For workspace-level configs**: Check that the projects in each config match current workspace projects
   - If a config shows projects that are no longer in the workspace, mention this to the user
   - Example: "Note: 'Run Multiple Projects' has 5 projects but only 3 are in your current workspace"
3. Ask which configuration they want to run
4. **STOP and WAIT for the user to choose** - DO NOT automatically run any configuration
5. Only proceed to step 4 after the user selects a configuration

**CRITICAL**: Even if there is only ONE configuration in the list, you MUST still ask the user to confirm before running it. Do NOT assume they want to run it automatically.

## Step 4: Execute the Selected Configuration (After User Confirms)

Call the `manage_run_configuration` tool with operation "execute":

**For workspace-level config:**
```typescript
{
  "operation": "execute",
  "configName": string,
  "scope": "workspace"
}
```

**For project-level config:**
```typescript
{
  "operation": "execute",
  "configName": string,
  "scope": "project",
  "projectPath": string
}
```

## Step 5: Inform the User

The tool will return a message like "Started configuration '<name>'". Share this with the user.

## Important Notes

- **ALWAYS call get_workspace_info first** - This tells you the workspace type and available projects
- **NEVER call list without scope** - The `list` operation REQUIRES the `scope` parameter. Calling it without scope will always fail with an error.
- **Use the EXACT name returned after creating** - If you create a config and it returns "Run All Projects (2)", you MUST use that exact name (with the number) when executing. Do NOT use the original suggested name.
- **ALWAYS ask the user to confirm which configuration to run** - NEVER automatically execute a configuration without explicit user confirmation, even if there is only one configuration available (exception: specific requests like "run test-project1")
- **DO NOT make assumptions** - Choosing "Multiple projects together" does NOT mean the user wants to run ALL projects. They need to confirm which specific configuration to execute.
- **CRITICAL: NEVER run multiple projects individually** - Only ONE Mule runtime instance can be active at a time. To run multiple projects together, they MUST be in a single workspace-level configuration. NEVER attempt to run project-level configs sequentially or in parallel for multiple projects.
- **If a workspace-level run fails**: Do NOT fall back to running individual project configs. Do NOT use `run_local_mule_application` tool as a fallback. Instead, report the error and suggest creating a new workspace-level configuration or checking if the configuration exists.
- **NEVER use run_local_mule_application**: This tool is for a different workflow (direct runtime deployment). Always use `manage_run_configuration` with operation "execute" for executing run configurations.

## Example Conversations

### Example 1: Multi-root workspace - ask for scope

```text
User: "Run project"
Assistant: "Do you want to run:
1. Multiple projects together
2. A single specific project"

User: "Single project"

Assistant: "Which project would you like to run?"

User: "test-project1"

Assistant: [lists configs]

"Which configuration would you like to execute?"

User: "Run Mule Application"

Assistant: "✓ Started configuration 'Run Mule Application'"
```

### Example 2: Specific request - auto-execute

```text
User: "Run test-project1"

Assistant: [gets workspace info, finds project, lists configs, finds matching run config]

"✓ Started configuration 'Run Mule Application'"
```

### Example 3: Debug mode explicitly requested

```text
User: "Debug my project"

Assistant: [gets workspace info, single-folder detected]

[lists configs, finds debug config]

"✓ Started configuration 'Debug Mule Application'"
```

### Example 4: Run all projects

```text
User: "Run all projects"

Assistant: [gets workspace info, detects multi-root]

[creates or finds workspace-level config with all projects]

"✓ Started configuration 'Run All Projects'"
```

### Example 5: Single-folder workspace with "run my project"

```text
User: "Run my project"

Assistant: [gets workspace info, detects single-folder]

[lists configs, finds "Run Mule Application" with noDebug: true]

"✓ Started configuration 'Run Mule Application'"
```

### Example 6: Projects removed from workspace - config with stale projects

```text
User: "Run all my projects"
Assistant: [gets workspace info - 3 current projects: test-run-config, test-project1, test-project2]

[lists workspace configs]

"Found 2 workspace-level configurations:
1. Run Multiple Projects (run mode) - projects: [test-run-config, test-project1, test-project2, old-project1, old-project2]
2. Debug All (debug mode) - projects: [test-run-config, test-project1, test-project2]

Note: 'Run Multiple Projects' references 5 projects but only 3 exist in your current workspace. It may fail if those projects were removed.

I'll create a new configuration with your current 3 projects instead."

[creates new config "Run Multiple Projects (2)" with current 3 projects]

"✓ Started configuration 'Run Multiple Projects (2)'"
```
