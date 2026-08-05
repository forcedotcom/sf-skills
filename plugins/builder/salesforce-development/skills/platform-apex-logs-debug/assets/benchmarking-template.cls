/**
 * Apex Benchmarking Template
 *
 * Reliable performance testing using established Apex benchmarking techniques.
 * Run in Anonymous Apex for consistent results.
 *
 * Features:
 * - Warm-up phase to normalize JIT compilation
 * - Multiple iterations for statistical accuracy
 * - Side-by-side comparison of two approaches
 * - Automatic winner determination
 *
 * See: references/benchmarking-guide.md for methodology and benchmark data
 */

// ═══════════════════════════════════════════════════════════════════════════
// SIMPLE BENCHMARK (Copy into Anonymous Apex)
// ═══════════════════════════════════════════════════════════════════════════

// Quick single-operation benchmark
Long startTime = System.currentTimeMillis();

for (Integer i = 0; i < 10000; i++) {
    // Your operation here
    String s = 'test'.toUpperCase();
}

Long duration = System.currentTimeMillis() - startTime;
System.debug('Duration: ' + duration + 'ms');
System.debug('Per iteration: ' + (duration / 10000.0) + 'ms');


// ═══════════════════════════════════════════════════════════════════════════
// COMPARISON BENCHMARK CLASS
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Compare two implementations side-by-side
 *
 * Usage in Anonymous Apex:
 *   BenchmarkComparison.run();
 */
public class BenchmarkComparison {

    private static final Integer ITERATIONS = 10000;
    private static final Integer WARMUP_ITERATIONS = 100;

    public static void run() {
        System.debug('═══════════════════════════════════════════════════════');
        System.debug('BENCHMARK: [Description Here]');
        System.debug('Iterations: ' + ITERATIONS);
        System.debug('═══════════════════════════════════════════════════════');

        // Warm-up phase (normalizes JIT compilation effects)
        System.debug('\n🔥 Warm-up phase...');
        for (Integer i = 0; i < WARMUP_ITERATIONS; i++) {
            methodA();
            methodB();
        }
        System.debug('   Warm-up complete');

        // Benchmark Method A
        System.debug('\n📊 Running Method A...');
        Long startA = System.currentTimeMillis();
        for (Integer i = 0; i < ITERATIONS; i++) {
            methodA();
        }
        Long durationA = System.currentTimeMillis() - startA;

        // Benchmark Method B
        System.debug('📊 Running Method B...');
        Long startB = System.currentTimeMillis();
        for (Integer i = 0; i < ITERATIONS; i++) {
            methodB();
        }
        Long durationB = System.currentTimeMillis() - startB;

        // Results
        System.debug('\n═══════════════════════════════════════════════════════');
        System.debug('RESULTS');
        System.debug('═══════════════════════════════════════════════════════');
        System.debug('Method A: ' + durationA + 'ms (' + (durationA / (Decimal)ITERATIONS) + 'ms per iteration)');
        System.debug('Method B: ' + durationB + 'ms (' + (durationB / (Decimal)ITERATIONS) + 'ms per iteration)');
        System.debug('───────────────────────────────────────────────────────');

        Long difference = Math.abs(durationA - durationB);
        String winner = durationA < durationB ? 'Method A' : 'Method B';
        Decimal improvement = durationA < durationB
            ? (durationB / (Decimal)durationA)
            : (durationA / (Decimal)durationB);

        System.debug('🏆 Winner: ' + winner);
        System.debug('   Difference: ' + difference + 'ms');
        System.debug('   Improvement: ' + improvement.setScale(1) + 'x faster');

        // Governor limits status
        System.debug('\n📈 Governor Limits Used:');
        System.debug('   CPU Time: ' + Limits.getCpuTime() + '/' + Limits.getLimitCpuTime() + 'ms');
        System.debug('   Heap Size: ' + Limits.getHeapSize() + '/' + Limits.getLimitHeapSize() + ' bytes');
    }

    // ═══════════════════════════════════════════════════════════════════
    // METHODS TO COMPARE (Replace with your implementations)
    // ═══════════════════════════════════════════════════════════════════

    private static void methodA() {
        // Implementation A - e.g., String concatenation
        String result = '';
        for (Integer i = 0; i < 10; i++) {
            result += 'item' + i + ',';
        }
    }

    private static void methodB() {
        // Implementation B - e.g., String.join()
        List<String> items = new List<String>();
        for (Integer i = 0; i < 10; i++) {
            items.add('item' + i);
        }
        String result = String.join(items, ',');
    }
}


// ═══════════════════════════════════════════════════════════════════════════
// DATA STRUCTURE BENCHMARK
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Compare List vs Set vs Map lookup performance
 *
 * Expected Results:
 *   List.contains(): O(n) - slow
 *   Set.contains(): O(1) - fast
 *   Map.containsKey(): O(1) - fast
 */
public class DataStructureBenchmark {

    private static final Integer DATA_SIZE = 1000;
    private static final Integer LOOKUPS = 5000;

