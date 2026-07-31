# Troubleshooting, Best Practices, and Dependencies — Reference

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Session timeout | Long-running tests | Split into smaller batches |
| Trace not found | CLI version issue | Update to sf CLI 2.131.0+ |
| `Nonexistent flag: --simulate-actions` on `preview start` | CLI older than 2.131.0 (plugin-agent < 1.32.16) | Update the CLI; below 2.131.0 only `--use-live-actions` exists |
| `Nonexistent flag: --no-prompt` on `preview end` | CLI older than 2.135.5 | Drop the flag — it only affects `end --all`, and single-session `end` never prompts |
| Action mock fails | Complex inputs | Use `--use-live-actions` flag |
| Context variables missing | Preview limitation | Use Runtime API for context tests |
| `jq` parse error on preview output | Control characters in CLI output | Use Python `re.sub` + `json.loads` (see below). `tr` via bash pipes is unreliable -- control chars survive `echo "$VAR"` expansion. |

### Defensive JSON Parsing

`sf agent preview` output may contain control characters (e.g. `\x08`, `\x1b`) that break `jq` and `json.loads`. Always sanitize before parsing.

**Use Python `re.sub`** -- this is the only reliable approach. The `tr` command via `echo "$VAR" | tr -d ...` is unreliable because bash variable expansion and `echo` can re-introduce or mangle control characters:

```bash
# Recommended: Python re.sub (handles all control characters reliably)
python3 -c "
import json, sys, re
raw = sys.stdin.read()
clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
data = json.loads(clean)
print(json.dumps(data.get('result', {}), indent=2))
" <<< "$RESPONSE"
```

## Debug Mode

Enable detailed logging for preview sessions:

```bash
# Enable SF CLI debug output
export SF_LOG_LEVEL=debug

# Run preview with verbose output (--authoring-bundle for local traces)
sf agent preview start --authoring-bundle MyAgent --simulate-actions -o myorg --json 2>&1 | tee /tmp/preview_debug.json
```

### `MissingModeFlag` on `preview start`

`When using --authoring-bundle, you must specify either --use-live-actions or --simulate-actions.` Add `--simulate-actions` (or `--use-live-actions` if you want real Apex/Flow execution) to `start`. Do **not** add it to `send` or `end` — they reject it with `Nonexistent flag`.

### `RequiresProjectError` on any `preview` subcommand

`This command is required to run from within a Salesforce project directory.` Run the command from the directory containing `sfdx-project.json`.

## Best Practices

### Test Strategy

1. **Start with smoke tests** - Basic happy path scenarios
2. **Add edge cases** - Boundary conditions, invalid inputs
3. **Test transitions** - Multi-turn conversations
4. **Verify guardrails** - Off-topic and safety boundaries
5. **Performance baseline** - Establish acceptable response times

### Test Maintenance

- Version test cases with agent versions
- Update expected outputs when agent evolves
- Archive historical test results
- Monitor test flakiness and address root causes

## Dependencies

This skill uses `sf` CLI commands directly. Required tools:
- `sf` CLI **2.131.0+** (plugin-agent 1.32.16+) — the floor for `preview start --authoring-bundle --simulate-actions`, which every example here uses. `start`/`send`/`end` as separate subcommands need 1.28.0; `--simulate-actions` needs 1.32.16 = CLI 2.131.0.
- `jq` (system) - JSON processing
- `python3` - For result parsing scripts

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | All tests passed | Safe to deploy |
| 1 | Some tests failed | Review failures before deploying |
| 2 | Critical test failure | Block deployment |
| 3 | Test execution error | Fix test infrastructure |
