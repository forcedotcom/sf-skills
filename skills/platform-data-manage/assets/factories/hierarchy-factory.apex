/**
 * Test Data Factory for creating complete Account->Contact->Opportunity hierarchies
 * Creates parent-child relationships in a single operation for comprehensive testing
 *
 * Usage:
 *   Map<String, List<SObject>> data = TestDataFactory_Hierarchy.createAccountHierarchy(5, 3, 2);
 *   List<Account> accounts = (List<Account>) data.get('accounts');
 *   List<Contact> contacts = (List<Contact>) data.get('contacts');
 *   List<Opportunity> opportunities = (List<Opportunity>) data.get('opportunities');
 *
 *   // Full hierarchy with Cases and Tasks
 *   Map<String, List<SObject>> fullData = TestDataFactory_Hierarchy.createFullHierarchy(5, 3, 2, 2, 1);
 */
public class TestDataFactory_Hierarchy {

    /**
     * Create Account->Contact->Opportunity hierarchy
     *
     * @param accountCount Number of parent Accounts to create
     * @param contactsPerAccount Number of Contacts per Account
     * @param oppsPerAccount Number of Opportunities per Account
     * @return Map with keys: 'accounts', 'contacts', 'opportunities'
     */
    public static Map<String, List<SObject>> createAccountHierarchy(
        Integer accountCount,
        Integer contactsPerAccount,
        Integer oppsPerAccount
    ) {
        // ═══════════════════════════════════════════════════════════════════
        // Step 1: Create Accounts
        // ═══════════════════════════════════════════════════════════════════
        List<Account> accounts = new List<Account>();
        for (Integer i = 0; i < accountCount; i++) {
            accounts.add(new Account(
                Name = 'Hierarchy Account ' + String.valueOf(i).leftPad(3, '0'),
                Industry = getIndustryForIndex(i),
                Type = 'Prospect',
                BillingCity = 'San Francisco',
                BillingState = 'CA',
                BillingCountry = 'USA',
                Description = 'Parent account for hierarchy testing'
            ));
        }
        insert accounts;

        // ═══════════════════════════════════════════════════════════════════
        // Step 2: Create Contacts for each Account
        // ═══════════════════════════════════════════════════════════════════
        List<Contact> contacts = new List<Contact>();
        Integer contactIndex = 0;

        for (Account acc : accounts) {
            for (Integer i = 0; i < contactsPerAccount; i++) {
                String indexStr = String.valueOf(contactIndex++).leftPad(5, '0');
                contacts.add(new Contact(
                    FirstName = 'Contact',
                    LastName = 'Hierarchy' + indexStr,
                    AccountId = acc.Id,
                    Email = 'contact.hierarchy' + indexStr + '@testfactory.example.com',
                    Phone = '(555) 100-' + String.valueOf(1000 + contactIndex),
                    Title = getTitleForIndex(i),
                    Description = 'Contact for ' + acc.Name
                ));
            }
        }
        if (!contacts.isEmpty()) {
            insert contacts;
        }

        // ═══════════════════════════════════════════════════════════════════
        // Step 3: Create Opportunities for each Account
        // ═══════════════════════════════════════════════════════════════════
        List<Opportunity> opportunities = new List<Opportunity>();
        Integer oppIndex = 0;

        for (Account acc : accounts) {
            for (Integer i = 0; i < oppsPerAccount; i++) {
                String indexStr = String.valueOf(oppIndex++).leftPad(5, '0');
                opportunities.add(new Opportunity(
                    Name = 'Hierarchy Opportunity ' + indexStr,
                    AccountId = acc.Id,
                    StageName = getStageForIndex(i),
                    CloseDate = Date.today().addDays(30 + (i * 7)),
                    Amount = 10000 + (oppIndex * 5000),
                    Type = 'New Customer',
                    LeadSource = 'Web',
                    Description = 'Opportunity for ' + acc.Name
                ));
            }
        }
        if (!opportunities.isEmpty()) {
            insert opportunities;
        }

        // Return all created records
        return new Map<String, List<SObject>>{
            'accounts' => accounts,
            'contacts' => contacts,
            'opportunities' => opportunities
        };
    }

