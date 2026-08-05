/**
 * ${OBJECT_NAME}Selector - Centralized SOQL queries for ${OBJECT_NAME}
 *
 * This selector class follows the Selector Layer pattern to:
 * - Centralize all ${OBJECT_NAME} queries in one place
 * - Enforce Field-Level Security (FLS) by default
 * - Support query mocking in unit tests
 * - Provide consistent field selection across the codebase
 *
 * @see https://blog.beyondthecloud.dev/blog/why-do-you-need-selector-layer
 * @see https://www.jamessimone.net/blog/joys-of-apex/repository-pattern/
 */
public inherited sharing class ${OBJECT_NAME}Selector {

    // ═══════════════════════════════════════════════════════════════════
    // FIELD DEFINITIONS
    // Centralize field lists to make updates easy
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Standard fields queried in most operations
     */
    private static final List<SObjectField> STANDARD_FIELDS = new List<SObjectField>{
        ${OBJECT_NAME}.Id,
        ${OBJECT_NAME}.Name,
        ${OBJECT_NAME}.OwnerId,
        ${OBJECT_NAME}.CreatedDate,
        ${OBJECT_NAME}.LastModifiedDate
        // Add commonly needed fields here
    };

    /**
     * Extended fields for detail views
     */
    private static final List<SObjectField> DETAIL_FIELDS = new List<SObjectField>{
        ${OBJECT_NAME}.Id,
        ${OBJECT_NAME}.Name,
        ${OBJECT_NAME}.OwnerId,
        ${OBJECT_NAME}.CreatedDate,
        ${OBJECT_NAME}.LastModifiedDate
        // Add detail-specific fields here
    };

    // ═══════════════════════════════════════════════════════════════════
    // MOCKING SUPPORT (for unit tests)
    // ═══════════════════════════════════════════════════════════════════

    @TestVisible
    private static List<${OBJECT_NAME}> mockResults;

    @TestVisible
    private static void setMockResults(List<${OBJECT_NAME}> records) {
        mockResults = records;
    }

    @TestVisible
    private static void clearMockResults() {
        mockResults = null;
    }

    private static Boolean useMock() {
        return Test.isRunningTest() && mockResults != null;
    }

    // ═══════════════════════════════════════════════════════════════════
    // QUERY METHODS
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Query records by their IDs
     *
     * @param recordIds Set of record IDs to query
     * @return List of matching records with standard fields
     */
    public static List<${OBJECT_NAME}> byIds(Set<Id> recordIds) {
        if (recordIds == null || recordIds.isEmpty()) {
            return new List<${OBJECT_NAME}>();
        }
        if (useMock()) {
            return mockResults;
        }
        return [
            SELECT Id, Name, OwnerId, CreatedDate, LastModifiedDate
            FROM ${OBJECT_NAME}
            WHERE Id IN :recordIds
            WITH SECURITY_ENFORCED
        ];
    }

    /**
     * Query records by their IDs, returning a Map for O(1) lookups
     *
     * @param recordIds Set of record IDs to query
     * @return Map of Id to record
     */
    public static Map<Id, ${OBJECT_NAME}> byIdsAsMap(Set<Id> recordIds) {
        return new Map<Id, ${OBJECT_NAME}>(byIds(recordIds));
    }

    /**
     * Query records by Owner
     *
     * @param ownerId The owner's User Id
     * @return List of records owned by the specified user
     */
    public static List<${OBJECT_NAME}> byOwnerId(Id ownerId) {
        if (ownerId == null) {
            return new List<${OBJECT_NAME}>();
        }
        if (useMock()) {
            return mockResults;
        }
        return [
            SELECT Id, Name, OwnerId, CreatedDate, LastModifiedDate
            FROM ${OBJECT_NAME}
            WHERE OwnerId = :ownerId
            WITH SECURITY_ENFORCED
            ORDER BY LastModifiedDate DESC
            LIMIT 1000
        ];
    }

    /**
     * Query records created within a date range
     *
     * @param startDate Start of date range (inclusive)
     * @param endDate End of date range (inclusive)
     * @return List of records created within the range
     */
    public static List<${OBJECT_NAME}> byCreatedDateRange(Date startDate, Date endDate) {
        if (startDate == null || endDate == null) {
            return new List<${OBJECT_NAME}>();
        }
        if (useMock()) {
            return mockResults;
        }
        return [
            SELECT Id, Name, OwnerId, CreatedDate, LastModifiedDate
            FROM ${OBJECT_NAME}
            WHERE CreatedDate >= :startDate
            AND CreatedDate <= :endDate
            WITH SECURITY_ENFORCED
            ORDER BY CreatedDate DESC
            LIMIT 10000
        ];
    }

    // ═══════════════════════════════════════════════════════════════════
    // RELATIONSHIP QUERIES
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Query records with related child records
     * Customize the subquery for your object relationships
     *
     * @param recordIds Set of parent record IDs
     * @return List of parent records with child records populated
     */
    public static List<${OBJECT_NAME}> withChildRecordsByIds(Set<Id> recordIds) {
        if (recordIds == null || recordIds.isEmpty()) {
            return new List<${OBJECT_NAME}>();
        }
        if (useMock()) {
            return mockResults;
        }
        return [
            SELECT Id, Name, OwnerId,
                   (SELECT Id, Name
                    FROM ChildRelationshipName__r  // Replace with actual relationship
                    WHERE IsActive__c = true
                    LIMIT 50)
            FROM ${OBJECT_NAME}
            WHERE Id IN :recordIds
            WITH SECURITY_ENFORCED
        ];
    }

    // ═══════════════════════════════════════════════════════════════════
    // AGGREGATE QUERIES
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Count records by a grouping field
     *
     * @return List of AggregateResult with grouping and count
     */
    public static List<AggregateResult> countByOwner() {
        return [
            SELECT OwnerId, COUNT(Id) recordCount
            FROM ${OBJECT_NAME}
            GROUP BY OwnerId
            HAVING COUNT(Id) > 0
        ];
    }

    // ═══════════════════════════════════════════════════════════════════
    // EXISTENCE CHECK
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Check if a record exists by ID (efficient single record lookup)
     *
     * @param recordId The record ID to check
     * @return true if the record exists
     */
    public static Boolean existsById(Id recordId) {
        if (recordId == null) {
            return false;
        }
        List<${OBJECT_NAME}> results = [
            SELECT Id
            FROM ${OBJECT_NAME}
            WHERE Id = :recordId
            WITH SECURITY_ENFORCED
            LIMIT 1
        ];
        return !results.isEmpty();
    }
}
