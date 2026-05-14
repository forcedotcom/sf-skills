/**
 * DML IN LOOP FIX PATTERN
 *
 * Problem: DML operations inside loops consume governor limits rapidly
 * Detection: DEBUG LOG shows repeated DML_BEGIN entries
 * Limits:
 *   - 150 DML statements per transaction
 *   - 10,000 DML rows per transaction
 *
 * This template demonstrates the collection pattern to fix DML in loops.
 */

// ═══════════════════════════════════════════════════════════════════════════
// BEFORE: DML IN LOOP (PROBLEMATIC)
// ═══════════════════════════════════════════════════════════════════════════

public class ContactService_BEFORE {

    // This method will fail if accounts.size() > 150
    public void createContactsForAccounts(List<Account> accounts) {
        for (Account acc : accounts) {
            // DML inside loop - each iteration uses 1 DML statement
            Contact c = new Contact(
                FirstName = 'Primary',
                LastName = 'Contact',
                AccountId = acc.Id,
                Email = acc.Name.replaceAll(' ', '') + '@example.com'
            );
            insert c;  // DML in loop!
        }
    }

    // Updates in loop - also problematic
    public void updateAccountStatuses(List<Account> accounts, String newStatus) {
        for (Account acc : accounts) {
            acc.Status__c = newStatus;
            update acc;  // DML in loop!
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// AFTER: COLLECTION PATTERN (CORRECT)
// ═══════════════════════════════════════════════════════════════════════════

public class ContactService_AFTER {

    // This method uses only 1 DML statement regardless of accounts.size()
    public void createContactsForAccounts(List<Account> accounts) {
        // Step 1: Build list of records to insert
        List<Contact> contactsToInsert = new List<Contact>();

        for (Account acc : accounts) {
            Contact c = new Contact(
                FirstName = 'Primary',
                LastName = 'Contact',
                AccountId = acc.Id,
                Email = acc.Name.replaceAll(' ', '') + '@example.com'
            );
            contactsToInsert.add(c);  // Add to list, no DML
        }

        // Step 2: Single DML statement AFTER the loop
        if (!contactsToInsert.isEmpty()) {
            insert contactsToInsert;
        }
    }

    // Updates outside loop - correct pattern
    public void updateAccountStatuses(List<Account> accounts, String newStatus) {
        // Modify in loop (no DML)
        for (Account acc : accounts) {
            acc.Status__c = newStatus;
        }

        // Single DML after loop
        if (!accounts.isEmpty()) {
            update accounts;
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// ADVANCED: MIXED INSERT/UPDATE/DELETE PATTERN
// ═══════════════════════════════════════════════════════════════════════════

public class RecordProcessor_Bulkified {

    /**
     * Process records with conditional insert/update/delete
     * Uses collections for all DML operations
     */
    public void processRecords(List<Account> accounts) {
        // Collections for different DML operations
        List<Contact> contactsToInsert = new List<Contact>();
        List<Contact> contactsToUpdate = new List<Contact>();
        List<Contact> contactsToDelete = new List<Contact>();

        // Query existing contacts once
        Set<Id> accountIds = new Set<Id>();
        for (Account acc : accounts) {
            accountIds.add(acc.Id);
        }

        Map<Id, Contact> existingContacts = new Map<Id, Contact>();
        for (Contact c : [
            SELECT Id, AccountId, Email, IsInactive__c
            FROM Contact
            WHERE AccountId IN :accountIds
        ]) {
            existingContacts.put(c.AccountId, c);
        }

        // Process and categorize
        for (Account acc : accounts) {
            Contact existing = existingContacts.get(acc.Id);

            if (existing == null) {
                // No contact exists - INSERT
                contactsToInsert.add(new Contact(
                    FirstName = 'Auto',
                    LastName = 'Generated',
                    AccountId = acc.Id
                ));
            } else if (existing.IsInactive__c) {
                // Inactive contact - DELETE
                contactsToDelete.add(existing);
            } else {
                // Active contact - UPDATE
                existing.LastActivityDate__c = Date.today();
                contactsToUpdate.add(existing);
            }
        }

        // Execute DML operations (3 statements max, regardless of record count)
        if (!contactsToInsert.isEmpty()) {
            insert contactsToInsert;
        }
        if (!contactsToUpdate.isEmpty()) {
            update contactsToUpdate;
        }
        if (!contactsToDelete.isEmpty()) {
            delete contactsToDelete;
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN: UPSERT FOR INSERT-OR-UPDATE LOGIC
// ═══════════════════════════════════════════════════════════════════════════

public class UpsertPatternService {

    /**
     * When you need to insert if not exists, update if exists
     * Use UPSERT with an External ID field
     */
    public void syncExternalContacts(List<ExternalContact> externalData) {
        List<Contact> contactsToUpsert = new List<Contact>();

        for (ExternalContact ext : externalData) {
            Contact c = new Contact(
                External_Id__c = ext.id,  // External ID field
                FirstName = ext.firstName,
                LastName = ext.lastName,
                Email = ext.email
            );
            contactsToUpsert.add(c);
        }

        // Single upsert handles both insert and update
        if (!contactsToUpsert.isEmpty()) {
            upsert contactsToUpsert External_Id__c;
        }
    }

    // Wrapper class for external data
    public class ExternalContact {
        public String id;
        public String firstName;
        public String lastName;
        public String email;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN: PARTIAL SUCCESS HANDLING
// ═══════════════════════════════════════════════════════════════════════════

public class PartialSuccessService {

    /**
     * Handle partial failures gracefully
     * Use Database.insert with allOrNone = false
     */
    public List<Database.SaveResult> insertWithPartialSuccess(List<Contact> contacts) {
        if (contacts.isEmpty()) {
            return new List<Database.SaveResult>();
        }

        // allOrNone = false allows partial success
        List<Database.SaveResult> results = Database.insert(contacts, false);

        // Log failures for analysis
        for (Integer i = 0; i < results.size(); i++) {
            Database.SaveResult sr = results[i];
            if (!sr.isSuccess()) {
                for (Database.Error err : sr.getErrors()) {
                    System.debug(LoggingLevel.ERROR,
                        'Failed to insert contact: ' + contacts[i] +
                        ' Error: ' + err.getMessage()
                    );
                }
            }
        }

        return results;
    }
}
