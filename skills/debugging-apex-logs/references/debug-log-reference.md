<!-- Parent: debugging-apex-logs/SKILL.md -->
# Salesforce Debug Log Reference

## Log Structure

Debug logs follow a consistent format:
```
TIMESTAMP|EVENT_IDENTIFIER|[PARAMS]|DETAILS
```

Example:
```
14:32:54.123 (123456789)|SOQL_EXECUTE_BEGIN|[45]|SELECT Id FROM Account
```

---

## Event Categories

### Execution Events

| Event | Description | Analysis Notes |
|-------|-------------|----------------|
| `EXECUTION_STARTED` | Transaction begins | Identifies transaction type |
| `EXECUTION_FINISHED` | Transaction ends | Total execution time |
| `CODE_UNIT_STARTED` | Method/trigger entry | Call stack tracing |
| `CODE_UNIT_FINISHED` | Method/trigger exit | Method duration |

### SOQL Events

| Event | Description | Key Fields |
|-------|-------------|------------|
| `SOQL_EXECUTE_BEGIN` | Query starts | Line number, Query text |
| `SOQL_EXECUTE_END` | Query ends | Rows returned |

**Analysis Pattern:**
```
|SOQL_EXECUTE_BEGIN|[45]|SELECT Id, Name FROM Account WHERE...
|SOQL_EXECUTE_END|[3 rows]
```
- Line 45 in source code
- Query returned 3 rows

**Warning Signs:**
- Same query appearing multiple times → SOQL in loop
- `[100000 rows]` → Non-selective query
- Query without WHERE clause → Full table scan

### DML Events

| Event | Description | Key Fields |
|-------|-------------|------------|
| `DML_BEGIN` | DML starts | Line number, Operation type, Object |
| `DML_END` | DML ends | Rows affected |

**Analysis Pattern:**
```
|DML_BEGIN|[78]|Op:Insert|Type:Contact|
|DML_END|[200 rows]
```
- Line 78: INSERT operation
- 200 Contact records inserted

**Warning Signs:**
- Same DML operation appearing multiple times → DML in loop
- DML after each SOQL → Likely unbulkified code

### Limit Events

| Event | Description | Format |
|-------|-------------|--------|
| `LIMIT_USAGE` | Current limit usage | `LIMIT_NAME|used|max` |
| `LIMIT_USAGE_FOR_NS` | Per-namespace limits | `LIMIT_NAME|used|max|namespace` |
| `CUMULATIVE_LIMIT_USAGE` | End of transaction | Summary of all limits |

**Example:**
```
|LIMIT_USAGE|SOQL_QUERIES|25|100
|LIMIT_USAGE|DML_STATEMENTS|45|150
|LIMIT_USAGE|CPU_TIME|3500|10000
|LIMIT_USAGE|HEAP_SIZE|2500000|6000000
```

### Exception Events

| Event | Description | Format |
|-------|-------------|--------|
| `EXCEPTION_THROWN` | Exception occurs | `[line]|ExceptionType|Message` |
| `FATAL_ERROR` | Unhandled exception | Full stack trace |

**Analysis Pattern:**
```
|EXCEPTION_THROWN|[67]|System.NullPointerException|Attempt to de-reference a null object
|FATAL_ERROR|System.NullPointerException: Attempt to de-reference a null object
  Class.ContactService.processContacts: line 67, column 1
  Class.AccountTriggerHandler.afterUpdate: line 34, column 1
  Trigger.AccountTrigger: line 5, column 1
```

### Method Events

| Event | Description | Use Case |
|-------|-------------|----------|
| `METHOD_ENTRY` | Method called | Call hierarchy |
| `METHOD_EXIT` | Method returns | Method duration |
| `CONSTRUCTOR_ENTRY` | Constructor called | Object creation |
| `CONSTRUCTOR_EXIT` | Constructor returns | |

### Loop Events

| Event | Description | Important For |
|-------|-------------|---------------|
| `LOOP_BEGIN` | Loop starts | SOQL/DML in loop detection |
| `LOOP_END` | Loop ends | |
| `ITERATION_BEGIN` | Loop iteration | Iteration count |
| `ITERATION_END` | Iteration ends | |

**Detection Pattern for SOQL in Loop:**
```
|LOOP_BEGIN|
  |ITERATION_BEGIN|
    |SOQL_EXECUTE_BEGIN|[45]|SELECT...
    |SOQL_EXECUTE_END|[1 rows]
  |ITERATION_END|
  |ITERATION_BEGIN|
    |SOQL_EXECUTE_BEGIN|[45]|SELECT...  ← Same query repeating!
    |SOQL_EXECUTE_END|[1 rows]
  |ITERATION_END|
|LOOP_END|
```

### Callout Events

| Event | Description | Key Fields |
|-------|-------------|------------|
| `CALLOUT_EXTERNAL_ENTRY` | HTTP callout starts | Endpoint URL |
| `CALLOUT_EXTERNAL_EXIT` | HTTP callout ends | Status code, Duration |

**Example:**
```
|CALLOUT_EXTERNAL_ENTRY|[89]|https://api.example.com/endpoint
|CALLOUT_EXTERNAL_EXIT|[200]|[1500ms]
```

### Heap Events

| Event | Description | Importance |
|-------|-------------|------------|
| `HEAP_ALLOCATE` | Heap allocation | Track large allocations |
| `HEAP_DEALLOCATE` | Heap freed | Garbage collection |

---

## Log Levels

### Categories and Levels

