/**
 * @description Change Data Capture (CDC) Handler for {{ObjectName}}
 *
 * Use Case: Business logic for processing CDC events
 * - Sync changes to external systems
 * - Maintain audit logs
 * - Trigger downstream processes
 *
 * This class is called by the {{ObjectName}}CDCSubscriber trigger
 * and contains all business logic for CDC event processing.
 *
 * @author {{Author}}
 * @date {{Date}}
 */
public with sharing class {{ObjectName}}CDCHandler {

    // Fields to watch for sync (ignore changes to other fields)
    private static final Set<String> SYNC_FIELDS = new Set<String>{
        'Name',
        'Status__c',
        'Amount__c'
        // Add fields that should trigger sync
    };

    /**
     * @description Handle CREATE change events
     * @param event The CDC event
     * @param header The change event header
     */
    public static void handleCreate({{ObjectName}}ChangeEvent event, EventBus.ChangeEventHeader header) {
        List<String> recordIds = header.getRecordIds();
        Datetime commitTime = header.getCommitTimestamp();

        System.debug(LoggingLevel.DEBUG,
            'CDC CREATE - Records: ' + recordIds + ' at ' + commitTime);

        // Build payload from event field values
        Map<String, Object> payload = buildPayloadFromEvent(event);
        payload.put('recordIds', recordIds);
        payload.put('operation', 'CREATE');
        payload.put('timestamp', commitTime);

        // Queue sync to external system
        System.enqueueJob(new ExternalSyncQueueable(payload));
    }

    /**
     * @description Handle UPDATE change events
     * @param event The CDC event
     * @param header The change event header
     * @param changedFields List of changed field API names
     */
    public static void handleUpdate(
        {{ObjectName}}ChangeEvent event,
        EventBus.ChangeEventHeader header,
        List<String> changedFields
    ) {
        List<String> recordIds = header.getRecordIds();

        // Check if any sync-relevant fields changed
        Boolean relevantChange = false;
        List<String> relevantFields = new List<String>();

        for (String field : changedFields) {
            if (SYNC_FIELDS.contains(field)) {
                relevantChange = true;
                relevantFields.add(field);
            }
        }

        if (!relevantChange) {
            System.debug(LoggingLevel.DEBUG,
                'CDC UPDATE - Ignoring (no sync fields changed): ' + changedFields);
            return;
        }

        System.debug(LoggingLevel.DEBUG,
            'CDC UPDATE - Records: ' + recordIds +
            ', Relevant changed fields: ' + relevantFields);

        // Build payload with changed values
        Map<String, Object> payload = buildPayloadFromEvent(event);
        payload.put('recordIds', recordIds);
        payload.put('operation', 'UPDATE');
        payload.put('changedFields', relevantFields);
        payload.put('timestamp', header.getCommitTimestamp());

        // Queue sync to external system
        System.enqueueJob(new ExternalSyncQueueable(payload));
    }

    /**
     * @description Handle DELETE change events
     * @param recordIds Deleted record IDs
     * @param header The change event header
     */
    public static void handleDelete(List<String> recordIds, EventBus.ChangeEventHeader header) {
        System.debug(LoggingLevel.DEBUG,
            'CDC DELETE - Records: ' + recordIds);

        Map<String, Object> payload = new Map<String, Object>{
            'recordIds' => recordIds,
            'operation' => 'DELETE',
            'timestamp' => header.getCommitTimestamp()
        };

        // Queue delete sync to external system
        System.enqueueJob(new ExternalSyncQueueable(payload));
    }

    /**
     * @description Handle UNDELETE change events
     * @param event The CDC event
     * @param header The change event header
     */
    public static void handleUndelete({{ObjectName}}ChangeEvent event, EventBus.ChangeEventHeader header) {
        // Treat undelete like create - sync full record
        handleCreate(event, header);
    }

    /**
     * @description Handle GAP events (missed events)
     * @param recordIds Affected record IDs
     * @param gapType Type of gap event
     */
    public static void handleGap(List<String> recordIds, String gapType) {
        System.debug(LoggingLevel.WARN,
            'CDC GAP - Type: ' + gapType + ', Records: ' + recordIds);

        // Query current state of records and sync
        // This ensures we have accurate data despite missed events
        /*
        List<{{ObjectName}}> records = [
            SELECT Id, Name, Status__c, Amount__c
            FROM {{ObjectName}}
            WHERE Id IN :recordIds
            WITH USER_MODE
        ];

        for ({{ObjectName}} record : records) {
            Map<String, Object> payload = new Map<String, Object>{
                'recordIds' => new List<String>{record.Id},
                'operation' => 'SYNC', // Full sync due to gap
                'data' => record
            };
            System.enqueueJob(new ExternalSyncQueueable(payload));
        }
        */
    }

    /**
     * @description Handle GAP_OVERFLOW (too many changes)
     * @param entityName The object API name
     */
    public static void handleOverflow(String entityName) {
        System.debug(LoggingLevel.ERROR,
            'CDC OVERFLOW for ' + entityName + ' - Full sync required!');

        // Create alert/task for admin attention
        /*
        Task alertTask = new Task(
            Subject = 'CDC Overflow - Full Sync Required for ' + entityName,
            Description = 'Change Data Capture experienced overflow. ' +
                         'Some events were missed. Full sync is required.',
            Priority = 'High',
            Status = 'Open',
            ActivityDate = Date.today()
        );
        insert alertTask;
        */

        // Consider triggering a batch job for full sync
        // Database.executeBatch(new FullSyncBatch(entityName));
    }

    /**
     * @description Build payload map from CDC event field values
     * @param event The CDC event
     * @return Map of field values
     */
    private static Map<String, Object> buildPayloadFromEvent({{ObjectName}}ChangeEvent event) {
        Map<String, Object> payload = new Map<String, Object>();

        // Map event fields to payload
        // Only non-null values are changed fields
        payload.put('Name', event.Name);
        // payload.put('Status__c', event.Status__c);
        // payload.put('Amount__c', event.Amount__c);
        // Add more fields as needed

        // Remove null values (unchanged fields)
        Set<String> keysToRemove = new Set<String>();
        for (String key : payload.keySet()) {
            if (payload.get(key) == null) {
                keysToRemove.add(key);
            }
        }
        for (String key : keysToRemove) {
            payload.remove(key);
        }

        return payload;
    }

    /**
     * @description Queueable job for syncing to external system
     */
    public class ExternalSyncQueueable implements Queueable, Database.AllowsCallouts {
        private Map<String, Object> payload;

        public ExternalSyncQueueable(Map<String, Object> payload) {
            this.payload = payload;
        }

        public void execute(QueueableContext context) {
            try {
                // Call external system with payload
                // Example: Use Named Credential + REST callout
                /*
                HttpRequest req = new HttpRequest();
                req.setEndpoint('callout:ExternalSystem/sync');
                req.setMethod('POST');
                req.setHeader('Content-Type', 'application/json');
                req.setBody(JSON.serialize(payload));

                Http http = new Http();
                HttpResponse res = http.send(req);

                if (res.getStatusCode() >= 200 && res.getStatusCode() < 300) {
                    System.debug('Sync successful');
                } else {
                    System.debug('Sync failed: ' + res.getStatusCode());
                }
                */

                System.debug(LoggingLevel.DEBUG,
                    'External sync payload: ' + JSON.serialize(payload));

            } catch (Exception e) {
                System.debug(LoggingLevel.ERROR,
                    'External sync failed: ' + e.getMessage());
                // Consider: Create error log, retry logic, DLQ
            }
        }
    }
}
