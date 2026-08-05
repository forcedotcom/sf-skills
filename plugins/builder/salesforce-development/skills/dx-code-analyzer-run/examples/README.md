# Examples Directory

Sample outputs and command patterns for the dx-code-analyzer-run skill.

## Files

| File | Purpose |
|------|---------|
| [`basic-scan-output.json`](basic-scan-output.json) | Small scan (~127 violations) showing typical structure for personal projects |
| [`large-scan-output.json`](large-scan-output.json) | Large scan (~69k violations) from real NPSP project, demonstrates scale handling |
| [`security-focused-output.json`](security-focused-output.json) | Security-only scan with `all:Security:(1,2)` selector, shows critical issues |
| [`fix-application-before-after.md`](fix-application-before-after.md) | Before/after comparison showing engine-provided fixes in action |
| [`command-variations.md`](command-variations.md) | 20+ real command patterns with explanations and anti-patterns |

## When to Use

### As a User/Developer
- **Validate your scan output** matches expected format
- **See real-world command examples** for common scenarios
- **Understand fix application** before running it on your code

### As the Agent
- **Compare output structure** when parsing scan results
- **Verify fix format** when applying auto-fixes
- **Reference command patterns** when building complex rule selectors
- **Use as templates** when explaining results to users

## Usage from SKILL.md

These files are **reference examples**, not loaded by default. Reference them in specific scenarios:

```markdown
**For large result sets (5000+ violations)**, compare against `examples/large-scan-output.json` to verify your summary format matches the expected structure.

**Before applying fixes**, show the user the before/after comparison from `examples/fix-application-before-after.md` to set expectations.

**For complex command construction**, reference `examples/command-variations.md` to find the pattern that matches the user's intent.
```
