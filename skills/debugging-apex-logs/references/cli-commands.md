<!-- Parent: debugging-apex-logs/SKILL.md -->
# Salesforce CLI Debug Commands Reference

## Quick Reference

| Task | Command |
|------|---------|
| List recent logs | `sf apex list log --target-org my-org` |
| Get specific log | `sf apex get log --log-id 07Lxx0000000000` |
| Stream real-time | `sf apex tail log --target-org my-org` |
| Delete log | `sf data delete record --sobject ApexLog --record-id <id> --target-org my-org` |

---

## Log Retrieval

### List Available Logs

```bash
# List all logs for current user
sf apex list log --target-org my-org

# JSON output for parsing
sf apex list log --target-org my-org --json
```

**Output Fields:**
- `Id` - Log ID for retrieval
- `LogUser.Name` - Who generated the log
- `Operation` - What triggered the log
- `Status` - Success/Failure
- `LogLength` - Size in bytes
- `StartTime` - When it was generated

### Get Specific Log

```bash
# Download log by ID
sf apex get log \
  --log-id 07Lxx0000000000AAA \
  --target-org my-org

# Save to file
sf apex get log \
  --log-id 07Lxx0000000000AAA \
  --target-org my-org \
  --output-dir ./logs

# Get most recent log
sf apex list log --target-org my-org --json | \
  jq -r '.result[0].Id' | \
  xargs -I {} sf apex get log --log-id {} --target-org my-org
```

### Stream Logs Real-Time

```bash
# Tail logs with color highlighting
sf apex tail log --target-org my-org --color

# Tail with color highlighting
sf apex tail log \
  --target-org my-org \
  --color
# Note: Debug levels are configured via TraceFlag records in Setup, not CLI flags

# Tail with skip flag (don't show historical logs)
sf apex tail log --target-org my-org --skip-trace-flag
```

---

## Log Management

### Delete Logs

> **Note**: `sf apex log delete` does not exist in sf CLI v2. Use `sf data delete record` instead.

```bash
# Delete specific log
sf data delete record \
  --sobject ApexLog \
  --record-id 07Lxx0000000000AAA \
  --target-org my-org
```

---

## Debug Level Configuration

### Using Trace Flags

Trace flags control what gets logged and for which users.

```bash
# Create trace flag for specific user
sf data create record \
  --sobject TraceFlag \
  --values "TracedEntityId='005xx0000001234' LogType='USER_DEBUG' DebugLevelId='7dlxx0000000000' StartDate='2025-01-01T00:00:00Z' ExpirationDate='2025-01-02T00:00:00Z'" \
  --target-org my-org

# Query existing trace flags
sf data query \
  --query "SELECT Id, TracedEntityId, DebugLevel.MasterLabel, ExpirationDate FROM TraceFlag" \
  --target-org my-org

# Delete trace flag
sf data delete record \
  --sobject TraceFlag \
  --record-id 7tfxx0000000000AAA \
  --target-org my-org
```

### Debug Levels

```bash
# List available debug levels
sf data query \
  --query "SELECT Id, MasterLabel, ApexCode, ApexProfiling, Callout, Database, System, Workflow FROM DebugLevel" \
  --target-org my-org

# Create custom debug level
sf data create record \
  --sobject DebugLevel \
  --values "MasterLabel='PerformanceDebug' DeveloperName='PerformanceDebug' ApexCode='FINE' ApexProfiling='FINEST' Database='FINE' System='DEBUG'" \
  --target-org my-org
```

---

## Advanced Usage

### Execute Anonymous with Logging

```bash
# Run anonymous Apex and capture log
echo "System.debug('Test'); Account a = [SELECT Id FROM Account LIMIT 1];" | \
  sf apex run --target-org my-org

# Run from file
sf apex run \
  --file ./scripts/debug-script.apex \
  --target-org my-org

# Get the log from that execution
sf apex list log --target-org my-org --json | \
  jq -r '.result[0].Id' | \
  xargs -I {} sf apex get log --log-id {} --target-org my-org
```

### Query Plan Analysis

```bash
# Analyze query plan using Tooling API
sf data query \
  --query "SELECT Id FROM Account WHERE Name = 'Test'" \
  --target-org my-org \
  --use-tooling-api
# Note: --explain does not exist. Use REST API for query plans:
# GET /services/data/v66.0/query/?explain=SELECT+Id+FROM+Account+WHERE+Name='Test'
```

### Log Analysis with grep

```bash
# Find SOQL queries in log
sf apex get log --log-id 07Lxx0000000000 --target-org my-org | \
  rg "SOQL_EXECUTE"

# Count SOQL queries
sf apex get log --log-id 07Lxx0000000000 --target-org my-org | \
  rg -c "SOQL_EXECUTE_BEGIN"

# Find exceptions
sf apex get log --log-id 07Lxx0000000000 --target-org my-org | \
  rg "EXCEPTION_THROWN|FATAL_ERROR"

# Find limit usage
sf apex get log --log-id 07Lxx0000000000 --target-org my-org | \
  rg "LIMIT_USAGE"

# Find slow operations (method timing)
sf apex get log --log-id 07Lxx0000000000 --target-org my-org | \
  rg "METHOD_EXIT.*\|([0-9]{4,})\|"
```

---

## Automation Scripts

### Save and Analyze Latest Log