    /**
     * Create full hierarchy including Cases and Tasks
     *
     * @param accountCount Number of parent Accounts
     * @param contactsPerAccount Number of Contacts per Account
     * @param oppsPerAccount Number of Opportunities per Account
     * @param casesPerAccount Number of Cases per Account
     * @param tasksPerContact Number of Tasks per Contact
     * @return Map with keys: 'accounts', 'contacts', 'opportunities', 'cases', 'tasks'
     */
    public static Map<String, List<SObject>> createFullHierarchy(
        Integer accountCount,
        Integer contactsPerAccount,
        Integer oppsPerAccount,
        Integer casesPerAccount,
        Integer tasksPerContact
    ) {
        // Create base hierarchy
        Map<String, List<SObject>> hierarchy = createAccountHierarchy(
            accountCount, contactsPerAccount, oppsPerAccount
        );

        List<Account> accounts = (List<Account>) hierarchy.get('accounts');
        List<Contact> contacts = (List<Contact>) hierarchy.get('contacts');

        // ═══════════════════════════════════════════════════════════════════
        // Step 4: Create Cases for each Account
        // ═══════════════════════════════════════════════════════════════════
        List<Case> cases = new List<Case>();
        Integer caseIndex = 0;

        // Get first contact per account for case contact
        Map<Id, Contact> accountToContact = new Map<Id, Contact>();
        for (Contact con : contacts) {
            if (!accountToContact.containsKey(con.AccountId)) {
                accountToContact.put(con.AccountId, con);
            }
        }

        for (Account acc : accounts) {
            Contact accountContact = accountToContact.get(acc.Id);
            for (Integer i = 0; i < casesPerAccount; i++) {
                String indexStr = String.valueOf(caseIndex++).leftPad(5, '0');
                cases.add(new Case(
                    Subject = 'Hierarchy Case ' + indexStr,
                    AccountId = acc.Id,
                    ContactId = accountContact?.Id,
                    Status = 'New',
                    Priority = getPriorityForIndex(i),
                    Origin = 'Web',
                    Type = 'Problem',
                    Description = 'Case for ' + acc.Name
                ));
            }
        }
        if (!cases.isEmpty()) {
            insert cases;
        }

        // ═══════════════════════════════════════════════════════════════════
        // Step 5: Create Tasks for each Contact
        // ═══════════════════════════════════════════════════════════════════
        List<Task> tasks = new List<Task>();
        Integer taskIndex = 0;

        for (Contact con : contacts) {
            for (Integer i = 0; i < tasksPerContact; i++) {
                String indexStr = String.valueOf(taskIndex++).leftPad(5, '0');
                tasks.add(new Task(
                    Subject = 'Hierarchy Task ' + indexStr,
                    WhoId = con.Id,
                    WhatId = con.AccountId,
                    Status = 'Not Started',
                    Priority = 'Normal',
                    ActivityDate = Date.today().addDays(7 + i),
                    Description = 'Task for ' + con.FirstName + ' ' + con.LastName
                ));
            }
        }
        if (!tasks.isEmpty()) {
            insert tasks;
        }

        // Add new records to hierarchy map
        hierarchy.put('cases', cases);
        hierarchy.put('tasks', tasks);

        return hierarchy;
    }

    /**
     * Create nested Account hierarchy (parent-child accounts)
     *
     * @param rootCount Number of root (top-level) accounts
     * @param levelsDeep Number of child levels (1-4 recommended)
     * @param childrenPerLevel Number of child accounts per parent
     * @return Map with keys: 'level0', 'level1', 'level2', etc.
     */
    public static Map<String, List<Account>> createNestedAccountHierarchy(
        Integer rootCount,
        Integer levelsDeep,
        Integer childrenPerLevel
    ) {
        Map<String, List<Account>> hierarchy = new Map<String, List<Account>>();

        // Create root accounts
        List<Account> rootAccounts = new List<Account>();
        for (Integer i = 0; i < rootCount; i++) {
            rootAccounts.add(new Account(
                Name = 'Root Account ' + String.valueOf(i).leftPad(3, '0'),
                Industry = 'Technology',
                Type = 'Customer',
                Description = 'Root level account'
            ));
        }
        insert rootAccounts;
        hierarchy.put('level0', rootAccounts);

        // Create child levels
        List<Account> parentLevel = rootAccounts;

        for (Integer level = 1; level <= levelsDeep; level++) {
            List<Account> childLevel = new List<Account>();
            Integer childIndex = 0;

            for (Account parent : parentLevel) {
                for (Integer i = 0; i < childrenPerLevel; i++) {
                    childLevel.add(new Account(
                        Name = 'Level' + level + ' Account ' + String.valueOf(childIndex++).leftPad(3, '0'),
                        ParentId = parent.Id,
                        Industry = parent.Industry,
                        Type = 'Customer',
                        Description = 'Child of ' + parent.Name
                    ));
                }
            }

            if (!childLevel.isEmpty()) {
                insert childLevel;
                hierarchy.put('level' + level, childLevel);
                parentLevel = childLevel;
            }
        }

        return hierarchy;
    }

