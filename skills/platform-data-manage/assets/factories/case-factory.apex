/**
 * Test Data Factory for Case records
 * Supports bulk creation with Account/Contact relationships and priority variations
 *
 * Usage:
 *   List<Case> cases = TestDataFactory_Case.create(200);
 *   List<Case> casesForAccount = TestDataFactory_Case.createForAccount(50, accountId);
 *   List<Case> highPriority = TestDataFactory_Case.createWithPriority(100, 'High');
 */
public class TestDataFactory_Case {

    private static final String DEFAULT_SUBJECT_PREFIX = 'Test Case ';
    private static final String DEFAULT_STATUS = 'New';
    private static final String DEFAULT_PRIORITY = 'Medium';
    private static final String DEFAULT_ORIGIN = 'Web';

    /**
     * Create and insert Case records (creates parent Account automatically)
     * @param count Number of records to create
     * @return List of inserted Case records with IDs
     */
    public static List<Case> create(Integer count) {
        return create(count, true);
    }

    /**
     * Create Case records with insert option
     * @param count Number of records to create
     * @param doInsert Whether to insert records
     * @return List of Case records
     */
    public static List<Case> create(Integer count, Boolean doInsert) {
        // Create parent Account and Contact
        Account parentAccount = new Account(Name = 'Test Parent Account for Cases');
        insert parentAccount;

        Contact parentContact = new Contact(
            FirstName = 'Test',
            LastName = 'CaseContact',
            AccountId = parentAccount.Id,
            Email = 'casecontact@testfactory.example.com'
        );
        insert parentContact;

        return createForAccountAndContact(count, parentAccount.Id, parentContact.Id, doInsert);
    }

    /**
     * Create Case records for a specific Account
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @return List of inserted Case records
     */
    public static List<Case> createForAccount(Integer count, Id accountId) {
        return createForAccount(count, accountId, true);
    }

    /**
     * Create Case records for a specific Account with insert option
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @param doInsert Whether to insert records
     * @return List of Case records
     */
    public static List<Case> createForAccount(Integer count, Id accountId, Boolean doInsert) {
        List<Case> records = new List<Case>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, accountId, null));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Case records for specific Account and Contact
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @param contactId Parent Contact ID
     * @param doInsert Whether to insert records
     * @return List of Case records
     */
    public static List<Case> createForAccountAndContact(Integer count, Id accountId, Id contactId, Boolean doInsert) {
        List<Case> records = new List<Case>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, accountId, contactId));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Case records with a specific Priority
     * @param count Number of records to create
     * @param priority Priority picklist value (Low, Medium, High)
     * @return List of inserted Case records
     */
    public static List<Case> createWithPriority(Integer count, String priority) {
        Account parentAccount = new Account(Name = 'Test Account for ' + priority + ' Priority Cases');
        insert parentAccount;

        List<Case> records = new List<Case>();
        for (Integer i = 0; i < count; i++) {
            Case c = buildRecord(i, parentAccount.Id, null);
            c.Priority = priority;
            records.add(c);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Case records with a specific Status
     * @param count Number of records to create
     * @param status Status picklist value
     * @return List of inserted Case records
     */
    public static List<Case> createWithStatus(Integer count, String status) {
        Account parentAccount = new Account(Name = 'Test Account for ' + status + ' Cases');
        insert parentAccount;

        List<Case> records = new List<Case>();
        for (Integer i = 0; i < count; i++) {
            Case c = buildRecord(i, parentAccount.Id, null);
            c.Status = status;
            records.add(c);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Cases with varied Types for categorization testing
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @return List of inserted Case records with varied types
     */
    public static List<Case> createWithVariedTypes(Integer count, Id accountId) {
        List<String> types = new List<String>{
            'Mechanical', 'Electrical', 'Electronic', 'Structural', 'Other',
            'Feature Request', 'Question', 'Problem'
        };

        List<Case> records = new List<Case>();
        for (Integer i = 0; i < count; i++) {
            Case c = buildRecord(i, accountId, null);
            c.Type = types[Math.mod(i, types.size())];
            records.add(c);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create escalated Cases for escalation rule testing
     * @param count Number of records to create
     * @return List of inserted escalated Case records
     */
    public static List<Case> createEscalated(Integer count) {
        Account parentAccount = new Account(Name = 'Test Account for Escalated Cases');
        insert parentAccount;

        List<Case> records = new List<Case>();
        for (Integer i = 0; i < count; i++) {
            Case c = buildRecord(i, parentAccount.Id, null);
            c.Priority = 'High';
            c.IsEscalated = true;
            records.add(c);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Build a single Case record with default values
     * @param index Record index for unique naming
     * @param accountId Parent Account ID
     * @param contactId Parent Contact ID (optional)
     * @return Case record (not inserted)
     */
    private static Case buildRecord(Integer index, Id accountId, Id contactId) {
        String indexStr = String.valueOf(index).leftPad(5, '0');

        return new Case(
            Subject = DEFAULT_SUBJECT_PREFIX + indexStr,
            AccountId = accountId,
            ContactId = contactId,
            Status = DEFAULT_STATUS,
            Priority = DEFAULT_PRIORITY,
            Origin = DEFAULT_ORIGIN,
            Type = 'Problem',
            Reason = 'User didn\'t attend training',
            Description = 'Test case created by TestDataFactory for automated testing. Case index: ' + index,
            SuppliedName = 'Test Supplied Name ' + index,
            SuppliedEmail = 'supplied' + index + '@testfactory.example.com',
            SuppliedPhone = '(555) 600-' + String.valueOf(1000 + index),
            SuppliedCompany = 'Test Supplied Company ' + index
        );
    }

    /**
     * Get IDs of created records for cleanup
     * @param records List of Case records
     * @return Set of Case IDs
     */
    public static Set<Id> getIds(List<Case> records) {
        Set<Id> ids = new Set<Id>();
        for (Case c : records) {
            if (c.Id != null) {
                ids.add(c.Id);
            }
        }
        return ids;
    }

    /**
     * Delete records by IDs (cleanup utility)
     * @param recordIds Set of Case IDs to delete
     */
    public static void cleanup(Set<Id> recordIds) {
        if (!recordIds.isEmpty()) {
            delete [SELECT Id FROM Case WHERE Id IN :recordIds];
        }
    }
}
