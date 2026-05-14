/**
 * Test Data Factory Template for Custom Objects
 *
 * INSTRUCTIONS:
 * 1. Copy this file and rename to TestDataFactory_[YourObject].cls
 * 2. Replace {{ObjectName}} with your object API name (e.g., Invoice__c)
 * 3. Replace {{ObjectLabel}} with display name (e.g., Invoice)
 * 4. Update buildRecord() with your object's fields
 * 5. Add object-specific creation methods as needed
 *
 * Usage:
 *   List<{{ObjectName}}> records = TestDataFactory_{{ObjectLabel}}.create(200);
 *   List<{{ObjectName}}> recordsNoInsert = TestDataFactory_{{ObjectLabel}}.create(200, false);
 */
public class TestDataFactory_{{ObjectLabel}} {

    // ═══════════════════════════════════════════════════════════════════════
    // CONFIGURATION - Update these for your object
    // ═══════════════════════════════════════════════════════════════════════

    private static final String DEFAULT_NAME_PREFIX = 'Test {{ObjectLabel}} ';

    // Add default values for required picklist fields
    // private static final String DEFAULT_STATUS = 'Draft';
    // private static final String DEFAULT_TYPE = 'Standard';

    // ═══════════════════════════════════════════════════════════════════════
    // STANDARD FACTORY METHODS
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Create and insert records with default values
     * @param count Number of records to create
     * @return List of inserted records with IDs
     */
    public static List<{{ObjectName}}> create(Integer count) {
        return create(count, true);
    }

    /**
     * Create records with insert option
     * @param count Number of records to create
     * @param doInsert Whether to insert records
     * @return List of records
     */
    public static List<{{ObjectName}}> create(Integer count, Boolean doInsert) {
        List<{{ObjectName}}> records = new List<{{ObjectName}}>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // RELATIONSHIP METHODS - Uncomment and modify if object has lookups
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Create records for a specific parent Account
     * Uncomment if your object has an Account lookup
     */
    /*
    public static List<{{ObjectName}}> createForAccount(Integer count, Id accountId) {
        return createForAccount(count, accountId, true);
    }

    public static List<{{ObjectName}}> createForAccount(Integer count, Id accountId, Boolean doInsert) {
        List<{{ObjectName}}> records = new List<{{ObjectName}}>();
        for (Integer i = 0; i < count; i++) {
            {{ObjectName}} record = buildRecord(i);
            record.Account__c = accountId;  // Update with your lookup field API name
            records.add(record);
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }
    */

    /**
     * Create records for a specific parent (generic lookup)
     * Uncomment and modify for your parent object
     */
    /*
    public static List<{{ObjectName}}> createForParent(Integer count, Id parentId) {
        List<{{ObjectName}}> records = new List<{{ObjectName}}>();
        for (Integer i = 0; i < count; i++) {
            {{ObjectName}} record = buildRecord(i);
            record.Parent__c = parentId;  // Update with your lookup field API name
            records.add(record);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }
    */

    // ═══════════════════════════════════════════════════════════════════════
    // VARIATION METHODS - Add methods for specific field variations
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Create records with a specific Status
     * Uncomment if your object has a Status picklist
     */
    /*
    public static List<{{ObjectName}}> createWithStatus(Integer count, String status) {
        List<{{ObjectName}}> records = new List<{{ObjectName}}>();
        for (Integer i = 0; i < count; i++) {
            {{ObjectName}} record = buildRecord(i);
            record.Status__c = status;  // Update with your status field API name
            records.add(record);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }
    */

    /**
     * Create records with varied values for comprehensive testing
     * Modify for your object's key picklist fields
     */
    /*
    public static List<{{ObjectName}}> createWithVariedValues(Integer count) {
        List<String> statuses = new List<String>{'Draft', 'Active', 'Complete', 'Cancelled'};

        List<{{ObjectName}}> records = new List<{{ObjectName}}>();
        for (Integer i = 0; i < count; i++) {
            {{ObjectName}} record = buildRecord(i);
            record.Status__c = statuses[Math.mod(i, statuses.size())];
            records.add(record);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }
    */

    // ═══════════════════════════════════════════════════════════════════════
    // RECORD BUILDER - Customize for your object's fields
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Build a single record with default values
     *
     * UPDATE THIS METHOD with your object's fields:
     * 1. Add all required fields
     * 2. Add fields needed for testing
     * 3. Use realistic test values
     *
     * @param index Record index for unique naming
     * @return Record (not inserted)
     */
    private static {{ObjectName}} buildRecord(Integer index) {
        String indexStr = String.valueOf(index).leftPad(5, '0');

        return new {{ObjectName}}(
            Name = DEFAULT_NAME_PREFIX + indexStr

            // ─────────────────────────────────────────────────────────────
            // ADD YOUR FIELDS BELOW
            // ─────────────────────────────────────────────────────────────

            // Text fields
            // , Description__c = 'Test {{ObjectLabel}} created by TestDataFactory'

            // Picklist fields (use valid picklist values)
            // , Status__c = DEFAULT_STATUS
            // , Type__c = DEFAULT_TYPE

            // Number fields
            // , Amount__c = 1000 + (index * 100)
            // , Quantity__c = 1 + index

            // Date fields
            // , StartDate__c = Date.today()
            // , EndDate__c = Date.today().addDays(30 + index)

            // DateTime fields
            // , ScheduledDateTime__c = DateTime.now().addDays(index)

            // Checkbox fields
            // , IsActive__c = true

            // Currency fields
            // , TotalAmount__c = 10000.00 + (index * 500)

            // Percent fields
            // , DiscountPercent__c = 10 + index

            // Email fields
            // , ContactEmail__c = 'test' + index + '@testfactory.example.com'

            // Phone fields
            // , ContactPhone__c = '(555) 900-' + String.valueOf(1000 + index)

            // URL fields
            // , Website__c = 'https://test' + index + '.example.com'

            // Lookup fields (requires parent record ID)
            // , Account__c = accountId
            // , Contact__c = contactId

            // ─────────────────────────────────────────────────────────────
        );
    }

    // ═══════════════════════════════════════════════════════════════════════
    // UTILITY METHODS
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Get IDs of created records for cleanup
     * @param records List of records
     * @return Set of record IDs
     */
    public static Set<Id> getIds(List<{{ObjectName}}> records) {
        Set<Id> ids = new Set<Id>();
        for ({{ObjectName}} record : records) {
            if (record.Id != null) {
                ids.add(record.Id);
            }
        }
        return ids;
    }

    /**
     * Delete records by IDs (cleanup utility)
     * @param recordIds Set of record IDs to delete
     */
    public static void cleanup(Set<Id> recordIds) {
        if (!recordIds.isEmpty()) {
            delete [SELECT Id FROM {{ObjectName}} WHERE Id IN :recordIds];
        }
    }

    /**
     * Delete records by Name pattern (cleanup utility)
     * @param namePattern LIKE pattern (e.g., 'Test%')
     */
    public static void cleanupByName(String namePattern) {
        List<{{ObjectName}}> records = [
            SELECT Id FROM {{ObjectName}}
            WHERE Name LIKE :namePattern
            LIMIT 10000
        ];
        if (!records.isEmpty()) {
            delete records;
        }
    }
}
