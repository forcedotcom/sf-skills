/**
 * @description Platform Event Publisher for {{EventName}}__e
 *
 * Use Case: Publish events from Apex
 * - Trigger-based event publishing
 * - Service layer event notifications
 * - Batch job completion events
 *
 * Features:
 * - Single and bulk event publishing
 * - Error handling and logging
 * - Partial success handling for bulk publishes
 *
 * @author {{Author}}
 * @date {{Date}}
 */
public with sharing class {{EventName}}Publisher {

    /**
     * @description Publish a single event
     * @param recordId ID of the triggering record
     * @param operation Operation type (CREATE, UPDATE, DELETE)
     * @param payload JSON payload data
     * @throws EventPublishException if publish fails
     */
    public static void publishEvent(Id recordId, String operation, Map<String, Object> payload) {
        {{EventName}}__e event = new {{EventName}}__e();
        event.Record_Id__c = recordId;
        event.Operation__c = operation;
        event.Payload__c = JSON.serialize(payload);
        event.Correlation_Id__c = generateCorrelationId();
        event.Event_Timestamp__c = Datetime.now();

        Database.SaveResult result = EventBus.publish(event);

        if (!result.isSuccess()) {
            String errorMessage = getErrorMessage(result);
            System.debug(LoggingLevel.ERROR, 'Event publish failed: ' + errorMessage);
            throw new EventPublishException('Failed to publish event: ' + errorMessage);
        }

        System.debug(LoggingLevel.DEBUG, 'Event published successfully. Correlation ID: ' + event.Correlation_Id__c);
    }

    /**
     * @description Publish multiple events in bulk
     * @param events List of events to publish
     * @return List of publish results
     */
    public static List<PublishResult> publishEvents(List<{{EventName}}__e> events) {
        if (events == null || events.isEmpty()) {
            return new List<PublishResult>();
        }

        // Ensure correlation IDs and timestamps
        for ({{EventName}}__e event : events) {
            if (String.isBlank(event.Correlation_Id__c)) {
                event.Correlation_Id__c = generateCorrelationId();
            }
            if (event.Event_Timestamp__c == null) {
                event.Event_Timestamp__c = Datetime.now();
            }
        }

        List<Database.SaveResult> results = EventBus.publish(events);

        List<PublishResult> publishResults = new List<PublishResult>();
        for (Integer i = 0; i < results.size(); i++) {
            Database.SaveResult sr = results[i];
            {{EventName}}__e event = events[i];

            PublishResult pr = new PublishResult();
            pr.correlationId = event.Correlation_Id__c;
            pr.success = sr.isSuccess();

            if (!sr.isSuccess()) {
                pr.errorMessage = getErrorMessage(sr);
                System.debug(LoggingLevel.ERROR,
                    'Event publish failed for correlation ' + pr.correlationId + ': ' + pr.errorMessage);
            }

            publishResults.add(pr);
        }

        return publishResults;
    }

    /**
     * @description Publish events for record changes (use in triggers)
     * @param records Changed records
     * @param operation Operation type
     */
    public static void publishForRecords(List<SObject> records, String operation) {
        if (records == null || records.isEmpty()) {
            return;
        }

        List<{{EventName}}__e> events = new List<{{EventName}}__e>();

        for (SObject record : records) {
            {{EventName}}__e event = new {{EventName}}__e();
            event.Record_Id__c = record.Id;
            event.Operation__c = operation;
            event.Payload__c = JSON.serialize(record);
            event.Correlation_Id__c = generateCorrelationId();
            event.Event_Timestamp__c = Datetime.now();
            events.add(event);
        }

        List<PublishResult> results = publishEvents(events);

        // Log any failures
        for (PublishResult pr : results) {
            if (!pr.success) {
                System.debug(LoggingLevel.ERROR, 'Publish failed: ' + pr.errorMessage);
            }
        }
    }

    /**
     * @description Create event from Map (flexible payload)
     * @param eventData Map containing event fields
     * @return Constructed event
     */
    public static {{EventName}}__e createEvent(Map<String, Object> eventData) {
        {{EventName}}__e event = new {{EventName}}__e();

        if (eventData.containsKey('recordId')) {
            event.Record_Id__c = (String) eventData.get('recordId');
        }
        if (eventData.containsKey('operation')) {
            event.Operation__c = (String) eventData.get('operation');
        }
        if (eventData.containsKey('payload')) {
            Object payload = eventData.get('payload');
            event.Payload__c = payload instanceof String
                ? (String) payload
                : JSON.serialize(payload);
        }
        if (eventData.containsKey('correlationId')) {
            event.Correlation_Id__c = (String) eventData.get('correlationId');
        } else {
            event.Correlation_Id__c = generateCorrelationId();
        }

        event.Event_Timestamp__c = Datetime.now();

        return event;
    }

    /**
     * @description Generate unique correlation ID
     * @return UUID-like correlation ID
     */
    private static String generateCorrelationId() {
        Blob b = Crypto.generateAesKey(128);
        String h = EncodingUtil.convertToHex(b);
        return h.substring(0, 8) + '-' +
               h.substring(8, 12) + '-' +
               h.substring(12, 16) + '-' +
               h.substring(16, 20) + '-' +
               h.substring(20);
    }

    /**
     * @description Extract error message from SaveResult
     * @param result Database.SaveResult
     * @return Error message string
     */
    private static String getErrorMessage(Database.SaveResult result) {
        List<String> messages = new List<String>();
        for (Database.Error err : result.getErrors()) {
            messages.add(err.getStatusCode() + ': ' + err.getMessage());
        }
        return String.join(messages, '; ');
    }

    /**
     * @description Result wrapper for bulk publish operations
     */
    public class PublishResult {
        public String correlationId;
        public Boolean success;
        public String errorMessage;
    }

    /**
     * @description Exception for event publish failures
     */
    public class EventPublishException extends Exception {}
}
