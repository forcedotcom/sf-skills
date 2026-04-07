# Troubleshooting, Best Practices, and Dependencies — Reference

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Session timeout | Long-running tests | Split into smaller batches |
| Trace not found | CLI version issue | Update to sf CLI 2.121.7+ |
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
sf agent preview start --authoring-bundle MyAgent -o myorg --json 2>&1 | tee /tmp/preview_debug.json
```

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
- `sf` CLI 2.121.7+ (for preview trace support)
- `jq` (system) - JSON processing
- `python3` - For result parsing scripts

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | All tests passed | Safe to deploy |
| 1 | Some tests failed | Review failures before deploying |
| 2 | Critical test failure | Block deployment |
| 3 | Test execution error | Fix test infrastructure |
