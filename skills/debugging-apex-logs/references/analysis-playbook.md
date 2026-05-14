# Debug Analysis Playbook

Use this playbook when `debugging-apex-logs` is active and you need the expanded workflow.

## 1. Gather context

Collect:
- org alias
- failing transaction or test context
- approximate time window
- relevant user / record / request identifiers

## 2. Retrieve logs

Preferred commands:

```bash
sf apex list log --target-org <alias> --json
sf apex get log --log-id <id> --target-org <alias>
sf apex tail log --target-org <alias> --color
```

See [cli-commands.md](cli-commands.md) for more options.

## 3. Analyze in this order

1. transaction entry point
2. exceptions and fatal errors
3. governor limits
4. SOQL / DML repetition patterns
5. CPU / heap hotspots
6. callout timing and external failures

## 4. Classify severity

- **Critical** — runtime failure, hard limit, data corruption risk
- **Warning** — near-limit, non-selective query, slow path
- **Info** — optimization opportunity, cleanup item, observability gap

## 5. Propose fixes

Prefer fixes that are:
- root-cause oriented
- bulk-safe
- testable
- deployable in one clean change set

## 6. Loop with adjacent skills

- use `sf-apex` for code fixes
- use `running-apex-tests` to reproduce and verify
- use `deploying-sf-metadata` to deploy fixes
- use `handling-sf-data` when the issue depends on missing or malformed test data