    /**
     * Create bulk test hierarchy for performance/bulkification testing
     * Creates 251+ records to test Salesforce batch boundaries
     *
     * @return Map with keys: 'accounts', 'contacts', 'opportunities'
     */
    public static Map<String, List<SObject>> createBulkTestHierarchy() {
        // 51 accounts x 5 contacts = 255 contacts
        // 51 accounts x 5 opportunities = 255 opportunities
        return createAccountHierarchy(51, 5, 5);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // HELPER METHODS
    // ═══════════════════════════════════════════════════════════════════════

    private static String getIndustryForIndex(Integer index) {
        List<String> industries = new List<String>{
            'Technology', 'Healthcare', 'Finance', 'Manufacturing',
            'Retail', 'Education', 'Energy', 'Media'
        };
        return industries[Math.mod(index, industries.size())];
    }

    private static String getTitleForIndex(Integer index) {
        List<String> titles = new List<String>{
            'CEO', 'CFO', 'CTO', 'VP Sales', 'VP Marketing',
            'Director', 'Manager', 'Senior Developer', 'Analyst'
        };
        return titles[Math.mod(index, titles.size())];
    }

    private static String getStageForIndex(Integer index) {
        List<String> stages = new List<String>{
            'Prospecting', 'Qualification', 'Needs Analysis',
            'Proposal/Price Quote', 'Negotiation/Review'
        };
        return stages[Math.mod(index, stages.size())];
    }

    private static String getPriorityForIndex(Integer index) {
        List<String> priorities = new List<String>{'Low', 'Medium', 'High'};
        return priorities[Math.mod(index, priorities.size())];
    }

    // ═══════════════════════════════════════════════════════════════════════
    // CLEANUP METHODS
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Get all IDs from a hierarchy map
     * @param hierarchy Map returned by create methods
     * @return Set of all record IDs
     */
    public static Map<String, Set<Id>> getAllIds(Map<String, List<SObject>> hierarchy) {
        Map<String, Set<Id>> idsByType = new Map<String, Set<Id>>();

        for (String key : hierarchy.keySet()) {
            Set<Id> ids = new Set<Id>();
            for (SObject record : hierarchy.get(key)) {
                if (record.Id != null) {
                    ids.add(record.Id);
                }
            }
            idsByType.put(key, ids);
        }

        return idsByType;
    }

    /**
     * Delete all records in a hierarchy (in correct order)
     * Deletes children before parents to avoid referential integrity errors
     *
     * @param hierarchy Map returned by create methods
     */
    public static void cleanup(Map<String, List<SObject>> hierarchy) {
        // Delete in reverse dependency order
        List<String> deleteOrder = new List<String>{
            'tasks', 'events', 'cases', 'opportunities', 'contacts', 'accounts'
        };

        for (String key : deleteOrder) {
            if (hierarchy.containsKey(key)) {
                List<SObject> records = hierarchy.get(key);
                if (!records.isEmpty()) {
                    try {
                        delete records;
                    } catch (DmlException e) {
                        System.debug('Cleanup error for ' + key + ': ' + e.getMessage());
                    }
                }
            }
        }
    }

    /**
     * Delete nested account hierarchy (in correct order - leaves first)
     *
     * @param hierarchy Map returned by createNestedAccountHierarchy
     */
    public static void cleanupNestedHierarchy(Map<String, List<Account>> hierarchy) {
        // Find max level
        Integer maxLevel = 0;
        for (String key : hierarchy.keySet()) {
            if (key.startsWith('level')) {
                Integer level = Integer.valueOf(key.replace('level', ''));
                maxLevel = Math.max(maxLevel, level);
            }
        }

        // Delete from deepest level up
        for (Integer level = maxLevel; level >= 0; level--) {
            String key = 'level' + level;
            if (hierarchy.containsKey(key)) {
                List<Account> accounts = hierarchy.get(key);
                if (!accounts.isEmpty()) {
                    delete accounts;
                }
            }
        }
    }
}
