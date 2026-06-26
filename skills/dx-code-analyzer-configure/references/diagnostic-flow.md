# Diagnostic Flow: Fix a Broken Setup

**TRIGGER:** User says "not working", "broken", "getting errors", "scan fails", "help me fix", etc.

## NEVER DO THESE (anti-patterns that waste time)

- ❌ NEVER run `which sfdx`, `which sf`, `find`, `ls /opt/homebrew/bin/` or search for binaries
- ❌ NEVER use an old `sfdx` binary as a workaround — it is NOT a substitute for `sf`
- ❌ NEVER create symlinks (`ln -s`) to work around missing commands
- ❌ NEVER check PATH, inspect Cellar directories, or search for alternative installations
- ❌ NEVER proceed to Layer 2 if Layer 1 failed — fix Layer 1 first
- ❌ NEVER give the user a list of manual steps — fix it yourself or give ONE command

## Diagnostic Flow (follow this EXACTLY, no deviation)

Run **ONLY** this one command first:
```bash
sf --version 2>&1
```

**If output contains "command not found":**
→ STOP. Do not run any other commands. Tell user: "sf CLI is not installed. I'll install it now."
→ Ask user for permission, then run: `npm install -g @salesforce/cli`
→ After install, re-run `sf --version 2>&1` to verify. If it works, continue to next layer.

**If sf works**, run ONLY:
```bash
sf plugins --core 2>&1 | grep -i "code-analyzer"
```

**If output is empty or shows "JIT" but not a real version:**
→ STOP. Run: `sf plugins install @salesforce/plugin-code-analyzer`
→ After install, re-check. If it works, continue to next layer.

**If plugin is installed**, check engine deps:
```bash
java -version 2>&1
node --version 2>&1
```

**If all pass**, verify with a scan:
```bash
sf code-analyzer run --rule-selector Recommended 2>&1 | tail -20
```

## Fix Table

| Error Pattern | The ONE Fix |
|--------------|-------------|
| `sf: command not found` | `npm install -g @salesforce/cli` |
| Plugin missing / JIT error | `sf plugins install @salesforce/plugin-code-analyzer` |
| `Cannot find module` | `sf plugins uninstall @salesforce/plugin-code-analyzer && sf plugins install @salesforce/plugin-code-analyzer` |
| `java: command not found` | Install Java 11+ (see `<skill_dir>/references/engine-prerequisites.md`) |
| `OutOfMemoryError` (SFGE) | Add `engines.sfge.java_max_heap_size: "4g"` to `code-analyzer.yml` |
| `YAMLException` | Read the config file, fix YAML syntax |
| `EPERM` / npm permission error | Tell user to run: `sudo chown -R $(whoami) ~/.npm` — then wait for them to confirm, then retry the SAME install command that failed. Do NOT dump next steps. |

## After Fix: Verify and Hand Off

Re-run the check for the fixed layer. Once a scan succeeds, tell the user what was fixed and **proceed to run the full scan**.

## When a fix requires user action (sudo, manual step)

Tell the user ONLY the ONE command they need to run and WHY. Then STOP and WAIT for them to confirm it's done. Do NOT:
- ❌ List the remaining steps ("after that, do X, then Y, then Z")
- ❌ Tell them what to run next after the manual step
- ❌ Provide a multi-step recovery plan
- ❌ Ask "would you like me to attempt with sudo or do it yourself"

Just say: "Run this command: `<command>`. It fixes [reason]. Let me know when it's done and I'll continue."
