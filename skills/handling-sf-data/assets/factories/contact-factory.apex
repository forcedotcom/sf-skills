/**
 * Test Data Factory for Contact records
 * Supports bulk creation with Account relationships
 *
 * Usage:
 *   List<Contact> contacts = TestDataFactory_Contact.create(200);
 *   List<Contact> contactsForAccount = TestDataFactory_Contact.createForAccount(50, accountId);
 *   List<Contact> contactsNoInsert = TestDataFactory_Contact.create(200, false);
 */
public class TestDataFactory_Contact {

    private static final String DEFAULT_FIRST_NAME_PREFIX = 'Test';
    private static final String DEFAULT_LAST_NAME_PREFIX = 'Contact';
    private static final String DEFAULT_EMAIL_DOMAIN = 'testfactory.example.com';

    /**
     * Create and insert Contact records (creates parent Account automatically)
     * @param count Number of records to create
     * @return List of inserted Contact records with IDs
     */
    public static List<Contact> create(Integer count) {
        return create(count, true);
    }

    /**
     * Create Contact records with insert option
     * @param count Number of records to create
     * @param doInsert Whether to insert records
     * @return List of Contact records
     */
    public static List<Contact> create(Integer count, Boolean doInsert) {
        // Create a parent Account for orphan protection
        Account parentAccount = new Account(Name = 'Test Parent Account for Contacts');
        insert parentAccount;

        return createForAccount(count, parentAccount.Id, doInsert);
    }

    /**
     * Create Contact records for a specific Account
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @return List of inserted Contact records
     */
    public static List<Contact> createForAccount(Integer count, Id accountId) {
        return createForAccount(count, accountId, true);
    }

    /**
     * Create Contact records for a specific Account with insert option
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @param doInsert Whether to insert records
     * @return List of Contact records
     */
    public static List<Contact> createForAccount(Integer count, Id accountId, Boolean doInsert) {
        List<Contact> records = new List<Contact>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, accountId));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Contacts distributed across multiple Accounts
     * @param accountIds List of Account IDs
     * @param contactsPerAccount Number of Contacts per Account
     * @return List of inserted Contact records
     */
    public static List<Contact> createForAccounts(List<Id> accountIds, Integer contactsPerAccount) {
        List<Contact> records = new List<Contact>();
        Integer globalIndex = 0;

        for (Id accountId : accountIds) {
            for (Integer i = 0; i < contactsPerAccount; i++) {
                records.add(buildRecord(globalIndex++, accountId));
            }
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Contacts with varied titles for role-based testing
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @return List of inserted Contact records with varied titles
     */
    public static List<Contact> createWithVariedTitles(Integer count, Id accountId) {
        List<String> titles = new List<String>{
            'CEO', 'CFO', 'CTO', 'VP Sales', 'VP Marketing',
            'Director', 'Manager', 'Senior Developer', 'Analyst', 'Consultant'
        };

        List<Contact> records = new List<Contact>();
        for (Integer i = 0; i < count; i++) {
            Contact con = buildRecord(i, accountId);
            con.Title = titles[Math.mod(i, titles.size())];
            records.add(con);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Build a single Contact record with default values
     * @param index Record index for unique naming
     * @param accountId Parent Account ID
     * @return Contact record (not inserted)
     */
    private static Contact buildRecord(Integer index, Id accountId) {
        String indexStr = String.valueOf(index).leftPad(5, '0');
        String firstName = DEFAULT_FIRST_NAME_PREFIX + indexStr;
        String lastName = DEFAULT_LAST_NAME_PREFIX + indexStr;

        return new Contact(
            FirstName = firstName,
            LastName = lastName,
            AccountId = accountId,
            Email = firstName.toLowerCase() + '.' + lastName.toLowerCase() + '@' + DEFAULT_EMAIL_DOMAIN,
            Phone = '(555) 200-' + String.valueOf(1000 + index),
            MobilePhone = '(555) 300-' + String.valueOf(1000 + index),
            Title = 'Test Title',
            Department = 'Test Department',
            MailingStreet = '456 Contact Ave',
            MailingCity = 'San Francisco',
            MailingState = 'CA',
            MailingPostalCode = '94103',
            MailingCountry = 'USA',
            Birthdate = Date.today().addYears(-30).addDays(index),
            Description = 'Test contact created by TestDataFactory for automated testing'
        );
    }

    /**
     * Get IDs of created records for cleanup
     * @param records List of Contact records
     * @return Set of Contact IDs
     */
    public static Set<Id> getIds(List<Contact> records) {
        Set<Id> ids = new Set<Id>();
        for (Contact con : records) {
            if (con.Id != null) {
                ids.add(con.Id);
            }
        }
        return ids;
    }

    /**
     * Delete records by IDs (cleanup utility)
     * @param recordIds Set of Contact IDs to delete
     */
    public static void cleanup(Set<Id> recordIds) {
        if (!recordIds.isEmpty()) {
            delete [SELECT Id FROM Contact WHERE Id IN :recordIds];
        }
    }
}
