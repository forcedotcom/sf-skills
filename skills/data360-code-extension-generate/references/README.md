# data360-code-extension-generate

An agent skill for building Data 360 (Data Cloud) code extensions. Code extensions are custom PySpark transformations and Search Index Chunking functions, developed, tested and deployed with the `sf data-code-extension` CLI plugin and the `salesforce-data-customcode` SDK.

The skill is **agent-agnostic**. It works in any tool that can read a `SKILL.md` and run shell commands, and it has no dependency on a particular LLM or client.

## What it does

0. **Environment check**: runs the read-only `scripts/check_env.sh`, picks a Python mode, and sets up Python 3.11, the SDK, Java and the sf plugin. If `python3` is already 3.11 (typical in cloud workspaces and containers), it installs into that Python with no venv. Otherwise (typical on macOS) it creates a project `.venv`.
1. **Init**: scaffolds a script or function package.
2. **Discover schemas**: fetches the source and target DLO fields and prints a field mapping, before any code is written.
3. **Develop**: writes the PySpark transformation from that mapping.
4. **Scan**: generates `config.json` and `requirements.txt`.
5. **Run**: tests locally against real org data.
6. **Deploy**: deploys to Data 360, with redeploy and cleanup guidance.
7. **Verify**: runs the data transform and checks the output.

## Defaults without prompting

The agent doesn't ask for the project folder or org when the environment already decides them. In **Code Builder**, it uses `/home/codebuilder/dx-project` and the single Connected (default) org, prints them, and continues. Elsewhere it uses the current folder and the CLI default org (if Connected) or the only Connected org. It asks only when several orgs are Connected and none is the default. To pin values without prompting, set `D360_PROJECT_DIR` and `D360_TARGET_ORG`.

## Manual prerequisite (no API)

An org admin must enable **Code Extension** in **Data Cloud Setup → Feature Manager**.

## Install the skill

The skill is a folder with `SKILL.md`, `references/` and `scripts/`. Copy or symlink the whole folder to wherever your agent loads skills from:

| Agent | Typical location |
|---|---|
| Claude Code | `~/.claude/skills/` or `<project>/.claude/skills/` |
| Codex CLI | `~/.codex/skills/` or `<project>/.codex/skills/` |
| Gemini CLI, Cursor, Copilot, others | That tool's skills or rules folder. Otherwise, reference `SKILL.md` from your project's `AGENTS.md` or rules file |

```bash
git clone --depth 1 https://github.com/forcedotcom/sf-skills.git ~/sf-skills
ln -s ~/sf-skills/skills/data360-code-extension-generate <your-agent-skills-dir>/data360-code-extension-generate
```

## Example prompts

```text
Set up my Mac for Data 360 code extension development against org myorg in ~/projects/d360-ext
Create a code extension that uppercases Employee__dll.position__c into Employee_Upper__dll
Scan and run my code extension locally against myorg
Deploy employee_upper to myorg as version 0.0.1
I changed the code. Redeploy employee_upper
```

## Resources

- SF CLI plugin: https://github.com/salesforcecli/plugin-data-code-extension
- Python SDK: https://github.com/forcedotcom/datacloud-customcode-python-sdk (PyPI: `salesforce-data-customcode`)
- Hosted MCP servers: https://developer.salesforce.com/docs/platform/hosted-mcp-servers/overview