```bash
#!/bin/bash
# save-latest-log.sh

ORG_ALIAS=${1:-"my-org"}
OUTPUT_DIR=${2:-"./logs"}

mkdir -p $OUTPUT_DIR

# Get latest log ID
LOG_ID=$(sf apex list log --target-org $ORG_ALIAS --json | jq -r '.result[0].Id')

if [ "$LOG_ID" == "null" ]; then
    echo "No logs found"
    exit 1
fi

# Save log
FILENAME="$OUTPUT_DIR/$(date +%Y%m%d_%H%M%S)_$LOG_ID.log"
sf apex get log --log-id $LOG_ID --target-org $ORG_ALIAS > $FILENAME

echo "Log saved to: $FILENAME"

# Quick analysis
echo ""
echo "=== QUICK ANALYSIS ==="
echo "SOQL Queries: $(rg -c 'SOQL_EXECUTE_BEGIN' $FILENAME || echo 0)"
echo "DML Statements: $(rg -c 'DML_BEGIN' $FILENAME || echo 0)"
echo "Exceptions: $(rg -c 'EXCEPTION_THROWN|FATAL_ERROR' $FILENAME || echo 0)"
```

### Monitor for Errors

```bash
#!/bin/bash
# monitor-errors.sh

ORG_ALIAS=${1:-"my-org"}

echo "Monitoring $ORG_ALIAS for errors..."
echo "Press Ctrl+C to stop"

sf apex tail log --target-org $ORG_ALIAS --color 2>&1 | \
  while read line; do
    if echo "$line" | rg -q "EXCEPTION|FATAL_ERROR|LimitException"; then
      echo "🔴 ERROR DETECTED: $line"
      # Optional: Send alert
      # osascript -e 'display notification "Error in Salesforce" with title "debugging-apex-logs"'
    fi
  done
```

### Bulk Log Cleanup

```bash
#!/bin/bash
# cleanup-logs.sh

ORG_ALIAS=${1:-"my-org"}
DAYS_OLD=${2:-7}

echo "Deleting logs older than $DAYS_OLD days from $ORG_ALIAS..."

# Get old log IDs
OLD_LOGS=$(sf data query \
  --query "SELECT Id FROM ApexLog WHERE StartTime < LAST_N_DAYS:$DAYS_OLD" \
  --target-org $ORG_ALIAS \
  --json | jq -r '.result.records[].Id')

COUNT=0
for LOG_ID in $OLD_LOGS; do
    sf data delete record --sobject ApexLog --record-id $LOG_ID --target-org $ORG_ALIAS --json > /dev/null
    ((COUNT++))
done

echo "Deleted $COUNT logs"
```

---

## Troubleshooting

### No Logs Appearing

1. **Check trace flags exist:**
   ```bash
   sf data query \
     --query "SELECT Id, TracedEntityId, ExpirationDate FROM TraceFlag WHERE ExpirationDate > TODAY" \
     --target-org my-org
   ```

2. **Check log retention:**
   ```bash
   sf data query \
     --query "SELECT Id, StartTime FROM ApexLog ORDER BY StartTime DESC LIMIT 5" \
     --target-org my-org
   ```

3. **Verify user has API access:**
   - User must have "API Enabled" permission
   - User must have "Author Apex" for trace flags

### Log Too Large

Logs over 2MB are truncated. Solutions:

1. **Reduce debug level:**
   ```
   ApexCode: DEBUG → INFO
   ApexProfiling: FINEST → FINE
   ```

2. **Focus on specific operation:**
   - Create trace flag just before the operation
   - Delete after capturing

3. **Use targeted logging:**
   - Add `System.debug()` only where needed
   - Use `LoggingLevel.ERROR` for critical info

### Logs Not Persisting

Default log retention is 24 hours. To keep logs longer:

```bash
# Export log to file immediately
sf apex get log --log-id 07Lxx0000000000 --target-org my-org > ./saved-log.txt
```

---

## Integration with debugging-apex-logs Skill

The debugging-apex-logs skill automatically:

1. **Fetches logs** when you run `sf apex get log` or `sf apex tail log`
2. **Parses content** for SOQL in loops, DML in loops, exceptions
3. **Displays analysis** with governor limit usage
4. **Suggests fixes** using sf-apex skill integration

Example workflow:
```bash
# Run a test that generates a log
sf apex run test --class-names MyTestClass --target-org my-org

# Get the log (debugging-apex-logs hook auto-analyzes)
sf apex list log --target-org my-org --json | \
  jq -r '.result[0].Id' | \
  xargs -I {} sf apex get log --log-id {} --target-org my-org
```

The hook will output analysis like:
```
============================================================
🔍 DEBUG LOG ANALYSIS
============================================================

🔴 CRITICAL ISSUES
------------------------------------------------------------
   • SOQL in loop detected: 50 queries executed inside loops
   • CPU limit critical: 9500/10000ms (95.0%)

📊 GOVERNOR LIMIT USAGE
------------------------------------------------------------
   ✅ SOQL Queries: 50/100 (50.0%)
   ✅ DML Statements: 25/150 (16.7%)
   🔴 CPU Time (ms): 9500/10000 (95.0%)

🤖 AGENTIC FIX RECOMMENDATIONS
============================================================

For SOQL in loop:
   1. Move query BEFORE the loop
   2. Store results in Map<Id, SObject>
   3. Access from Map inside loop
```