| Category | What It Controls |
|----------|------------------|
| Database | SOQL, SOSL, DML |
| Workflow | Workflow rules, Process Builder |
| Validation | Validation rules |
| Callout | HTTP callouts |
| Apex Code | Apex execution |
| Apex Profiling | Method timing |
| Visualforce | VF page execution |
| System | System operations |

### Level Values

| Level | Amount of Detail | Use Case |
|-------|------------------|----------|
| NONE | Nothing | Disable category |
| ERROR | Errors only | Production monitoring |
| WARN | Warnings + errors | |
| INFO | General info | Default |
| DEBUG | Detailed debug | Development |
| FINE | Very detailed | Deep debugging |
| FINER | Method entry/exit | Performance analysis |
| FINEST | Everything | Complete trace |

### Recommended Debug Level Settings

**For Performance Issues:**
```
Apex Code: FINE
Apex Profiling: FINEST
Database: FINE
System: DEBUG
```

**For Exception Debugging:**
```
Apex Code: DEBUG
Apex Profiling: FINE
Database: INFO
System: DEBUG
```

**For Callout Issues:**
```
Apex Code: DEBUG
Callout: FINEST
System: DEBUG
```

---

## Governor Limits Reference

### Synchronous Limits

| Limit | Value | Log Event |
|-------|-------|-----------|
| SOQL Queries | 100 | `SOQL_QUERIES` |
| SOQL Rows | 50,000 | `SOQL_ROWS` |
| DML Statements | 150 | `DML_STATEMENTS` |
| DML Rows | 10,000 | `DML_ROWS` |
| CPU Time | 10,000 ms | `CPU_TIME` |
| Heap Size | 6 MB | `HEAP_SIZE` |
| Callouts | 100 | `CALLOUTS` |
| Future Calls | 50 | `FUTURE_CALLS` |

### Asynchronous Limits

| Limit | Value | Applies To |
|-------|-------|------------|
| CPU Time | 60,000 ms | @future, Batch, Queueable |
| Heap Size | 12 MB | @future, Batch, Queueable |

### Warning Thresholds

| Limit | Warning (80%) | Critical (95%) |
|-------|---------------|----------------|
| SOQL Queries | 80 | 95 |
| DML Statements | 120 | 143 |
| CPU Time | 8,000 ms | 9,500 ms |
| Heap Size | 4.8 MB | 5.7 MB |

---

## Common Log Patterns

### Pattern 1: SOQL in Loop

```
|LOOP_BEGIN|
|ITERATION_BEGIN|
|SOQL_EXECUTE_BEGIN|[45]|SELECT Id FROM Contact WHERE AccountId = '001xxx'
|SOQL_EXECUTE_END|[1 rows]
|ITERATION_END|
|ITERATION_BEGIN|
|SOQL_EXECUTE_BEGIN|[45]|SELECT Id FROM Contact WHERE AccountId = '001yyy'
|SOQL_EXECUTE_END|[1 rows]
|ITERATION_END|
... (repeats 100 times)
|LIMIT_USAGE|SOQL_QUERIES|100|100  ← LIMIT HIT!
|FATAL_ERROR|System.LimitException: Too many SOQL queries: 101
```

### Pattern 2: DML in Loop

```
|LOOP_BEGIN|
|ITERATION_BEGIN|
|DML_BEGIN|[78]|Op:Insert|Type:Contact|
|DML_END|[1 rows]
|ITERATION_END|
... (repeats 150 times)
|LIMIT_USAGE|DML_STATEMENTS|150|150  ← LIMIT HIT!
|FATAL_ERROR|System.LimitException: Too many DML statements: 151
```

### Pattern 3: Non-Selective Query

```
|SOQL_EXECUTE_BEGIN|[23]|SELECT Id FROM Lead WHERE Status = 'Open'
|SOQL_EXECUTE_END|[250000 rows]  ← Large result set!
```

### Pattern 4: CPU Limit Approaching

```
|CUMULATIVE_LIMIT_USAGE|
|CPU_TIME|9500|10000  ← 95% used!
```

### Pattern 5: Null Pointer Exception

```
|SOQL_EXECUTE_BEGIN|[45]|SELECT Id FROM Account WHERE Id = '001xxx'
|SOQL_EXECUTE_END|[0 rows]  ← No results!
|METHOD_EXIT|getAccount|
|EXCEPTION_THROWN|[47]|System.NullPointerException|Attempt to de-reference a null object
```

---

## Log Analysis Checklist

### Quick Scan

1. **Search for `FATAL_ERROR`** - Find the exception
2. **Search for `LIMIT_USAGE`** - Check governor limits
3. **Search for `SOQL_EXECUTE_BEGIN`** - Count queries
4. **Search for `DML_BEGIN`** - Count DML operations
5. **Search for `LOOP_BEGIN`** - Check for operations in loops

### Deep Analysis

1. **Trace the call stack** - Use `CODE_UNIT_STARTED` events
2. **Find the hotspot** - Use `Apex Profiling: FINEST` for method timing
3. **Identify large queries** - Look for `[N rows]` in SOQL_EXECUTE_END
4. **Check callout timing** - Look for slow `CALLOUT_EXTERNAL_EXIT`
5. **Monitor heap growth** - Track `HEAP_ALLOCATE` events

---

## Related Commands

| Command | Purpose |
|---------|---------|
| `sf apex list log` | List available logs |
| `sf apex get log --log-id XXX` | Download specific log |
| `sf apex tail log` | Stream logs real-time |
| `sf data delete record --sobject ApexLog --record-id <id>` | Delete individual log record |

See [cli-commands.md](./cli-commands.md) for detailed command reference.
