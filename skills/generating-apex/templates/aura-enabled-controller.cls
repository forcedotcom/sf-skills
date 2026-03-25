/**
 * Controller for {ComponentName} Lightning Web Component.
 * Exposes server-side operations to LWC via @AuraEnabled methods.
 * All queries use WITH USER_MODE for CRUD/FLS enforcement.
 */
public with sharing class {ClassName}Controller {

    // ─── Read Operations (cacheable) ─────────────────────────────────────

    /**
     * Retrieves {SObject} records for the given parent Id.
     *              Cacheable for LDS/wire adapter performance.
     * @param parentId The parent record Id to filter by
     * @return List of {SObject} records
     */
    @AuraEnabled(cacheable=true)
    public static List<{SObject}> getRecords(Id parentId) {
        if (parentId == null) {
            return new List<{SObject}>();
        }

        return [
            SELECT Id, Name, CreatedDate
            FROM {SObject}
            WHERE {ParentField} = :parentId
            WITH USER_MODE
            ORDER BY Name ASC
        ];
    }

    // ─── Write Operations (non-cacheable) ────────────────────────────────

    /**
     * Creates or updates a {SObject} record.
     *              Cannot use cacheable=true because this performs DML.
     * @param record The {SObject} record to save
     * @return The saved record Id
     */
    @AuraEnabled
    public static Id saveRecord({SObject} record) {
        if (record == null) {
            throw new AuraHandledException('Record cannot be null.');
        }

        try {
            upsert record;
            return record.Id;
        } catch (DmlException e) {
            throw new AuraHandledException(e.getDmlMessage(0));
        }
    }

    /**
     * Deletes a {SObject} record by Id.
     * @param recordId The Id of the record to delete
     */
    @AuraEnabled
    public static void deleteRecord(Id recordId) {
        if (recordId == null) {
            throw new AuraHandledException('Record Id cannot be null.');
        }

        try {
            delete [SELECT Id FROM {SObject} WHERE Id = :recordId WITH USER_MODE];
        } catch (DmlException e) {
            throw new AuraHandledException(e.getDmlMessage(0));
        }
    }

    // ─── Action Operations ───────────────────────────────────────────────

    /**
     * Processes a {SObject} record and returns a result map.
     *              Use for imperative calls from LWC that need structured responses.
     * @param recordId The Id of the record to process
     * @return Map with isSuccess (Boolean), message (String), and optional data
     */
    @AuraEnabled
    public static Map<String, Object> processRecord(Id recordId) {
        if (recordId == null) {
            throw new AuraHandledException('Record Id cannot be null.');
        }

        try {
            {SObject} record = [
                SELECT Id, Name
                FROM {SObject}
                WHERE Id = :recordId
                WITH USER_MODE
            ];

            // TODO: Implement processing logic

            return new Map<String, Object>{
                'isSuccess' => true,
                'message' => 'Record processed successfully.',
                'recordId' => record.Id
            };
        } catch (QueryException e) {
            throw new AuraHandledException('Record not found.');
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }
}
