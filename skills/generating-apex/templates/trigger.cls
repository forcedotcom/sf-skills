/**
 * Trigger for {SObject}.
 *              Delegates all logic to the Trigger Actions Framework (MetadataTriggerHandler).
 *              If TAF is not installed, delegate to a single handler class instead.
 */
trigger {SObject}Trigger on {SObject} (
    before insert, after insert,
    before update, after update,
    before delete, after delete,
    after undelete
) {
    // Option A: Trigger Actions Framework (recommended when TAF is installed)
    new MetadataTriggerHandler().run();

    // Option B: Single handler class (when TAF is not available)
    // {SObject}TriggerHandler.handle(Trigger.operationType, Trigger.new, Trigger.old);
}
