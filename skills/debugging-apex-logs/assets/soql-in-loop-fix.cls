/**
 * SOQL IN LOOP FIX PATTERN
 *
 * Problem: SOQL queries inside loops consume governor limits rapidly
 * Detection: DEBUG LOG shows repeated SOQL_EXECUTE_BEGIN entries
 * Limit: 100 SOQL queries per synchronous transaction
 *
 * This template demonstrates the bulkification pattern to fix SOQL in loops.
 */

// ═══════════════════════════════════════════════════════════════════════════
// BEFORE: SOQL IN LOOP (PROBLEMATIC)
// ═══════════════════════════════════════════════════════════════════════════

public class AccountService_BEFORE {

    // This method will fail if accounts.size() > 100
    public void processAccounts(List<Account> accounts) {
        for (Account acc : accounts) {
            // SOQL inside loop - each iteration uses 1 query
            Contact primaryContact = [
                SELECT Id, Email, Phone
                FROM Contact
                WHERE AccountId = :acc.Id
                AND IsPrimary__c = true
                LIMIT 1
            ];

            if (primaryContact != null) {
                acc.Primary_Contact_Email__c = primaryContact.Email;
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// AFTER: BULKIFIED PATTERN (CORRECT)
// ═══════════════════════════════════════════════════════════════════════════

public class AccountService_AFTER {

    // This method uses only 1 SOQL query regardless of accounts.size()
    public void processAccounts(List<Account> accounts) {
        // Step 1: Collect all Account IDs
        Set<Id> accountIds = new Set<Id>();
        for (Account acc : accounts) {
            accountIds.add(acc.Id);
        }

        // Step 2: Single SOQL query BEFORE the loop
        Map<Id, Contact> primaryContactsByAccountId = new Map<Id, Contact>();
        for (Contact c : [
            SELECT Id, Email, Phone, AccountId
            FROM Contact
            WHERE AccountId IN :accountIds
            AND IsPrimary__c = true
        ]) {
            primaryContactsByAccountId.put(c.AccountId, c);
        }

        // Step 3: Access from Map inside loop (no SOQL)
        for (Account acc : accounts) {
            Contact primaryContact = primaryContactsByAccountId.get(acc.Id);
            if (primaryContact != null) {
                acc.Primary_Contact_Email__c = primaryContact.Email;
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// ADVANCED: NESTED RELATIONSHIP PATTERN
// ═══════════════════════════════════════════════════════════════════════════

public class OrderService_Bulkified {

    // Complex scenario: Orders → Accounts → Contacts
    public void processOrders(List<Order> orders) {
        // Collect all Account IDs from Orders
        Set<Id> accountIds = new Set<Id>();
        for (Order o : orders) {
            if (o.AccountId != null) {
                accountIds.add(o.AccountId);
            }
        }

        // Query Accounts with related Contacts in ONE query (relationship query)
        Map<Id, Account> accountsWithContacts = new Map<Id, Account>([
            SELECT Id, Name,
                   (SELECT Id, Email FROM Contacts WHERE IsPrimary__c = true LIMIT 1)
            FROM Account
            WHERE Id IN :accountIds
        ]);

        // Process orders using the pre-queried data
        for (Order o : orders) {
            Account acc = accountsWithContacts.get(o.AccountId);
            if (acc != null && !acc.Contacts.isEmpty()) {
                o.Notification_Email__c = acc.Contacts[0].Email;
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN: MAP FACTORY FOR REUSABLE QUERIES
// ═══════════════════════════════════════════════════════════════════════════

public class ContactQueryService {

    /**
     * Factory method to get primary contacts by Account ID
     * Reusable across multiple services
     */
    public static Map<Id, Contact> getPrimaryContactsByAccountId(Set<Id> accountIds) {
        Map<Id, Contact> result = new Map<Id, Contact>();

        if (accountIds.isEmpty()) {
            return result;
        }

        for (Contact c : [
            SELECT Id, FirstName, LastName, Email, Phone, AccountId
            FROM Contact
            WHERE AccountId IN :accountIds
            AND IsPrimary__c = true
        ]) {
            result.put(c.AccountId, c);
        }

        return result;
    }

    /**
     * Get all contacts grouped by Account ID
     * Returns Map<AccountId, List<Contact>>
     */
    public static Map<Id, List<Contact>> getContactsGroupedByAccount(Set<Id> accountIds) {
        Map<Id, List<Contact>> result = new Map<Id, List<Contact>>();

        // Initialize empty lists for all accounts
        for (Id accId : accountIds) {
            result.put(accId, new List<Contact>());
        }

        for (Contact c : [
            SELECT Id, FirstName, LastName, Email, Phone, AccountId
            FROM Contact
            WHERE AccountId IN :accountIds
            ORDER BY CreatedDate DESC
        ]) {
            result.get(c.AccountId).add(c);
        }

        return result;
    }
}
