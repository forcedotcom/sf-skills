/**
 * Test Data Factory for Account records
 * Supports bulk creation with configurable field values
 *
 * Usage:
 *   List<Account> accounts = TestDataFactory_Account.create(200);
 *   List<Account> accountsNoInsert = TestDataFactory_Account.create(200, false);
 *   List<Account> customAccounts = TestDataFactory_Account.createWithIndustry(50, 'Healthcare');
 */
public class TestDataFactory_Account {

    private static final String DEFAULT_NAME_PREFIX = 'Test Account ';
    private static final String DEFAULT_INDUSTRY = 'Technology';
    private static final String DEFAULT_TYPE = 'Prospect';

    /**
     * Create and insert Account records with default values
     * @param count Number of records to create
     * @return List of inserted Account records with IDs
     */
    public static List<Account> create(Integer count) {
        return create(count, true);
    }

    /**
     * Create Account records with insert option
     * @param count Number of records to create
     * @param doInsert Whether to insert records (true) or return without inserting (false)
     * @return List of Account records
     */
    public static List<Account> create(Integer count, Boolean doInsert) {
        List<Account> records = new List<Account>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Account records with specific Industry
     * @param count Number of records to create
     * @param industry Industry picklist value
     * @return List of inserted Account records
     */
    public static List<Account> createWithIndustry(Integer count, String industry) {
        List<Account> records = new List<Account>();
        for (Integer i = 0; i < count; i++) {
            Account acc = buildRecord(i);
            acc.Industry = industry;
            records.add(acc);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Account records with varying Industries for comprehensive testing
     * Distributes records across multiple Industry values
     * @param count Number of records to create
     * @return List of inserted Account records with varied Industries
     */
    public static List<Account> createWithVariedIndustries(Integer count) {
        List<String> industries = new List<String>{
            'Technology', 'Healthcare', 'Finance', 'Manufacturing',
            'Retail', 'Education', 'Energy', 'Media'
        };

        List<Account> records = new List<Account>();
        for (Integer i = 0; i < count; i++) {
            Account acc = buildRecord(i);
            acc.Industry = industries[Math.mod(i, industries.size())];
            records.add(acc);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Account hierarchy (parent-child accounts)
     * @param parentCount Number of parent accounts
     * @param childrenPerParent Number of child accounts per parent
     * @return Map with 'parents' and 'children' lists
     */
    public static Map<String, List<Account>> createHierarchy(Integer parentCount, Integer childrenPerParent) {
        // Create parent accounts
        List<Account> parents = create(parentCount);

        // Create child accounts
        List<Account> children = new List<Account>();
        for (Account parent : parents) {
            for (Integer i = 0; i < childrenPerParent; i++) {
                Account child = new Account(
                    Name = parent.Name + ' - Child ' + i,
                    ParentId = parent.Id,
                    Industry = parent.Industry,
                    Type = 'Customer'
                );
                children.add(child);
            }
        }
        if (!children.isEmpty()) {
            insert children;
        }

        return new Map<String, List<Account>>{
            'parents' => parents,
            'children' => children
        };
    }

    /**
     * Build a single Account record with default values
     * @param index Record index for unique naming
     * @return Account record (not inserted)
     */
    private static Account buildRecord(Integer index) {
        return new Account(
            Name = DEFAULT_NAME_PREFIX + String.valueOf(index).leftPad(5, '0'),
            Industry = DEFAULT_INDUSTRY,
            Type = DEFAULT_TYPE,
            BillingStreet = '123 Test Street',
            BillingCity = 'San Francisco',
            BillingState = 'CA',
            BillingPostalCode = '94102',
            BillingCountry = 'USA',
            Phone = '(555) 123-' + String.valueOf(1000 + index),
            Website = 'https://testaccount' + index + '.example.com',
            NumberOfEmployees = 100 + (index * 10),
            AnnualRevenue = 1000000 + (index * 50000),
            Description = 'Test account created by TestDataFactory for automated testing'
        );
    }

    /**
     * Get IDs of created records for cleanup
     * @param records List of Account records
     * @return Set of Account IDs
     */
    public static Set<Id> getIds(List<Account> records) {
        Set<Id> ids = new Set<Id>();
        for (Account acc : records) {
            if (acc.Id != null) {
                ids.add(acc.Id);
            }
        }
        return ids;
    }

    /**
     * Delete records by IDs (cleanup utility)
     * @param recordIds Set of Account IDs to delete
     */
    public static void cleanup(Set<Id> recordIds) {
        if (!recordIds.isEmpty()) {
            delete [SELECT Id FROM Account WHERE Id IN :recordIds];
        }
    }
}
