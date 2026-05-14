<!-- Parent: debugging-apex-logs/SKILL.md -->
# Apex Benchmarking Guide

Performance testing is essential for writing efficient Apex code. This guide covers reliable benchmarking techniques and real-world performance data based on established Apex community practices and Salesforce governor limit behavior.

---

## Why Benchmark?

"Premature optimization is the root of all evil" - but **informed optimization** is essential. Benchmarking answers:

1. **Which approach is faster?** (Loop styles, data structures)
2. **Will this scale?** (200 records vs 10,000)
3. **Where are the bottlenecks?** (CPU, heap, SOQL)

---

## Apex Benchmarking Technique

The recommended approach for reliable Apex performance testing:

### The Pattern

```apex
// Run in Anonymous Apex for consistent environment
Long startTime = System.currentTimeMillis();

// Your code to benchmark
for (Integer i = 0; i < 10000; i++) {
    // Operation being tested
}

Long endTime = System.currentTimeMillis();
System.debug('Duration: ' + (endTime - startTime) + 'ms');
```

### Key Principles

| Principle | Why It Matters |
|-----------|----------------|
| **Use Anonymous Apex** | Consistent execution environment, no trigger interference |
| **Run Multiple Iterations** | Averages out JIT compilation and garbage collection |
| **Test at Scale** | 200 records ≠ 10,000 records in terms of performance |
| **Isolate the Operation** | Test one thing at a time |
| **Run Multiple Times** | First run often slower due to JIT compilation |

### Example: Complete Benchmark

```apex
// Comprehensive benchmark template
public class BenchmarkRunner {

    public static void compareMethods() {
        Integer iterations = 10000;

        // Warm-up run (JIT compilation)
        warmUp();

        // Method A
        Long startA = System.currentTimeMillis();
        for (Integer i = 0; i < iterations; i++) {
            methodA();
        }
        Long durationA = System.currentTimeMillis() - startA;

        // Method B
        Long startB = System.currentTimeMillis();
        for (Integer i = 0; i < iterations; i++) {
            methodB();
        }
        Long durationB = System.currentTimeMillis() - startB;

        // Results
        System.debug('Method A: ' + durationA + 'ms');
        System.debug('Method B: ' + durationB + 'ms');
        System.debug('Difference: ' + Math.abs(durationA - durationB) + 'ms');
        System.debug('Winner: ' + (durationA < durationB ? 'Method A' : 'Method B'));
    }

    private static void warmUp() {
        for (Integer i = 0; i < 100; i++) {
            methodA();
            methodB();
        }
    }

    private static void methodA() { /* Implementation A */ }
    private static void methodB() { /* Implementation B */ }
}
```

---

## Real-World Benchmark Results

### String Concatenation vs String.join()

From documented Apex benchmarks:

| Method | Records | Duration | Result |
|--------|---------|----------|--------|
| String `+=` in loop | 1,750 | 11,767ms | CPU LIMIT HIT |
| `String.join()` | 7,500 | 539ms | Still running |
| **Improvement** | - | **22x faster** | - |

```apex
// ❌ SLOW: String concatenation in loop (O(n²) string copies)
String result = '';
for (Account acc : accounts) {
    result += acc.Name + '\n';  // Creates new string each time!
}

// ✅ FAST: String.join() (O(n) single allocation)
List<String> names = new List<String>();
for (Account acc : accounts) {
    names.add(acc.Name);
}
String result = String.join(names, '\n');
```

### Loop Performance Comparison

From documented Apex loop benchmarks (10,000 iterations):

| Loop Type | Duration | Notes |
|-----------|----------|-------|
| While loop | ~0.4s | Fastest |
| Cached iterator | ~0.8s | Good alternative |
| For loop (index) | ~1.4s | Acceptable |
| Enhanced for-each | ~2.4s | Convenient but slower |
| Uncached iterator | CPU LIMIT | Avoid |

```apex
// 🏆 FASTEST: While loop
Iterator<Account> iter = accounts.iterator();
while (iter.hasNext()) {
    Account acc = iter.next();
    // process
}

// ✅ GOOD: Traditional for loop
for (Integer i = 0; i < accounts.size(); i++) {
    Account acc = accounts[i];
    // process
}

// ⚠️ CONVENIENT BUT SLOWER: Enhanced for-each
for (Account acc : accounts) {
    // process - OK for small collections
}
```

