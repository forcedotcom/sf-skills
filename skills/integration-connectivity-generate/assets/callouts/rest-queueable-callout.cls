/**
 * @description Asynchronous REST Callout using Queueable
 *
 * Use Case: Callouts triggered from DML operations
 * - Trigger-based integrations
 * - Process Builder / Flow callouts
 * - Any callout after DML (insert, update, delete)
 *
 * CRITICAL: Synchronous callouts are NOT allowed after DML.
 *           Always use Queueable with Database.AllowsCallouts for such scenarios.
 *
 * Features:
 * - Implements Database.AllowsCallouts for HTTP requests
 * - Processes records in batches
 * - Includes error handling and logging
 * - Supports job chaining for pagination
 *
 * @author {{Author}}
 * @date {{Date}}
 */
public with sharing class {{ServiceName}}QueueableCallout implements Queueable, Database.AllowsCallouts {

    private static final String NAMED_CREDENTIAL = 'callout:{{NamedCredentialName}}';
    private static final Integer DEFAULT_TIMEOUT = 120000;
    private static final Integer BATCH_SIZE = 10; // Callouts per job (max 100 per transaction)

    private List<Id> recordIds;
    private String operation;
    private Integer startIndex;

    /**
     * @description Constructor for processing records
     * @param recordIds List of record IDs to process
     * @param operation Operation type (CREATE, UPDATE, DELETE, SYNC)
     */
    public {{ServiceName}}QueueableCallout(List<Id> recordIds, String operation) {
        this(recordIds, operation, 0);
    }

    /**
     * @description Constructor with pagination support
     * @param recordIds List of record IDs to process
     * @param operation Operation type
     * @param startIndex Starting index for batch processing
     */
    public {{ServiceName}}QueueableCallout(List<Id> recordIds, String operation, Integer startIndex) {
        this.recordIds = recordIds;
        this.operation = operation;
        this.startIndex = startIndex;
    }

    /**
     * @description Execute the queueable job
     * @param context QueueableContext
     */
    public void execute(QueueableContext context) {
        if (recordIds == null || recordIds.isEmpty()) {
            return;
        }

        // Calculate batch bounds
        Integer endIndex = Math.min(startIndex + BATCH_SIZE, recordIds.size());
        List<Id> batchIds = new List<Id>();
        for (Integer i = startIndex; i < endIndex; i++) {
            batchIds.add(recordIds[i]);
        }

        try {
            // Query records for this batch
            List<{{ObjectName}}> records = [
                SELECT Id, Name{{AdditionalFields}}
                FROM {{ObjectName}}
                WHERE Id IN :batchIds
                WITH USER_MODE
            ];

            // Process each record
            List<{{ObjectName}}> toUpdate = new List<{{ObjectName}}>();
            for ({{ObjectName}} record : records) {
                try {
                    processRecord(record, operation);
                    // Mark success on record if needed
                    record.Integration_Status__c = 'Success';
                    record.Integration_Date__c = Datetime.now();
                    toUpdate.add(record);
                } catch (Exception e) {
                    // Log individual record failure
                    System.debug(LoggingLevel.ERROR,
                        'Failed to process record ' + record.Id + ': ' + e.getMessage());
                    record.Integration_Status__c = 'Error';
                    record.Integration_Error__c = e.getMessage().left(255);
                    toUpdate.add(record);
                }
            }

            // Update records with sync status
            if (!toUpdate.isEmpty()) {
                update toUpdate;
            }

            // Chain next batch if more records remain
            if (endIndex < recordIds.size()) {
                System.enqueueJob(
                    new {{ServiceName}}QueueableCallout(recordIds, operation, endIndex)
                );
            }

        } catch (Exception e) {
            System.debug(LoggingLevel.ERROR, '{{ServiceName}}QueueableCallout Error: ' + e.getMessage());
            System.debug(LoggingLevel.ERROR, 'Stack Trace: ' + e.getStackTraceString());
            // Consider: Create Integration_Log__c record, send notification, etc.
        }
    }

    /**
     * @description Process a single record with external API
     * @param record The record to process
     * @param operation The operation type
     */
    private void processRecord({{ObjectName}} record, String operation) {
        switch on operation {
            when 'CREATE' {
                createExternalRecord(record);
            }
            when 'UPDATE' {
                updateExternalRecord(record);
            }
            when 'DELETE' {
                deleteExternalRecord(record.Id);
            }
            when 'SYNC' {
                syncExternalRecord(record);
            }
            when else {
                throw new IntegrationException('Unknown operation: ' + operation);
            }
        }
    }

    /**
     * @description Create record in external system
     * @param record Salesforce record
     */
    private void createExternalRecord({{ObjectName}} record) {
        Map<String, Object> payload = buildPayload(record);

        HttpRequest req = new HttpRequest();
        req.setEndpoint(NAMED_CREDENTIAL + '/{{Endpoint}}');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setTimeout(DEFAULT_TIMEOUT);
        req.setBody(JSON.serialize(payload));

        HttpResponse res = new Http().send(req);
        handleResponse(res, record.Id);
    }

    /**
     * @description Update record in external system
     * @param record Salesforce record
     */
    private void updateExternalRecord({{ObjectName}} record) {
        if (String.isBlank(record.External_Id__c)) {
            throw new IntegrationException('No external ID for record: ' + record.Id);
        }

        Map<String, Object> payload = buildPayload(record);

        HttpRequest req = new HttpRequest();
        req.setEndpoint(NAMED_CREDENTIAL + '/{{Endpoint}}/' + record.External_Id__c);
        req.setMethod('PUT');
        req.setHeader('Content-Type', 'application/json');
        req.setTimeout(DEFAULT_TIMEOUT);
        req.setBody(JSON.serialize(payload));

        HttpResponse res = new Http().send(req);
        handleResponse(res, record.Id);
    }

    /**
     * @description Delete record from external system
     * @param recordId Salesforce record ID
     */
    private void deleteExternalRecord(Id recordId) {
        // Query for external ID
        {{ObjectName}} record = [
            SELECT External_Id__c
            FROM {{ObjectName}}
            WHERE Id = :recordId
            WITH USER_MODE
            LIMIT 1
        ];

        if (String.isBlank(record.External_Id__c)) {
            return; // Nothing to delete externally
        }

        HttpRequest req = new HttpRequest();
        req.setEndpoint(NAMED_CREDENTIAL + '/{{Endpoint}}/' + record.External_Id__c);
        req.setMethod('DELETE');
        req.setTimeout(DEFAULT_TIMEOUT);

        HttpResponse res = new Http().send(req);
        handleResponse(res, recordId);
    }

    /**
     * @description Sync record with external system (get latest and update)
     * @param record Salesforce record
     */
    private void syncExternalRecord({{ObjectName}} record) {
        if (String.isBlank(record.External_Id__c)) {
            createExternalRecord(record);
        } else {
            updateExternalRecord(record);
        }
    }

    /**
     * @description Build API payload from Salesforce record
     * @param record Salesforce record
     * @return Payload map for API
     */
    private Map<String, Object> buildPayload({{ObjectName}} record) {
        return new Map<String, Object>{
            'salesforceId' => record.Id,
            'name' => record.Name
            // Add more field mappings as needed
        };
    }

    /**
     * @description Handle HTTP response
     * @param res HTTP response
     * @param recordId Salesforce record ID (for logging)
     */
    private void handleResponse(HttpResponse res, Id recordId) {
        Integer statusCode = res.getStatusCode();

        if (statusCode >= 200 && statusCode < 300) {
            System.debug(LoggingLevel.DEBUG, 'Success for ' + recordId + ': ' + res.getBody());
            return;
        }

        if (statusCode >= 400 && statusCode < 500) {
            throw new IntegrationException(
                'Client Error (' + statusCode + ') for ' + recordId + ': ' + res.getBody()
            );
        }

        if (statusCode >= 500) {
            throw new IntegrationException(
                'Server Error (' + statusCode + ') for ' + recordId + ': ' + res.getBody()
            );
        }
    }

    /**
     * @description Custom exception for integration errors
     */
    public class IntegrationException extends Exception {}
}
