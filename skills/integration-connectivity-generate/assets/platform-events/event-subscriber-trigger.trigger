/**
 * @description Platform Event Subscriber Trigger for {{EventName}}__e
 *
 * Use Case: React to published Platform Events
 * - Process incoming events from other systems
 * - Sync data based on events
 * - Trigger downstream processes
 *
 * Key Concepts:
 * - Platform Event triggers run in their own execution context
 * - Events are processed in batches (up to 2000 for High Volume)
 * - ReplayId enables resuming from failures
 * - SetResumeCheckpoint ensures durability
 *
 * IMPORTANT:
 * - Triggers on Platform Events only fire on AFTER INSERT
 * - Events are immutable (cannot be updated or deleted)
 * - Triggers run as Automated Process user
 *
 * @author {{Author}}
 * @date {{Date}}
 */
trigger {{EventName}}Subscriber on {{EventName}}__e (after insert) {

    // Track last processed replay ID for durability
    String lastReplayId = '';

    // Process each event
    for ({{EventName}}__e event : Trigger.new) {
        // Store replay ID for checkpoint
        lastReplayId = event.ReplayId;

        try {
            // Log event receipt
            System.debug(LoggingLevel.DEBUG,
                'Processing event: ' + event.Correlation_Id__c +
                ' Operation: ' + event.Operation__c +
                ' ReplayId: ' + event.ReplayId);

            // Route to handler based on operation
            switch on event.Operation__c {
                when 'CREATE' {
                    {{EventName}}Handler.handleCreate(event);
                }
                when 'UPDATE' {
                    {{EventName}}Handler.handleUpdate(event);
                }
                when 'DELETE' {
                    {{EventName}}Handler.handleDelete(event);
                }
                when else {
                    // Unknown operation - log and continue
                    System.debug(LoggingLevel.WARN,
                        'Unknown operation: ' + event.Operation__c +
                        ' for event: ' + event.Correlation_Id__c);
                }
            }

        } catch (Exception e) {
            // Log error but continue processing other events
            // Don't throw - that would cause retry of ALL events in batch
            System.debug(LoggingLevel.ERROR,
                'Error processing event ' + event.Correlation_Id__c + ': ' + e.getMessage());
            System.debug(LoggingLevel.ERROR, 'Stack: ' + e.getStackTraceString());

            // Consider: Create error log record for monitoring
            // {{EventName}}ErrorLogger.logError(event, e);
        }
    }

    // Set resume checkpoint for durability
    // If trigger fails after this point, processing resumes from this ReplayId
    if (String.isNotBlank(lastReplayId)) {
        EventBus.TriggerContext.currentContext().setResumeCheckpoint(lastReplayId);
    }
}

/*
 * ============================================================================
 * PLATFORM EVENT TRIGGER BEST PRACTICES
 * ============================================================================
 *
 * 1. ALWAYS set resume checkpoint
 *    - Call setResumeCheckpoint() with the last processed ReplayId
 *    - Ensures events aren't lost if trigger fails mid-batch
 *
 * 2. DON'T throw exceptions
 *    - Unhandled exceptions cause entire batch to retry
 *    - Catch errors per-event and log them
 *    - Continue processing remaining events
 *
 * 3. Keep processing lightweight
 *    - Avoid SOQL/DML in loops
 *    - Collect data, then do bulk DML outside loop
 *    - Consider queueing heavy work via Queueable
 *
 * 4. Handle duplicates
 *    - At-least-once delivery means duplicates possible
 *    - Use Correlation_Id__c to detect/dedupe
 *    - Design handlers to be idempotent
 *
 * 5. Monitor failures
 *    - Log errors to custom object for visibility
 *    - Set up alerts for processing failures
 *    - Review Event Delivery Failures in Setup
 *
 * ============================================================================
 */
