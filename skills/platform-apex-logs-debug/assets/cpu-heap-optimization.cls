/**
 * CPU TIME AND HEAP SIZE OPTIMIZATION PATTERNS
 *
 * CPU Limits:
 *   - Synchronous: 10,000 ms
 *   - Asynchronous: 60,000 ms
 *
 * Heap Limits:
 *   - Synchronous: 6 MB
 *   - Asynchronous: 12 MB
 *
 * This template demonstrates optimization patterns for CPU and heap limits.
 */

// ═══════════════════════════════════════════════════════════════════════════
// CPU OPTIMIZATION: ALGORITHM COMPLEXITY
// ═══════════════════════════════════════════════════════════════════════════

public class CPUOptimization {

    // BEFORE: O(n²) - Nested loops are expensive
    public void findDuplicatesBAD(List<Contact> contacts) {
        List<Contact> duplicates = new List<Contact>();

        for (Integer i = 0; i < contacts.size(); i++) {
            for (Integer j = i + 1; j < contacts.size(); j++) {
                if (contacts[i].Email == contacts[j].Email) {
                    duplicates.add(contacts[j]);
                }
            }
        }
    }

    // AFTER: O(n) - Use Map for lookups
    public List<Contact> findDuplicatesGOOD(List<Contact> contacts) {
        Map<String, Contact> emailToContact = new Map<String, Contact>();
        List<Contact> duplicates = new List<Contact>();

        for (Contact c : contacts) {
            if (c.Email == null) continue;

            String normalizedEmail = c.Email.toLowerCase();
            if (emailToContact.containsKey(normalizedEmail)) {
                duplicates.add(c);
            } else {
                emailToContact.put(normalizedEmail, c);
            }
        }

        return duplicates;
    }

    // BEFORE: Expensive string concatenation in loop
    public String buildReportBAD(List<Account> accounts) {
        String report = '';
        for (Account acc : accounts) {
            report += acc.Name + '\n';  // Creates new string each iteration!
        }
        return report;
    }