    public static void run() {
        // Setup test data
        List<String> testList = new List<String>();
        Set<String> testSet = new Set<String>();
        Map<String, Boolean> testMap = new Map<String, Boolean>();

        for (Integer i = 0; i < DATA_SIZE; i++) {
            String key = 'key_' + i;
            testList.add(key);
            testSet.add(key);
            testMap.put(key, true);
        }

        // Random lookup keys (mix of existing and non-existing)
        List<String> lookupKeys = new List<String>();
        for (Integer i = 0; i < LOOKUPS; i++) {
            lookupKeys.add('key_' + Math.mod(i * 7, DATA_SIZE * 2));
        }

        System.debug('═══════════════════════════════════════════════════════');
        System.debug('DATA STRUCTURE LOOKUP BENCHMARK');
        System.debug('Data Size: ' + DATA_SIZE + ' | Lookups: ' + LOOKUPS);
        System.debug('═══════════════════════════════════════════════════════');

        // List.contains()
        Long startList = System.currentTimeMillis();
        for (String key : lookupKeys) {
            Boolean found = testList.contains(key);
        }
        Long durationList = System.currentTimeMillis() - startList;

        // Set.contains()
        Long startSet = System.currentTimeMillis();
        for (String key : lookupKeys) {
            Boolean found = testSet.contains(key);
        }
        Long durationSet = System.currentTimeMillis() - startSet;

        // Map.containsKey()
        Long startMap = System.currentTimeMillis();
        for (String key : lookupKeys) {
            Boolean found = testMap.containsKey(key);
        }
        Long durationMap = System.currentTimeMillis() - startMap;

        // Results
        System.debug('\nRESULTS:');
        System.debug('List.contains(): ' + durationList + 'ms');
        System.debug('Set.contains():  ' + durationSet + 'ms');
        System.debug('Map.containsKey(): ' + durationMap + 'ms');

        if (durationList > 0) {
            System.debug('\nSet is ' + (durationList / Math.max(1, durationSet)) + 'x faster than List');
        }
    }
}


// ═══════════════════════════════════════════════════════════════════════════
// LOOP STYLE BENCHMARK
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Compare different loop constructs
 *
 * Expected Results (from documented Apex loop benchmarks):
 *   While loop: ~0.4s (fastest)
 *   Cached iterator: ~0.8s
 *   For loop (index): ~1.4s
 *   Enhanced for-each: ~2.4s
 */
public class LoopBenchmark {

    private static final Integer ITERATIONS = 10000;

    public static void run() {
        // Create test data
        List<Integer> numbers = new List<Integer>();
        for (Integer i = 0; i < 1000; i++) {
            numbers.add(i);
        }

        System.debug('═══════════════════════════════════════════════════════');
        System.debug('LOOP STYLE BENCHMARK');
        System.debug('Outer Iterations: ' + ITERATIONS + ' | List Size: ' + numbers.size());
        System.debug('═══════════════════════════════════════════════════════');

        // While loop with iterator
        Long startWhile = System.currentTimeMillis();
        for (Integer outer = 0; outer < ITERATIONS; outer++) {
            Iterator<Integer> iter = numbers.iterator();
            while (iter.hasNext()) {
                Integer num = iter.next();
            }
        }
        Long durationWhile = System.currentTimeMillis() - startWhile;

        // Traditional for loop
        Long startFor = System.currentTimeMillis();
        for (Integer outer = 0; outer < ITERATIONS; outer++) {
            for (Integer i = 0; i < numbers.size(); i++) {
                Integer num = numbers[i];
            }
        }
        Long durationFor = System.currentTimeMillis() - startFor;

        // Enhanced for-each
        Long startEnhanced = System.currentTimeMillis();
        for (Integer outer = 0; outer < ITERATIONS; outer++) {
            for (Integer num : numbers) {
                // Just iterate
            }
        }
        Long durationEnhanced = System.currentTimeMillis() - startEnhanced;

        // Results
        System.debug('\nRESULTS:');
        System.debug('While loop:     ' + durationWhile + 'ms');
        System.debug('For loop:       ' + durationFor + 'ms');
        System.debug('Enhanced for:   ' + durationEnhanced + 'ms');

        System.debug('\n📊 Analysis:');
        Long fastest = Math.min(durationWhile, Math.min(durationFor, durationEnhanced));
        if (durationWhile == fastest) {
            System.debug('🏆 While loop is fastest');
        } else if (durationFor == fastest) {
            System.debug('🏆 For loop is fastest');
        } else {
            System.debug('🏆 Enhanced for is fastest');
        }
    }
}


// ═══════════════════════════════════════════════════════════════════════════
// STRING BENCHMARK (demonstrates 22x improvement)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * String concatenation vs String.join()
 *
 * Expected Results (from documented Apex benchmarks):
 *   Concatenation: 11,767ms for 1,750 items (CPU LIMIT)
 *   String.join(): 539ms for 7,500 items (still running)
 *   Improvement: ~22x faster
 */
public class StringBenchmark {

    public static void run() {
        System.debug('═══════════════════════════════════════════════════════');
        System.debug('STRING BUILDING BENCHMARK');
        System.debug('═══════════════════════════════════════════════════════');

        // Test with safe number of items
        Integer itemCount = 500;

        // Method 1: String concatenation (BAD)
        Long startConcat = System.currentTimeMillis();
        String resultConcat = '';
        for (Integer i = 0; i < itemCount; i++) {
            resultConcat += 'Item_' + i + '_Name\n';
        }
        Long durationConcat = System.currentTimeMillis() - startConcat;

        // Method 2: String.join() (GOOD)
        Long startJoin = System.currentTimeMillis();
        List<String> items = new List<String>();
        for (Integer i = 0; i < itemCount; i++) {
            items.add('Item_' + i + '_Name');
        }
        String resultJoin = String.join(items, '\n');
        Long durationJoin = System.currentTimeMillis() - startJoin;

        // Results
        System.debug('\nRESULTS (' + itemCount + ' items):');
        System.debug('String +=:      ' + durationConcat + 'ms');
        System.debug('String.join():  ' + durationJoin + 'ms');

        if (durationJoin > 0 && durationConcat > durationJoin) {
            System.debug('\n🏆 String.join() is ' + (durationConcat / durationJoin) + 'x faster!');
        }

        System.debug('\n⚠️ WARNING: With larger datasets, concatenation hits CPU limit!');
        System.debug('   Documented benchmark: 11,767ms for 1,750 items (concat) vs 539ms for 7,500 items (join)');
    }
}
