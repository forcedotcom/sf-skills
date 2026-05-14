<!-- Parent: debugging-apex-logs/SKILL.md -->
# Log Analysis Tools

This guide covers tools for analyzing Salesforce debug logs, with a focus on performance profiling and bottleneck identification.

---

## Recommended: Apex Log Analyzer (VS Code)

The **Apex Log Analyzer** is a free VS Code extension that provides visual analysis of Apex debug logs.

### Installation

```
1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X / Cmd+Shift+X)
3. Search "Apex Log Analyzer"
4. Install "Apex Log Analyzer" by FinancialForce
```

Or install via command line:
```bash
code --install-extension FinancialForce.lana
```

### Key Features

| Feature | Description | Use Case |
|---------|-------------|----------|
| **Flame Charts** | Visual execution timeline | Find slow methods at a glance |
| **Call Tree** | Hierarchical method calls | Trace execution paths |
| **Database Analysis** | SOQL/DML highlighting | Find query hotspots |
| **Timeline View** | Execution over time | See parallel operations |
| **Limit Summary** | Governor limit usage | Quick health check |

### How to Use

1. **Get a debug log**:
   ```bash
   sf apex get log --log-id 07Lxx0000000000 --target-org my-sandbox -o debug.log
   ```

2. **Open in VS Code**:
   - Open the `.log` file
   - Click "Analyze Log" button in the editor toolbar
   - Or use Command Palette: "Apex Log: Analyze Log"

3. **Navigate the visualization**:
   - **Flame Chart**: Wider bars = more time spent
   - **Click methods** to see details
   - **Hover** for exact timing
   - **Filter** to focus on specific operations

### Reading Flame Charts

```
┌─────────────────────────────────────────────────────────────┐
│ FLAME CHART INTERPRETATION                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ████████████████████████████████████  AccountTrigger       │
│    ██████████████████  AccountService.processAccounts       │
│      ██████████  ← BOTTLENECK: Wide bar = slow operation    │
│        ████  SOQL query                                      │
│      ████████████  Another slow method                       │
│                                                              │
│  Time flows left → right                                     │
│  Width = execution time                                      │
│  Stack depth = call hierarchy                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Bottleneck Indicators**:
- Wide bars at lower levels (deep in call stack)
- Multiple identical bars (repeated operations)
- SOQL/DML bars inside loop patterns

---

## SF CLI Debug Commands

### List Available Logs

```bash
# List recent logs
sf apex list log --target-org my-sandbox --json

# Output includes:
# - Log ID
# - Start time
# - Operation type
# - User
# - Size
```

### Download Logs

```bash
# Download specific log
sf apex get log --log-id 07Lxx0000000000 --target-org my-sandbox

# Save to file
sf apex get log --log-id 07Lxx0000000000 --target-org my-sandbox > debug.log

# Download with number
sf apex get log --number 1 --target-org my-sandbox  # Most recent
```

### Real-Time Log Streaming

```bash
# Tail logs in real-time (like `tail -f`)
sf apex tail log --target-org my-sandbox

# With color highlighting
sf apex tail log --target-org my-sandbox --color

# Use an existing debug level when setting the trace flag
sf apex tail log --target-org my-sandbox --debug-level MyDebugLevel

# Skip trace flag setup when a trace flag is already configured
sf apex tail log --target-org my-sandbox --skip-trace-flag
```

### Set Debug Level

```bash
# Create trace flag via SFDX
sf data create record \
  --sobject TraceFlag \
  --values "TracedEntityId='005xx...' LogType='USER_DEBUG' StartDate='2024-01-01T00:00:00' ExpirationDate='2024-01-02T00:00:00'" \
  --target-org my-sandbox
```

---

## Manual Log Analysis (grep/ripgrep)

When you need quick analysis without visual tools:

### Find All SOQL Queries

```bash
# Count SOQL queries
rg "SOQL_EXECUTE_BEGIN" debug.log | wc -l

# See query text
rg "SOQL_EXECUTE_BEGIN" debug.log

# Find SOQL in loops (query appears multiple times on same line)
rg "SOQL_EXECUTE_BEGIN" debug.log | sort | uniq -c | sort -rn | head -10
```

### Find Large Result Sets

```bash
# Find queries returning many rows
rg "SOQL_EXECUTE_END.*\[\d{4,} rows\]" debug.log
```

### Check Governor Limits

```bash
# Find limit snapshots
rg "LIMIT_USAGE" debug.log | tail -20

# Find approaching limits (>80%)
rg "CPU_TIME" debug.log | tail -5
rg "HEAP_SIZE" debug.log | tail -5
```

### Find Exceptions

```bash
# Find all exceptions
rg "EXCEPTION_THROWN|FATAL_ERROR" debug.log

# Get stack traces
rg -A 10 "FATAL_ERROR" debug.log
```

### Find Slow Operations

```bash
# Extract all timing info
rg "\[\d+\]ms" debug.log | sort -t'[' -k2 -rn | head -20
```

---

## Developer Console Analysis

For quick checks directly in Salesforce:

### Query Plan Tool

1. Open Developer Console
2. Query Editor tab
3. Click "Query Plan" checkbox
4. Run your query
5. Review selectivity and cost

### Log Inspector

1. Open Developer Console
2. Debug → Open Execute Anonymous Window
3. Run code to generate log
4. Select log in "Logs" tab
5. Debug → View Log Panels

**Useful Panels**:
- **Execution Overview**: Summary of operations
- **Timeline**: Visual execution flow
- **Stack Tree**: Call hierarchy
- **Database**: SOQL/DML details

---

## Quick Reference: What to Look For

| Problem | What to Search | Pattern |
|---------|----------------|---------|
| SOQL in Loop | `SOQL_EXECUTE_BEGIN` | Same query repeated many times |
| DML in Loop | `DML_BEGIN` | Same DML repeated many times |
| Slow Query | `SOQL_EXECUTE_END` | Large row count |
| CPU Issue | `CPU_TIME` | Approaching 10,000ms |
| Heap Issue | `HEAP_SIZE` | Approaching 6,000,000 |
| Exception | `EXCEPTION_THROWN` | Stack trace |

---

## Comparison: Analysis Tools

| Tool | Pros | Cons | Best For |
|------|------|------|----------|
| **Apex Log Analyzer** | Visual, free, flame charts | Requires VS Code | Deep performance analysis |
| **Developer Console** | Built-in, no install | Limited visualization | Quick checks |
| **SF CLI + grep** | Scriptable, fast | No visualization | CI/CD, automation |
| **Salesforce Inspector** | Browser-based | Limited log analysis | Quick org exploration |

---

## Related Resources

- [debug-log-reference.md](./debug-log-reference.md) - Log event types
- [benchmarking-guide.md](./benchmarking-guide.md) - Performance testing
- [cli-commands.md](./cli-commands.md) - SF CLI reference
