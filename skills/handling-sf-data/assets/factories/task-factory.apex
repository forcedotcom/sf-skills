/**
 * Test Data Factory for Task records
 * Supports bulk creation with polymorphic Who/What relationships
 *
 * Usage:
 *   List<Task> tasks = TestDataFactory_Task.create(200);
 *   List<Task> tasksForContact = TestDataFactory_Task.createForWho(50, contactId);
 *   List<Task> tasksForAccount = TestDataFactory_Task.createForWhat(50, accountId);
 */
public class TestDataFactory_Task {

    private static final String DEFAULT_SUBJECT_PREFIX = 'Test Task ';
    private static final String DEFAULT_STATUS = 'Not Started';
    private static final String DEFAULT_PRIORITY = 'Normal';

    /**
     * Create and insert Task records (creates related Contact automatically)
     * @param count Number of records to create
     * @return List of inserted Task records with IDs
     */
    public static List<Task> create(Integer count) {
        return create(count, true);
    }

    /**
     * Create Task records with insert option
     * @param count Number of records to create
     * @param doInsert Whether to insert records
     * @return List of Task records
     */
    public static List<Task> create(Integer count, Boolean doInsert) {
        // Create parent Account and Contact for Who field
        Account parentAccount = new Account(Name = 'Test Parent Account for Tasks');
        insert parentAccount;

        Contact parentContact = new Contact(
            FirstName = 'Test',
            LastName = 'TaskContact',
            AccountId = parentAccount.Id
        );
        insert parentContact;

        List<Task> records = new List<Task>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, parentContact.Id, parentAccount.Id));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Task records for a specific Who (Contact or Lead)
     * @param count Number of records to create
     * @param whoId Contact or Lead ID for the Who field
     * @return List of inserted Task records
     */
    public static List<Task> createForWho(Integer count, Id whoId) {
        return createForWho(count, whoId, true);
    }

    /**
     * Create Task records for a specific Who with insert option
     * @param count Number of records to create
     * @param whoId Contact or Lead ID
     * @param doInsert Whether to insert records
     * @return List of Task records
     */
    public static List<Task> createForWho(Integer count, Id whoId, Boolean doInsert) {
        List<Task> records = new List<Task>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, whoId, null));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Task records for a specific What (Account, Opportunity, Case, etc.)
     * @param count Number of records to create
     * @param whatId Account, Opportunity, or Case ID
     * @return List of inserted Task records
     */
    public static List<Task> createForWhat(Integer count, Id whatId) {
        return createForWhat(count, whatId, true);
    }

    /**
     * Create Task records for a specific What with insert option
     * @param count Number of records to create
     * @param whatId Account, Opportunity, or Case ID
     * @param doInsert Whether to insert records
     * @return List of Task records
     */
    public static List<Task> createForWhat(Integer count, Id whatId, Boolean doInsert) {
        List<Task> records = new List<Task>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, null, whatId));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Task records for both Who and What
     * @param count Number of records to create
     * @param whoId Contact or Lead ID
     * @param whatId Account, Opportunity, or Case ID
     * @return List of inserted Task records
     */
    public static List<Task> createForWhoAndWhat(Integer count, Id whoId, Id whatId) {
        List<Task> records = new List<Task>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, whoId, whatId));
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Tasks with a specific Status
     * @param count Number of records to create
     * @param status Task Status picklist value
     * @return List of inserted Task records
     */
    public static List<Task> createWithStatus(Integer count, String status) {
        Account parentAccount = new Account(Name = 'Test Account for ' + status + ' Tasks');
        insert parentAccount;

        List<Task> records = new List<Task>();
        for (Integer i = 0; i < count; i++) {
            Task t = buildRecord(i, null, parentAccount.Id);
            t.Status = status;
            records.add(t);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create completed Tasks for history testing
     * @param count Number of records to create
     * @return List of inserted completed Task records
     */
    public static List<Task> createCompleted(Integer count) {
        Account parentAccount = new Account(Name = 'Test Account for Completed Tasks');
        insert parentAccount;

        List<Task> records = new List<Task>();
        for (Integer i = 0; i < count; i++) {
            Task t = buildRecord(i, null, parentAccount.Id);
            t.Status = 'Completed';
            t.Priority = 'Normal';
            records.add(t);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Tasks with varied Subjects for search testing
     * @param count Number of records to create
     * @return List of inserted Task records with varied subjects
     */
    public static List<Task> createWithVariedSubjects(Integer count) {
        List<String> subjects = new List<String>{
            'Call', 'Email', 'Meeting', 'Send Letter', 'Send Quote',
            'Follow Up', 'Demo', 'Proposal', 'Contract Review', 'Other'
        };

        Account parentAccount = new Account(Name = 'Test Account for Varied Tasks');
        insert parentAccount;

        List<Task> records = new List<Task>();
        for (Integer i = 0; i < count; i++) {
            Task t = buildRecord(i, null, parentAccount.Id);
            t.Subject = subjects[Math.mod(i, subjects.size())];
            records.add(t);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Build a single Task record with default values
     * @param index Record index for unique naming
     * @param whoId Contact or Lead ID (optional)
     * @param whatId Account, Opportunity, or Case ID (optional)
     * @return Task record (not inserted)
     */
    private static Task buildRecord(Integer index, Id whoId, Id whatId) {
        String indexStr = String.valueOf(index).leftPad(5, '0');

        return new Task(
            Subject = DEFAULT_SUBJECT_PREFIX + indexStr,
            WhoId = whoId,
            WhatId = whatId,
            Status = DEFAULT_STATUS,
            Priority = DEFAULT_PRIORITY,
            ActivityDate = Date.today().addDays(7 + index),
            Description = 'Test task created by TestDataFactory for automated testing. Task index: ' + index,
            Type = 'Call',
            IsReminderSet = false,
            TaskSubtype = 'Task'
        );
    }

    /**
     * Get IDs of created records for cleanup
     * @param records List of Task records
     * @return Set of Task IDs
     */
    public static Set<Id> getIds(List<Task> records) {
        Set<Id> ids = new Set<Id>();
        for (Task t : records) {
            if (t.Id != null) {
                ids.add(t.Id);
            }
        }
        return ids;
    }

    /**
     * Delete records by IDs (cleanup utility)
     * @param recordIds Set of Task IDs to delete
     */
    public static void cleanup(Set<Id> recordIds) {
        if (!recordIds.isEmpty()) {
            delete [SELECT Id FROM Task WHERE Id IN :recordIds];
        }
    }
}
