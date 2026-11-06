# Install the same folder in each client

Copy the entire `agentforce-hyperclassifier-optimize` directory, including `scripts`, `references`, and `assets`. Copying only `SKILL.md` is insufficient. No symlink to the source repository is necessary. Python 3.9 or newer must be available as `python3` (or use the equivalent Python launcher on Windows).

For customer-org onboarding, verify `sf --version`. If Salesforce CLI is missing, install it through the customer's approved method using the [official Salesforce CLI installation instructions](https://developer.salesforce.com/docs/platform/salesforce-cli/guide/sfdx_setup_install_cli.html). Direct evaluation with an already configured `--env-file` requires only Python and network access. Onboarding commands and runtime authentication remain independent of the agent host's model-provider configuration.

| Client | Project installation | Personal installation | Invocation |
| --- | --- | --- | --- |
| Claude Code | `.claude/skills/agentforce-hyperclassifier-optimize/` | `~/.claude/skills/agentforce-hyperclassifier-optimize/` | `/agentforce-hyperclassifier-optimize` followed by the task |
| Codex | `.agents/skills/agentforce-hyperclassifier-optimize/` | `~/.agents/skills/agentforce-hyperclassifier-optimize/` | `$agentforce-hyperclassifier-optimize` followed by the task |
| OpenCode | `.opencode/skills/agentforce-hyperclassifier-optimize/` | `~/.config/opencode/skills/agentforce-hyperclassifier-optimize/` | Ask to use `agentforce-hyperclassifier-optimize`; the agent loads it through its skill tool |

Example project installation (run from the project where the skill should be available):

```bash
# Set this to the source folder containing SKILL.md.
SKILL_SOURCE=/path/to/agentforce-hyperclassifier-optimize
mkdir -p .claude/skills
cp -R "$SKILL_SOURCE" .claude/skills/
```

For Codex substitute `.agents/skills`; for OpenCode substitute `.opencode/skills`. Choose one installation per client to avoid duplicate discovery. Back up an existing installation before replacing it. Do not copy credentials or run output into the installation. Start a new client session if it does not discover the skill immediately.

After installation, set `SKILL_DIR` to the installed directory's absolute path and verify without credentials:

```bash
python3 "$SKILL_DIR/scripts/hyperclassifier.py" evaluate \
  --evals "$SKILL_DIR/assets/sample_evals.csv" \
  --descriptions "$SKILL_DIR/assets/sample_descriptions.json" \
  --output-dir ./hc-sample-check --dry-run
```

The same command and files apply in all three hosts. No `$ARGUMENTS`, tool allowlists, injected shell commands, hooks, host-specific subagents, or MCP registration are required.

Discovery references: [Claude Code skills](https://code.claude.com/docs/en/skills), [Codex skills](https://developers.openai.com/codex/skills/), [OpenCode skills](https://opencode.ai/docs/skills/).
