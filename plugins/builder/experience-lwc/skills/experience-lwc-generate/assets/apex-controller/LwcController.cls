/**
 * APEX CONTROLLER TEMPLATE FOR LWC
 *
 * This template demonstrates @AuraEnabled methods for LWC with:
 * - Cacheable methods for wire service
 * - Non-cacheable methods for data mutations
 * - Proper error handling
 * - Security enforcement
 * - Bulk-safe patterns
 *
 * Replace: LwcController → YourControllerName
 */
public with sharing class LwcController {

    // ═══════════════════════════════════════════════════════════════════════
    // CACHEABLE METHODS (For @wire service)
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Get records for display in LWC
     * Use with @wire decorator for automatic caching and refresh
     *
     * @param parentId - Parent record ID (optional filter)
     * @param searchTerm - Search filter (optional)
     * @param limitSize - Max records to return
     * @return List of Account records
     */
    @AuraEnabled(cacheable=true)
    public static List<Account> getAccounts(Id parentId, String searchTerm, Integer limitSize) {
        try {
            Integer recordLimit = limitSize != null ? limitSize : 50;
            String searchKey = String.isNotBlank(searchTerm)
                ? '%' + String.escapeSingleQuotes(searchTerm) + '%'
                : '%';

            return [
                SELECT Id, Name, Industry, AnnualRevenue, Phone, CreatedDate
                FROM Account
                WHERE Name LIKE :searchKey
                WITH SECURITY_ENFORCED
                ORDER BY Name
                LIMIT :recordLimit
            ];
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    /**
     * Get single record by ID
     */
    @AuraEnabled(cacheable=true)
    public static Account getAccountById(Id accountId) {
        try {
            List<Account> accounts = [
                SELECT Id, Name, Industry, AnnualRevenue, Phone, BillingAddress,
                       (SELECT Id, FirstName, LastName, Email FROM Contacts LIMIT 5)
                FROM Account
                WHERE Id = :accountId
                WITH SECURITY_ENFORCED
                LIMIT 1
            ];

            if (accounts.isEmpty()) {
                throw new AuraHandledException('Account not found');
            }

            return accounts[0];
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    /**
     * Get picklist values for a field
     */
    @AuraEnabled(cacheable=true)
    public static List<PicklistOption> getIndustryOptions() {
        List<PicklistOption> options = new List<PicklistOption>();

        Schema.DescribeFieldResult fieldResult = Account.Industry.getDescribe();
        List<Schema.PicklistEntry> entries = fieldResult.getPicklistValues();

        for (Schema.PicklistEntry entry : entries) {
            if (entry.isActive()) {
                options.add(new PicklistOption(entry.getLabel(), entry.getValue()));
            }
        }

        return options;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // NON-CACHEABLE METHODS (For data mutations)
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Create a new account
     *
     * @param accountData - JSON string of account fields
     * @return Created Account with Id
     */
    @AuraEnabled
    public static Account createAccount(String accountData) {
        try {
            // Parse JSON to Map
            Map<String, Object> fieldMap = (Map<String, Object>) JSON.deserializeUntyped(accountData);

            // Create Account record
            Account newAccount = new Account();
            newAccount.Name = (String) fieldMap.get('Name');
            newAccount.Industry = (String) fieldMap.get('Industry');
            newAccount.Phone = (String) fieldMap.get('Phone');

            // Validate required fields
            if (String.isBlank(newAccount.Name)) {
                throw new AuraHandledException('Account name is required');
            }

            // Insert with security check
            SObjectAccessDecision decision = Security.stripInaccessible(
                AccessType.CREATABLE,
                new List<Account>{ newAccount }
            );
            insert decision.getRecords();

            return (Account) decision.getRecords()[0];
        } catch (DmlException e) {
            throw new AuraHandledException(e.getDmlMessage(0));
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    /**
     * Update an existing account
     *
     * @param accountId - Record ID to update
     * @param accountData - JSON string of fields to update
     * @return Updated Account
     */
    @AuraEnabled
    public static Account updateAccount(Id accountId, String accountData) {
        try {
            // Verify record exists and user has access
            List<Account> existing = [
                SELECT Id FROM Account
                WHERE Id = :accountId
                WITH SECURITY_ENFORCED
                LIMIT 1
            ];

            if (existing.isEmpty()) {
                throw new AuraHandledException('Account not found or access denied');
            }

            // Parse and apply updates
            Map<String, Object> fieldMap = (Map<String, Object>) JSON.deserializeUntyped(accountData);

            Account accountToUpdate = new Account(Id = accountId);

            if (fieldMap.containsKey('Name')) {
                accountToUpdate.Name = (String) fieldMap.get('Name');
            }
            if (fieldMap.containsKey('Industry')) {
                accountToUpdate.Industry = (String) fieldMap.get('Industry');
            }
            if (fieldMap.containsKey('Phone')) {
                accountToUpdate.Phone = (String) fieldMap.get('Phone');
            }

            // Update with security check
            SObjectAccessDecision decision = Security.stripInaccessible(
                AccessType.UPDATABLE,
                new List<Account>{ accountToUpdate }
            );
            update decision.getRecords();

            // Return refreshed record
            return getAccountById(accountId);
        } catch (DmlException e) {
            throw new AuraHandledException(e.getDmlMessage(0));
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    /**
     * Delete records
     *
     * @param recordIds - List of record IDs to delete
     */
    @AuraEnabled
    public static void deleteAccounts(List<Id> recordIds) {
        try {
            if (recordIds == null || recordIds.isEmpty()) {
                throw new AuraHandledException('No records specified for deletion');
            }

            // Query records to verify access
            List<Account> accountsToDelete = [
                SELECT Id FROM Account
                WHERE Id IN :recordIds
                WITH SECURITY_ENFORCED
            ];

            if (accountsToDelete.size() != recordIds.size()) {
                throw new AuraHandledException('Some records not found or access denied');
            }

            delete accountsToDelete;
        } catch (DmlException e) {
            throw new AuraHandledException(e.getDmlMessage(0));
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    /**
     * Bulk update records (for datatable inline editing)
     *
     * @param records - List of records with Id and fields to update
     */
    @AuraEnabled
    public static void updateRecords(List<Account> records) {
        try {
            if (records == null || records.isEmpty()) {
                return;
            }

            // Security check
            SObjectAccessDecision decision = Security.stripInaccessible(
                AccessType.UPDATABLE,
                records
            );

            update decision.getRecords();
        } catch (DmlException e) {
            throw new AuraHandledException(e.getDmlMessage(0));
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // PAGINATED QUERY (For infinite scrolling)
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Get paginated records for infinite scrolling
     *
     * @param limitSize - Records per page
     * @param offset - Starting position
     * @param sortBy - Field to sort by
     * @param sortDirection - ASC or DESC
     * @return PagedResult with records and total count
     */
    @AuraEnabled(cacheable=true)
    public static PagedResult getPagedAccounts(
        Integer limitSize,
        Integer offset,
        String sortBy,
        String sortDirection
    ) {
        try {
            Integer recordLimit = limitSize != null ? limitSize : 50;
            Integer recordOffset = offset != null ? offset : 0;
            String sortField = String.isNotBlank(sortBy) ? sortBy : 'Name';
            String sortDir = sortDirection == 'desc' ? 'DESC' : 'ASC';

            // Whitelist allowed sort fields to prevent SOQL injection
            Set<String> allowedSortFields = new Set<String>{
                'Name', 'Industry', 'AnnualRevenue', 'CreatedDate', 'Phone'
            };

            if (!allowedSortFields.contains(sortField)) {
                sortField = 'Name';
            }

            // Build dynamic query
            String query = 'SELECT Id, Name, Industry, AnnualRevenue, Phone, CreatedDate ' +
                          'FROM Account ' +
                          'WITH SECURITY_ENFORCED ' +
                          'ORDER BY ' + sortField + ' ' + sortDir + ' NULLS LAST ' +
                          'LIMIT :recordLimit OFFSET :recordOffset';

            List<Account> records = Database.query(query);

            // Get total count
            Integer totalCount = [SELECT COUNT() FROM Account WITH SECURITY_ENFORCED];

            return new PagedResult(records, totalCount);
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // WRAPPER CLASSES
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Wrapper for picklist options
     */
    public class PicklistOption {
        @AuraEnabled public String label;
        @AuraEnabled public String value;

        public PicklistOption(String label, String value) {
            this.label = label;
            this.value = value;
        }
    }

    /**
     * Wrapper for paginated results
     */
    public class PagedResult {
        @AuraEnabled public List<Account> records;
        @AuraEnabled public Integer totalCount;

        public PagedResult(List<Account> records, Integer totalCount) {
            this.records = records;
            this.totalCount = totalCount;
        }
    }
}
