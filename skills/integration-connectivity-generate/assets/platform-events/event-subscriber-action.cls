/**
 * @description Platform Event Handler/Action Class for {{EventName}}__e
 *
 * Use Case: Business logic for processing Platform Events
 * - Separated from trigger for testability
 * - TAF-compatible action pattern
 * - Bulkified processing
 *
 * This class is called by the {{EventName}}Subscriber trigger
 * and contains all business logic for event processing.
 *
 * @author {{Author}}
 * @date {{Date}}
 */
public with sharing class {{EventName}}Handler {

    /**
     * @description Handle CREATE operation events
     * @param event The platform event
     */
    public static void handleCreate({{EventName}}__e event) {
        Map<String, Object> payload = parsePayload(event.Payload__c);

        // Example: Create a record based on event data
        /*
        {{TargetObject}}__c newRecord = new {{TargetObject}}__c();
        newRecord.Name = (String) payload.get('name');
        newRecord.External_Id__c = event.Record_Id__c;
        newRecord.Source_System__c = 'Platform Event';
        insert newRecord;
        */

        System.debug(LoggingLevel.DEBUG,
            'Processed CREATE event: ' + event.Correlation_Id__c);
    }

    /**
     * @description Handle UPDATE operation events
     * @param event The platform event
     */
    public static void handleUpdate({{EventName}}__e event) {
        Map<String, Object> payload = parsePayload(event.Payload__c);
        String recordId = event.Record_Id__c;

        // Example: Update existing record
        /*
        List<{{TargetObject}}__c> records = [
            SELECT Id, Name
            FROM {{TargetObject}}__c
            WHERE External_Id__c = :recordId
            WITH USER_MODE
            LIMIT 1
        ];

        if (!records.isEmpty()) {
            {{TargetObject}}__c record = records[0];
            record.Name = (String) payload.get('name');
            record.Last_Sync__c = Datetime.now();
            update record;
        }
        */

        System.debug(LoggingLevel.DEBUG,
            'Processed UPDATE event: ' + event.Correlation_Id__c);
    }

    /**
     * @description Handle DELETE operation events
     * @param event The platform event
     */
    public static void handleDelete({{EventName}}__e event) {
        String recordId = event.Record_Id__c;

        // Example: Delete or archive record
        /*
        List<{{TargetObject}}__c> records = [
            SELECT Id
            FROM {{TargetObject}}__c
            WHERE External_Id__c = :recordId
            WITH USER_MODE
            LIMIT 1
        ];

        if (!records.isEmpty()) {
            delete records;
        }
        */

        System.debug(LoggingLevel.DEBUG,
            'Processed DELETE event: ' + event.Correlation_Id__c);
    }

    /**
     * @description Handle bulk events (for optimized processing)
     *              Call this from trigger instead of individual handlers
     *              when processing high volumes
     * @param events List of events to process
     */
    public static void handleBulk(List<{{EventName}}__e> events) {
        // Separate events by operation
        List<{{EventName}}__e> createEvents = new List<{{EventName}}__e>();
        List<{{EventName}}__e> updateEvents = new List<{{EventName}}__e>();
        List<{{EventName}}__e> deleteEvents = new List<{{EventName}}__e>();

        for ({{EventName}}__e event : events) {
            switch on event.Operation__c {
                when 'CREATE' {
                    createEvents.add(event);
                }
                when 'UPDATE' {
                    updateEvents.add(event);
                }
                when 'DELETE' {
                    deleteEvents.add(event);
                }
            }
        }

        // Process each operation type in bulk
        if (!createEvents.isEmpty()) {
            handleBulkCreate(createEvents);
        }
        if (!updateEvents.isEmpty()) {
            handleBulkUpdate(updateEvents);
        }
        if (!deleteEvents.isEmpty()) {
            handleBulkDelete(deleteEvents);
        }
    }

    /**
     * @description Bulk create handler
     * @param events CREATE events
     */
    private static void handleBulkCreate(List<{{EventName}}__e> events) {
        List<{{TargetObject}}__c> newRecords = new List<{{TargetObject}}__c>();

        for ({{EventName}}__e event : events) {
            Map<String, Object> payload = parsePayload(event.Payload__c);

            {{TargetObject}}__c record = new {{TargetObject}}__c();
            // Map fields from payload
            // record.Name = (String) payload.get('name');
            // record.External_Id__c = event.Record_Id__c;

            newRecords.add(record);
        }

        if (!newRecords.isEmpty()) {
            // Use Database.insert for partial success handling
            Database.SaveResult[] results = Database.insert(newRecords, false);
            logDmlResults(results, 'CREATE');
        }
    }

    /**
     * @description Bulk update handler
     * @param events UPDATE events
     */
    private static void handleBulkUpdate(List<{{EventName}}__e> events) {
        // Collect external IDs to query
        Set<String> externalIds = new Set<String>();
        Map<String, {{EventName}}__e> eventsByExternalId = new Map<String, {{EventName}}__e>();

        for ({{EventName}}__e event : events) {
            externalIds.add(event.Record_Id__c);
            eventsByExternalId.put(event.Record_Id__c, event);
        }

        // Query existing records
        /*
        Map<String, {{TargetObject}}__c> recordsByExternalId = new Map<String, {{TargetObject}}__c>();
        for ({{TargetObject}}__c record : [
            SELECT Id, External_Id__c, Name
            FROM {{TargetObject}}__c
            WHERE External_Id__c IN :externalIds
            WITH USER_MODE
        ]) {
            recordsByExternalId.put(record.External_Id__c, record);
        }

        // Update records
        List<{{TargetObject}}__c> toUpdate = new List<{{TargetObject}}__c>();
        for (String extId : externalIds) {
            if (recordsByExternalId.containsKey(extId)) {
                {{TargetObject}}__c record = recordsByExternalId.get(extId);
                {{EventName}}__e event = eventsByExternalId.get(extId);
                Map<String, Object> payload = parsePayload(event.Payload__c);

                // Update fields
                // record.Name = (String) payload.get('name');
                toUpdate.add(record);
            }
        }

        if (!toUpdate.isEmpty()) {
            Database.SaveResult[] results = Database.update(toUpdate, false);
            logDmlResults(results, 'UPDATE');
        }
        */
    }

    /**
     * @description Bulk delete handler
     * @param events DELETE events
     */
    private static void handleBulkDelete(List<{{EventName}}__e> events) {
        Set<String> externalIds = new Set<String>();
        for ({{EventName}}__e event : events) {
            externalIds.add(event.Record_Id__c);
        }

        /*
        List<{{TargetObject}}__c> toDelete = [
            SELECT Id
            FROM {{TargetObject}}__c
            WHERE External_Id__c IN :externalIds
            WITH USER_MODE
        ];

        if (!toDelete.isEmpty()) {
            Database.DeleteResult[] results = Database.delete(toDelete, false);
            logDeleteResults(results, 'DELETE');
        }
        */
    }

    /**
     * @description Parse JSON payload to Map
     * @param payloadJson JSON string
     * @return Parsed Map
     */
    private static Map<String, Object> parsePayload(String payloadJson) {
        if (String.isBlank(payloadJson)) {
            return new Map<String, Object>();
        }

        try {
            return (Map<String, Object>) JSON.deserializeUntyped(payloadJson);
        } catch (JSONException e) {
            System.debug(LoggingLevel.ERROR, 'Failed to parse payload: ' + e.getMessage());
            return new Map<String, Object>();
        }
    }

    /**
     * @description Log DML results for monitoring
     * @param results Database.SaveResult array
     * @param operation Operation name
     */
    private static void logDmlResults(Database.SaveResult[] results, String operation) {
        Integer successCount = 0;
        Integer failCount = 0;

        for (Database.SaveResult sr : results) {
            if (sr.isSuccess()) {
                successCount++;
            } else {
                failCount++;
                for (Database.Error err : sr.getErrors()) {
                    System.debug(LoggingLevel.ERROR,
                        operation + ' failed: ' + err.getStatusCode() + ' - ' + err.getMessage());
                }
            }
        }

        System.debug(LoggingLevel.INFO,
            operation + ' results - Success: ' + successCount + ', Failed: ' + failCount);
    }

    /**
     * @description Log delete results for monitoring
     * @param results Database.DeleteResult array
     * @param operation Operation name
     */
    private static void logDeleteResults(Database.DeleteResult[] results, String operation) {
        Integer successCount = 0;
        Integer failCount = 0;

        for (Database.DeleteResult dr : results) {
            if (dr.isSuccess()) {
                successCount++;
            } else {
                failCount++;
                for (Database.Error err : dr.getErrors()) {
                    System.debug(LoggingLevel.ERROR,
                        operation + ' failed: ' + err.getStatusCode() + ' - ' + err.getMessage());
                }
            }
        }

        System.debug(LoggingLevel.INFO,
            operation + ' results - Success: ' + successCount + ', Failed: ' + failCount);
    }
}
