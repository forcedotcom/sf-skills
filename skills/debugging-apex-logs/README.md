# debugging-apex-logs

Salesforce debugging and troubleshooting skill with log analysis, governor limit detection, and agentic fix suggestions. Identify performance bottlenecks and automatically suggest fixes.

## Features

- **Log Analysis**: Parse and analyze Apex debug logs
- **Governor Limit Detection**: SOQL, DML, CPU, and heap limit monitoring
- **Performance Analysis**: Find slow queries and expensive operations
- **Stack Trace Interpretation**: Parse exceptions and identify root causes
- **Agentic Fix Suggestions**: Automatically suggest code fixes
- **100-Point Scoring**: Issue severity classification


## Quick Start

### 1. Invoke the skill

```
Skill: debugging-apex-logs
Request: "Analyze debug logs for AccountTrigger performance issues in org dev"
```

### 2. Common operations

| Operation | Example Request |
|-----------|-----------------|
| Analyze log | "Analyze the latest debug log for errors" |
| List logs | "Show recent debug logs for org dev" |
| Tail logs | "Tail logs for user admin@company.com" |
| Find limits | "Find governor limit issues in the log" |
| Query plan | "Analyze query plan for Account SOQL" |

## Log Commands

```bash
# List recent logs
sf apex list log --target-org [alias] --json

# Get specific log
sf apex get log --log-id 07Lxx0000000000 --target-org [alias]

# Tail logs real-time
sf apex tail log --target-org [alias] --color
```

## Scoring System (100 Points)

| Category | Points | Focus |
|----------|--------|-------|
| Governor Limits | 25 | SOQL, DML, CPU, Heap analysis |
| Performance | 25 | Query optimization, N+1 detection |
| Error Analysis | 20 | Exception handling, stack traces |
| Root Cause | 20 | Issue identification, fix suggestions |
| Documentation | 10 | Clear explanations, actionable fixes |

## Cross-Skill Integration

| Related Skill | When to Use |
|---------------|-------------|
| sf-apex | Fix identified Apex issues |
| querying-soql | Optimize slow SOQL queries |
| running-apex-tests | Re-run tests after fixes |

## Documentation

- [Benchmarking Guide](references/benchmarking-guide.md)


## Requirements

- sf CLI v2
- Target Salesforce org
- Debug logs enabled for target user

## License

MIT License. See LICENSE file.
Copyright (c) 2024-2025 Salesforce
