# Quick Start: Minimum Viable Commands

If you're unsure about anything, use these EXACT commands as starting points.

**IMPORTANT:** Always generate a timestamp variable FIRST, then use it in the output filename:
```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
```

Then use it:
```bash
# Simplest scan (entire workspace, recommended rules)
sf code-analyzer run --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes

# Scan specific target
sf code-analyzer run --target "force-app/main/default" --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes

# Scan for security
sf code-analyzer run --rule-selector Security --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes

# Scan specific engine
sf code-analyzer run --rule-selector pmd --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes

# Scan with HTML report (only if user explicitly asks for HTML)
sf code-analyzer run --output-file "./code-analyzer-results-${TIMESTAMP}.html" --include-fixes
```

**After the command completes**, read the output file and present a summary to the user.