### Map vs List Lookup

| Operation | Complexity | 10,000 lookups |
|-----------|------------|----------------|
| List.contains() | O(n) | ~500ms |
| Set.contains() | O(1) | ~5ms |
| Map.containsKey() | O(1) | ~5ms |

```apex
// ❌ SLOW: List lookup
List<Id> processedIds = new List<Id>();
for (Account acc : accounts) {
    if (!processedIds.contains(acc.Id)) {  // O(n) each time!
        processedIds.add(acc.Id);
    }
}

// ✅ FAST: Set lookup
Set<Id> processedIds = new Set<Id>();
for (Account acc : accounts) {
    if (!processedIds.contains(acc.Id)) {  // O(1) constant time
        processedIds.add(acc.Id);
    }
}
```

---

## Governor Limit Ceilings

### Official Limits

| Limit | Synchronous | Asynchronous |
|-------|-------------|--------------|
| CPU Time | 10,000 ms | 60,000 ms |
| Heap Size | 6 MB | 12 MB |
| SOQL Queries | 100 | 200 |
| DML Statements | 150 | 150 |

### Practical Thresholds

| Limit | Warning (80%) | Critical (95%) |
|-------|---------------|----------------|
| CPU Time | 8,000 ms | 9,500 ms |
| Heap Size | 4.8 MB | 5.7 MB |
| SOQL Queries | 80 | 95 |

### Runtime Limit Checking

```apex
public void processWithSafety(List<Account> accounts) {
    Integer cpuWarning = 8000;
    Integer heapWarning = 4800000;

    for (Account acc : accounts) {
        // Check before each operation
        if (Limits.getCpuTime() > cpuWarning) {
            System.debug(LoggingLevel.WARN,
                'CPU approaching limit: ' + Limits.getCpuTime() + 'ms');
            // Consider switching to async or chunking
            break;
        }

        if (Limits.getHeapSize() > heapWarning) {
            System.debug(LoggingLevel.WARN,
                'Heap approaching limit: ' + Limits.getHeapSize() + ' bytes');
            break;
        }

        processAccount(acc);
    }
}
```

---

## Benchmarking Anti-Patterns

### ❌ Don't Do These

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Testing in triggers | Inconsistent environment | Use Anonymous Apex |
| Single iteration | JIT variance affects results | Run 1000+ iterations |
| Testing with 10 records | Doesn't reveal O(n²) issues | Test with 200+ records |
| Ignoring warm-up | First run skewed by JIT | Add warm-up phase |
| Mixing operations | Can't isolate bottleneck | Test one thing at a time |

---

## Benchmarking Checklist

Before optimizing, verify:

- [ ] Ran benchmark multiple times (3-5 runs)
- [ ] Used 1000+ iterations for micro-benchmarks
- [ ] Tested with production-scale data (200+ records)
- [ ] Included warm-up phase
- [ ] Ran in Anonymous Apex (not test context)
- [ ] Compared both approaches fairly
- [ ] Considered readability trade-offs

---

## When NOT to Optimize

Sometimes clarity beats performance:

```apex
// More readable, negligible performance difference for small collections
for (Account acc : accounts) {
    acc.Description = acc.Name + ' - Updated';
}

// vs micro-optimized but harder to read
Iterator<Account> iter = accounts.iterator();
while (iter.hasNext()) {
    Account acc = iter.next();
    acc.Description = acc.Name + ' - Updated';
}
```

**Rule of thumb**: Optimize when:
1. Processing 200+ records regularly
2. Approaching governor limits
3. User experience is affected
4. Benchmarks show measurable improvement

---

## Related Resources

- [assets/benchmarking-template.cls](../assets/benchmarking-template.cls) - Ready-to-use benchmark template
- [assets/cpu-heap-optimization.cls](../assets/cpu-heap-optimization.cls) - Optimization patterns
- [Apex Log Analyzer](./log-analysis-tools.md) - Visual performance analysis
