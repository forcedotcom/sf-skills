/**
 * Bulkified Query Patterns
 *
 * This file demonstrates the correct patterns for querying related data
 * in bulk operations (triggers, batches, etc.) without hitting governor limits.
 *
 * Key Pattern: Collect IDs first, query once, use Map for O(1) lookups.
 *
 * @see https://www.apexhours.com/bulkification-of-apex-triggers/
 * @see https://medium.com/@saurabh.samirs/salesforce-apex-triggers-5-bulkification-patterns-to-avoid-soql-dml-limits-f4e9c8bbfb3a
 */

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 1: Simple Map Lookup (Parent Record Access)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * ❌ ANTI-PATTERN: Query inside loop
 * This code will fail with "Too many SOQL queries: 101" for 101+ records
 */
public class AntiPatternExample {
    public void processContacts_WRONG(List<Contact> contacts) {
        for (Contact c : contacts) {
            // ❌ QUERY IN LOOP - will hit governor limit!
            Account a = [SELECT Name FROM Account WHERE Id = :c.AccountId];
            c.Description = 'Account: ' + a.Name;
        }
    }
}

/**
 * ✅ CORRECT PATTERN: Bulk query with Map lookup
 * Uses 1 query regardless of record count
 */
public class BulkPatternExample {
    public void processContacts_CORRECT(List<Contact> contacts) {
        // Step 1: Collect all parent IDs
        Set<Id> accountIds = new Set<Id>();
        for (Contact c : contacts) {
            if (c.AccountId != null) {
                accountIds.add(c.AccountId);
            }
        }

        // Step 2: Single bulk query
        Map<Id, Account> accountMap = new Map<Id, Account>([
            SELECT Id, Name
            FROM Account
            WHERE Id IN :accountIds
            WITH SECURITY_ENFORCED
        ]);

        // Step 3: O(1) Map lookups
        for (Contact c : contacts) {
            Account a = accountMap.get(c.AccountId);
            if (a != null) {
                c.Description = 'Account: ' + a.Name;
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 2: Grouped Child Records (One-to-Many)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Get child records grouped by parent ID
 * Useful when you need all children for each parent
 */
public class GroupedChildPattern {

    /**
     * Returns Contacts grouped by their AccountId
     */
    public static Map<Id, List<Contact>> getContactsByAccountId(Set<Id> accountIds) {
        Map<Id, List<Contact>> contactsByAccount = new Map<Id, List<Contact>>();

        // Initialize empty lists for each account
        for (Id accountId : accountIds) {
            contactsByAccount.put(accountId, new List<Contact>());
        }

        // Single query for all contacts
        for (Contact c : [
            SELECT Id, FirstName, LastName, Email, AccountId
            FROM Contact
            WHERE AccountId IN :accountIds
            WITH SECURITY_ENFORCED
        ]) {
            contactsByAccount.get(c.AccountId).add(c);
        }

        return contactsByAccount;
    }

    /**
     * Usage example in a trigger
     */
    public void onAccountUpdate(List<Account> accounts) {
        Set<Id> accountIds = new Set<Id>();
        for (Account a : accounts) {
            accountIds.add(a.Id);
        }

        // Get all contacts for all accounts in ONE query
        Map<Id, List<Contact>> contactsByAccount = getContactsByAccountId(accountIds);

        for (Account a : accounts) {
            List<Contact> accountContacts = contactsByAccount.get(a.Id);
            System.debug('Account ' + a.Name + ' has ' + accountContacts.size() + ' contacts');
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 3: Multi-Level Relationship Lookup
// ═══════════════════════════════════════════════════════════════════════════

/**
 * When you need to traverse multiple relationship levels
 * Example: Contact -> Account -> Owner
 */
public class MultiLevelLookupPattern {

    public void enrichContactsWithOwnerInfo(List<Contact> contacts) {
        // Step 1: Get Account IDs
        Set<Id> accountIds = new Set<Id>();
        for (Contact c : contacts) {
            if (c.AccountId != null) {
                accountIds.add(c.AccountId);
            }
        }

        // Step 2: Query Accounts with Owner info (single query)
        Map<Id, Account> accountMap = new Map<Id, Account>([
            SELECT Id, Name, OwnerId, Owner.Name, Owner.Email
            FROM Account
            WHERE Id IN :accountIds
            WITH SECURITY_ENFORCED
        ]);

        // Step 3: Use the data
        for (Contact c : contacts) {
            Account a = accountMap.get(c.AccountId);
            if (a != null && a.Owner != null) {
                c.Description = 'Account Owner: ' + a.Owner.Name;
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 4: Conditional Query Based on Field Values
// ═══════════════════════════════════════════════════════════════════════════

/**
 * When you only need to query for certain records based on field values
 */
public class ConditionalQueryPattern {

    public void updateHighValueOpportunities(List<Opportunity> opportunities) {
        // Step 1: Filter to high-value opportunities only
        Set<Id> highValueAccountIds = new Set<Id>();
        for (Opportunity opp : opportunities) {
            if (opp.Amount != null && opp.Amount > 100000 && opp.AccountId != null) {
                highValueAccountIds.add(opp.AccountId);
            }
        }

        // Step 2: Only query if we have high-value records
        if (highValueAccountIds.isEmpty()) {
            return; // No query needed!
        }

        Map<Id, Account> accountMap = new Map<Id, Account>([
            SELECT Id, Name, AnnualRevenue, Industry
            FROM Account
            WHERE Id IN :highValueAccountIds
            WITH SECURITY_ENFORCED
        ]);

        // Step 3: Process only the high-value opportunities
        for (Opportunity opp : opportunities) {
            if (opp.Amount != null && opp.Amount > 100000) {
                Account a = accountMap.get(opp.AccountId);
                if (a != null) {
                    opp.Description = 'High-value opp for ' + a.Industry + ' account';
                }
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 5: Avoiding Duplicate Queries in Complex Logic
// ═══════════════════════════════════════════════════════════════════════════

/**
 * When the same data is needed in multiple methods,
 * query once and pass the Map around
 */
public class SharedQueryPattern {

    private Map<Id, Account> accountCache;

    /**
     * Initialize the cache once at the start of processing
     */
    public void initializeCache(Set<Id> accountIds) {
        this.accountCache = new Map<Id, Account>([
            SELECT Id, Name, Industry, AnnualRevenue, OwnerId
            FROM Account
            WHERE Id IN :accountIds
            WITH SECURITY_ENFORCED
        ]);
    }

    /**
     * Multiple methods can use the cached data
     */
    public String getAccountName(Id accountId) {
        Account a = accountCache.get(accountId);
        return a != null ? a.Name : null;
    }

    public String getAccountIndustry(Id accountId) {
        Account a = accountCache.get(accountId);
        return a != null ? a.Industry : null;
    }

    public Decimal getAccountRevenue(Id accountId) {
        Account a = accountCache.get(accountId);
        return a != null ? a.AnnualRevenue : 0;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 6: SOQL For Loop (Large Dataset Processing)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * For processing very large datasets without hitting heap limits
 * The SOQL for loop fetches 200 records at a time
 */
public class LargeDatasetPattern {

    public void processAllAccounts() {
        // This fetches 200 records at a time, not all 50,000
        for (Account a : [
            SELECT Id, Name, Industry
            FROM Account
            WHERE CreatedDate = THIS_YEAR
        ]) {
            // Process one record at a time
            // Heap stays small because only 200 records in memory
            processAccount(a);
        }
    }

    public void processAllAccountsInBatches() {
        // Alternative: explicit batch processing (200 at a time)
        for (List<Account> accountBatch : [
            SELECT Id, Name, Industry
            FROM Account
            WHERE CreatedDate = THIS_YEAR
        ]) {
            // Process 200 records at a time
            processBatch(accountBatch);
        }
    }

    private void processAccount(Account a) {
        // Individual record processing
    }

    private void processBatch(List<Account> accounts) {
        // Batch processing
    }
}
