/**
 * @description Change Data Capture (CDC) Subscriber Trigger for {{ObjectName}}
 *
 * Use Case: React to data changes in near real-time
 * - Sync data to external systems
 * - Audit logging
 * - Cache invalidation
 * - Event-driven integrations
 *
 * CDC Channel Name: {{ObjectName}}ChangeEvent
 * - Standard objects: AccountChangeEvent, ContactChangeEvent, etc.
 * - Custom objects: MyObject__ChangeEvent (append "ChangeEvent" to API name)
 *
 * Key Concepts:
 * - ChangeEventHeader contains metadata (changeType, changedFields, recordIds)
 * - Event contains changed field values (nulls for unchanged fields)
 * - Supports CREATE, UPDATE, DELETE, UNDELETE change types
 * - Gap events indicate missed events (handle replay)
 *
 * IMPORTANT:
 * - Enable CDC for object in Setup → Integrations → Change Data Capture
 * - Triggers fire in separate transaction from DML
 * - Events are retained for 3 days (replay window)
 *
 * @author {{Author}}
 * @date {{Date}}
 */
trigger {{ObjectName}}CDCSubscriber on {{ObjectName}}ChangeEvent (after insert) {

    // Track replay ID for checkpoint
    String lastReplayId = '';

    for ({{ObjectName}}ChangeEvent event : Trigger.new) {
        // Store replay ID
        lastReplayId = event.ReplayId;

        // Get change event header (metadata about the change)
        EventBus.ChangeEventHeader header = event.ChangeEventHeader;

        // Extract header information
        String changeType = header.getChangeType();
        List<String> changedFields = header.getChangedFields();
        List<String> recordIds = header.getRecordIds();
        String entityName = header.getEntityName();
        Long commitNumber = header.getCommitNumber();
        Datetime commitTimestamp = header.getCommitTimestamp();
        String transactionKey = header.getTransactionKey();

        // Log event details
        System.debug(LoggingLevel.DEBUG,
            'CDC Event - Type: ' + changeType +
            ', Entity: ' + entityName +
            ', Records: ' + recordIds +
            ', Changed Fields: ' + changedFields);

        try {
            // Route based on change type
            switch on changeType {
                when 'CREATE' {
                    {{ObjectName}}CDCHandler.handleCreate(event, header);
                }
                when 'UPDATE' {
                    {{ObjectName}}CDCHandler.handleUpdate(event, header, changedFields);
                }
                when 'DELETE' {
                    {{ObjectName}}CDCHandler.handleDelete(recordIds, header);
                }
                when 'UNDELETE' {
                    {{ObjectName}}CDCHandler.handleUndelete(event, header);
                }
                when 'GAP_CREATE', 'GAP_UPDATE', 'GAP_DELETE', 'GAP_UNDELETE' {
                    // Gap events indicate missed events
                    // Should trigger full sync for affected records
                    System.debug(LoggingLevel.WARN,
                        'GAP event detected - some events may have been missed. ' +
                        'Type: ' + changeType + ', Records: ' + recordIds);
                    {{ObjectName}}CDCHandler.handleGap(recordIds, changeType);
                }
                when 'GAP_OVERFLOW' {
                    // Too many changes to track - full sync needed
                    System.debug(LoggingLevel.ERROR,
                        'GAP_OVERFLOW - full sync required for ' + entityName);
                    {{ObjectName}}CDCHandler.handleOverflow(entityName);
                }
            }

        } catch (Exception e) {
            // Log error but continue processing
            System.debug(LoggingLevel.ERROR,
                'CDC processing error for ' + recordIds + ': ' + e.getMessage());
            System.debug(LoggingLevel.ERROR, 'Stack: ' + e.getStackTraceString());
        }
    }

    // Set resume checkpoint for durability
    if (String.isNotBlank(lastReplayId)) {
        EventBus.TriggerContext.currentContext().setResumeCheckpoint(lastReplayId);
    }
}

/*
 * ============================================================================
 * CDC TRIGGER BEST PRACTICES
 * ============================================================================
 *
 * 1. ENABLE CDC FOR OBJECT
 *    Setup → Integrations → Change Data Capture → Select Objects
 *
 * 2. HANDLE ALL CHANGE TYPES
 *    - CREATE: New record
 *    - UPDATE: Record modified
 *    - DELETE: Record deleted
 *    - UNDELETE: Record restored from recycle bin
 *    - GAP_*: Events were missed (sync required)
 *    - GAP_OVERFLOW: Too many changes (full sync needed)
 *
 * 3. USE CHANGEDEVENTHEAD FOR METADATA
 *    - getChangeType(): Operation type
 *    - getChangedFields(): List of changed field API names
 *    - getRecordIds(): Affected record IDs
 *    - getCommitTimestamp(): When change occurred
 *
 * 4. FIELD VALUES IN EVENT
 *    - Changed fields have new values
 *    - Unchanged fields are NULL
 *    - Use changedFields list to know what changed
 *
 * 5. IDEMPOTENT HANDLERS
 *    - Same event might fire multiple times
 *    - Use transactionKey to detect duplicates
 *    - Design handlers to be safe for replay
 *
 * 6. BULK CONSIDERATIONS
 *    - Multiple records can be in single event (batch DML)
 *    - Use getRecordIds() to get all affected IDs
 *    - Process all record IDs efficiently
 *
 * ============================================================================
 */
