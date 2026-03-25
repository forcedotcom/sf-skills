/**
 * Test Data Factory for creating consistent test data across all test classes.
 *              Use this pattern to avoid hardcoded test data and ensure test isolation.
 *
 * USAGE:
 *   List<Account> accounts = TestDataFactory.createAccounts(5);
 *   insert accounts;
 *
 *   // Or with auto-insert:
 *   List<Account> accounts = TestDataFactory.createAndInsertAccounts(5);
 */
@IsTest
public class TestDataFactory {

    // ═══════════════════════════════════════════════════════════════════════════
    // ACCOUNT METHODS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Creates Account records without inserting
     * @param count Number of accounts to create
     * @return List of Account records (not inserted)
     */
    public static List<Account> createAccounts(Integer count) {
        List<Account> accounts = new List<Account>();
        for (Integer i = 0; i < count; i++) {
            accounts.add(new Account(
                Name = 'Test Account ' + i,
                Industry = 'Technology',
                BillingStreet = '123 Test Street',
                BillingCity = 'San Francisco',
                BillingState = 'CA',
                BillingPostalCode = '94105',
                BillingCountry = 'USA',
                Phone = '555-000-' + String.valueOf(i).leftPad(4, '0'),
                Website = 'https://testaccount' + i + '.example.com'
            ));
        }
        return accounts;
    }

    /**
     * Creates and inserts Account records
     * @param count Number of accounts to create
     * @return List of inserted Account records
     */
    public static List<Account> createAndInsertAccounts(Integer count) {
        List<Account> accounts = createAccounts(count);
        insert accounts;
        return accounts;
    }