    // AFTER: Use List and join
    public String buildReportGOOD(List<Account> accounts) {
        List<String> lines = new List<String>();
        for (Account acc : accounts) {
            lines.add(acc.Name);
        }
        return String.join(lines, '\n');
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// CPU OPTIMIZATION: CACHING
// ═══════════════════════════════════════════════════════════════════════════

public class CachingPatterns {

    // Cache expensive calculations
    private static Map<String, Decimal> calculationCache = new Map<String, Decimal>();

    public static Decimal getDiscountRate(String productCode, String region) {
        String cacheKey = productCode + ':' + region;

        if (calculationCache.containsKey(cacheKey)) {
            return calculationCache.get(cacheKey);  // Cache hit - no CPU cost
        }

        // Expensive calculation only happens once per unique key
        Decimal rate = performExpensiveCalculation(productCode, region);
        calculationCache.put(cacheKey, rate);

        return rate;
    }

    private static Decimal performExpensiveCalculation(String productCode, String region) {
        // Simulate complex calculation
        return 0.15;
    }

    // Platform Cache for cross-transaction caching
    public static Decimal getDiscountRateWithPlatformCache(String productCode, String region) {
        String cacheKey = 'discount_' + productCode + '_' + region;

        // Try to get from Platform Cache (Org partition)
        Cache.OrgPartition orgPart = Cache.Org.getPartition('local.DiscountCache');
        Decimal cachedRate = (Decimal)orgPart.get(cacheKey);

        if (cachedRate != null) {
            return cachedRate;
        }

        // Calculate and cache
        Decimal rate = performExpensiveCalculation(productCode, region);
        orgPart.put(cacheKey, rate, 3600);  // Cache for 1 hour

        return rate;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// HEAP OPTIMIZATION: LARGE DATA PROCESSING
// ═══════════════════════════════════════════════════════════════════════════

public class HeapOptimization {

    // BEFORE: Loads all records into heap at once
    public void processAllAccountsBAD() {
        List<Account> allAccounts = [SELECT Id, Name FROM Account];  // Could be millions!

        for (Account acc : allAccounts) {
            // Process each account
        }
    }

    // AFTER: SOQL FOR loop - streams records, doesn't load all into heap
    public void processAllAccountsGOOD() {
        for (Account acc : [SELECT Id, Name FROM Account]) {
            // Each record is loaded individually
            // Previous record can be garbage collected
            processAccount(acc);
        }
    }

    private void processAccount(Account acc) {
        // Process single account
    }

    // AFTER: Batch processing for very large datasets
    public void processAllAccountsBATCH() {
        // Use Database.executeBatch for millions of records
        Database.executeBatch(new AccountProcessorBatch(), 200);
    }
}

// Batch class for large datasets
public class AccountProcessorBatch implements Database.Batchable<SObject> {

    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator('SELECT Id, Name FROM Account');
    }

    public void execute(Database.BatchableContext bc, List<Account> scope) {
        // Process 200 records at a time (controlled heap usage)
        for (Account acc : scope) {
            // Process each account
        }
    }

    public void finish(Database.BatchableContext bc) {
        // Optional: Send completion notification
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// HEAP OPTIMIZATION: CLEARING REFERENCES
// ═══════════════════════════════════════════════════════════════════════════

public class HeapClearingPatterns {

    // Clear large collections when no longer needed
    public void processWithClearing() {
        // Phase 1: Query and process
        List<Account> accounts = [SELECT Id, Name FROM Account LIMIT 10000];
        Map<Id, String> accountNames = new Map<Id, String>();

        for (Account acc : accounts) {
            accountNames.put(acc.Id, acc.Name);
        }

        // Clear the original list - no longer needed
        accounts.clear();
        accounts = null;

        // Phase 2: Use the map
        for (Id accId : accountNames.keySet()) {
            // Process using map
        }

        // Clear the map when done
        accountNames.clear();
        accountNames = null;
    }

    // Use transient for Visualforce controllers
    public class LargeDataController {
        // transient = not stored in view state, reduces heap in page transitions
        transient public List<Account> largeAccountList { get; set; }

        public LargeDataController() {
            largeAccountList = [SELECT Id, Name FROM Account LIMIT 5000];
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// CPU OPTIMIZATION: ASYNC PROCESSING
// ═══════════════════════════════════════════════════════════════════════════

public class AsyncProcessingPatterns {

    // Move expensive operations to @future
    @future
    public static void processExpensiveOperation(Set<Id> recordIds) {
        // Has 60 second CPU limit instead of 10 seconds
        for (Id recordId : recordIds) {
            // Expensive processing
        }
    }

    // Use Queueable for chained processing
    public class ExpensiveQueueable implements Queueable {
        private List<Id> recordIds;

        public ExpensiveQueueable(List<Id> recordIds) {
            this.recordIds = recordIds;
        }

        public void execute(QueueableContext context) {
            // Process first batch
            List<Id> batch = new List<Id>();
            List<Id> remaining = new List<Id>();

            for (Integer i = 0; i < recordIds.size(); i++) {
                if (i < 100) {
                    batch.add(recordIds[i]);
                } else {
                    remaining.add(recordIds[i]);
                }
            }

            // Process this batch
            processBatch(batch);

            // Chain next batch if needed
            if (!remaining.isEmpty()) {
                System.enqueueJob(new ExpensiveQueueable(remaining));
            }
        }

        private void processBatch(List<Id> batch) {
            // Process 100 records
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN: LIMITS MONITORING
// ═══════════════════════════════════════════════════════════════════════════

public class LimitsMonitoring {

    // Check limits during execution
    public void processWithLimitChecking(List<Account> accounts) {
        Integer cpuWarning = 8000;  // 80% of 10,000ms limit
        Integer heapWarning = 4800000;  // 80% of 6MB limit

        for (Account acc : accounts) {
            // Check CPU limit
            if (Limits.getCpuTime() > cpuWarning) {
                System.debug(LoggingLevel.WARN,
                    'CPU limit approaching: ' + Limits.getCpuTime() + 'ms');
                // Consider switching to async
                break;
            }

            // Check heap limit
            if (Limits.getHeapSize() > heapWarning) {
                System.debug(LoggingLevel.WARN,
                    'Heap limit approaching: ' + Limits.getHeapSize() + ' bytes');
                break;
            }

            processAccount(acc);
        }
    }

    // Debug helper: Print all limits
    public static void debugLimits() {
        System.debug('=== GOVERNOR LIMITS ===');
        System.debug('SOQL Queries: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
        System.debug('DML Statements: ' + Limits.getDmlStatements() + '/' + Limits.getLimitDmlStatements());
        System.debug('DML Rows: ' + Limits.getDmlRows() + '/' + Limits.getLimitDmlRows());
        System.debug('CPU Time: ' + Limits.getCpuTime() + '/' + Limits.getLimitCpuTime());
        System.debug('Heap Size: ' + Limits.getHeapSize() + '/' + Limits.getLimitHeapSize());
        System.debug('Callouts: ' + Limits.getCallouts() + '/' + Limits.getLimitCallouts());
    }
}