    /**
     * Creates Account with specific attributes
     * @param name Account name
     * @param industry Industry value
     * @return Account record (not inserted)
     */
    public static Account createAccount(String name, String industry) {
        return new Account(
            Name = name,
            Industry = industry,
            BillingCity = 'San Francisco',
            BillingState = 'CA',
            BillingCountry = 'USA'
        );
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CONTACT METHODS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Creates Contact records without inserting
     * @param count Number of contacts to create
     * @param accountId Parent account ID
     * @return List of Contact records (not inserted)
     */
    public static List<Contact> createContacts(Integer count, Id accountId) {
        List<Contact> contacts = new List<Contact>();
        for (Integer i = 0; i < count; i++) {
            contacts.add(new Contact(
                FirstName = 'Test',
                LastName = 'Contact ' + i,
                AccountId = accountId,
                Email = 'testcontact' + i + '@example.com',
                Phone = '555-001-' + String.valueOf(i).leftPad(4, '0'),
                Title = 'Test Title ' + i,
                MailingStreet = '456 Test Ave',
                MailingCity = 'San Francisco',
                MailingState = 'CA',
                MailingPostalCode = '94105',
                MailingCountry = 'USA'
            ));
        }
        return contacts;
    }

    /**
     * Creates and inserts Contact records
     * @param count Number of contacts to create
     * @param accountId Parent account ID
     * @return List of inserted Contact records
     */
    public static List<Contact> createAndInsertContacts(Integer count, Id accountId) {
        List<Contact> contacts = createContacts(count, accountId);
        insert contacts;
        return contacts;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // LEAD METHODS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Creates Lead records without inserting
     * @param count Number of leads to create
     * @return List of Lead records (not inserted)
     */
    public static List<Lead> createLeads(Integer count) {
        List<Lead> leads = new List<Lead>();
        for (Integer i = 0; i < count; i++) {
            leads.add(new Lead(
                FirstName = 'Test',
                LastName = 'Lead ' + i,
                Company = 'Test Company ' + i,
                Email = 'testlead' + i + '@example.com',
                Phone = '555-002-' + String.valueOf(i).leftPad(4, '0'),
                Status = 'Open - Not Contacted',
                Industry = 'Technology',
                LeadSource = 'Web'
            ));
        }
        return leads;
    }

    /**
     * Creates and inserts Lead records
     * @param count Number of leads to create
     * @return List of inserted Lead records
     */
    public static List<Lead> createAndInsertLeads(Integer count) {
        List<Lead> leads = createLeads(count);
        insert leads;
        return leads;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // OPPORTUNITY METHODS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Creates Opportunity records without inserting
     * @param count Number of opportunities to create
     * @param accountId Parent account ID
     * @return List of Opportunity records (not inserted)
     */
    public static List<Opportunity> createOpportunities(Integer count, Id accountId) {
        List<Opportunity> opportunities = new List<Opportunity>();
        for (Integer i = 0; i < count; i++) {
            opportunities.add(new Opportunity(
                Name = 'Test Opportunity ' + i,
                AccountId = accountId,
                StageName = 'Prospecting',
                CloseDate = Date.today().addDays(30 + i),
                Amount = 10000 * (i + 1)
            ));
        }
        return opportunities;
    }

    /**
     * Creates and inserts Opportunity records
     * @param count Number of opportunities to create
     * @param accountId Parent account ID
     * @return List of inserted Opportunity records
     */
    public static List<Opportunity> createAndInsertOpportunities(Integer count, Id accountId) {
        List<Opportunity> opportunities = createOpportunities(count, accountId);
        insert opportunities;
        return opportunities;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CASE METHODS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Creates Case records without inserting
     * @param count Number of cases to create
     * @param accountId Parent account ID (optional)
     * @param contactId Related contact ID (optional)
     * @return List of Case records (not inserted)
     */
    public static List<Case> createCases(Integer count, Id accountId, Id contactId) {
        List<Case> cases = new List<Case>();
        for (Integer i = 0; i < count; i++) {
            cases.add(new Case(
                Subject = 'Test Case ' + i,
                Description = 'Test case description ' + i,
                Status = 'New',
                Priority = 'Medium',
                Origin = 'Web',
                AccountId = accountId,
                ContactId = contactId
            ));
        }
        return cases;
    }

    /**
     * Creates and inserts Case records
     * @param count Number of cases to create
     * @param accountId Parent account ID (optional)
     * @param contactId Related contact ID (optional)
     * @return List of inserted Case records
     */
    public static List<Case> createAndInsertCases(Integer count, Id accountId, Id contactId) {
        List<Case> cases = createCases(count, accountId, contactId);
        insert cases;
        return cases;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // USER METHODS (for System.runAs testing)
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Creates a test User with specified profile
     *              Use with System.runAs() for permission testing
     * @param profileName Name of the profile to assign
     * @param uniqueIdentifier Unique string to avoid duplicate usernames
     * @return User record (not inserted)
     */
    public static User createUser(String profileName, String uniqueIdentifier) {
        Profile p = [SELECT Id FROM Profile WHERE Name = :profileName LIMIT 1];

        String uniqueEmail = uniqueIdentifier + '@testuser.example.com';
        String uniqueUsername = uniqueIdentifier + '@testuser.example.com.test';

        return new User(
            FirstName = 'Test',
            LastName = 'User ' + uniqueIdentifier,
            Email = uniqueEmail,
            Username = uniqueUsername,
            Alias = uniqueIdentifier.left(8),
            ProfileId = p.Id,
            TimeZoneSidKey = 'America/Los_Angeles',
            LocaleSidKey = 'en_US',
            EmailEncodingKey = 'UTF-8',
            LanguageLocaleKey = 'en_US'
        );
    }

    /**
     * Creates and inserts a test User
     * @param profileName Name of the profile to assign
     * @param uniqueIdentifier Unique string to avoid duplicate usernames
     * @return Inserted User record
     */
    public static User createAndInsertUser(String profileName, String uniqueIdentifier) {
        User u = createUser(profileName, uniqueIdentifier);
        insert u;
        return u;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CUSTOM OBJECT METHODS (Template)
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Template for custom object creation
     *              Copy and modify for your custom objects
     * @param count Number of records to create
     * @return List of custom object records (not inserted)
     */
    /*
    public static List<Custom_Object__c> createCustomObjects(Integer count) {
        List<Custom_Object__c> records = new List<Custom_Object__c>();
        for (Integer i = 0; i < count; i++) {
            records.add(new Custom_Object__c(
                Name = 'Test Record ' + i,
                Custom_Field__c = 'Value ' + i
                // Add more fields as needed
            ));
        }
        return records;
    }

    public static List<Custom_Object__c> createAndInsertCustomObjects(Integer count) {
        List<Custom_Object__c> records = createCustomObjects(count);
        insert records;
        return records;
    }
    */

    // ═══════════════════════════════════════════════════════════════════════════
    // UTILITY METHODS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Generates a unique string for test data
     *              Useful for avoiding unique constraint violations
     * @return Unique string based on timestamp
     */
    public static String generateUniqueString() {
        return String.valueOf(Datetime.now().getTime()) +
               String.valueOf(Math.random()).substring(2, 8);
    }

    /**
     * Creates a map of records by a specified field
     *              Useful for test assertions
     * @param records List of SObjects
     * @param fieldName API name of the field to use as key
     * @return Map with field values as keys
     */
    public static Map<String, SObject> createMapByField(List<SObject> records, String fieldName) {
        Map<String, SObject> recordMap = new Map<String, SObject>();
        for (SObject record : records) {
            String keyValue = String.valueOf(record.get(fieldName));
            recordMap.put(keyValue, record);
        }
        return recordMap;
    }
}
