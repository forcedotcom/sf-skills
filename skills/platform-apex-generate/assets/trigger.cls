/**
 * {SObject} Trigger
 */
trigger {SObject}Trigger on {SObject} (
    before insert,
    before update,
    before delete,
    after insert,
    after update,
    after delete,
    after undelete
) {
    // ─── Option A: Trigger Actions Framework (TAF) ───────────────────────
    // Delegates to Trigger_Action__mdt-registered action classes.
    // Each action class handles one concern in one context.
    //
    // new MetadataTriggerHandler().run();

    // ─── Option B: Custom Handler Pattern ────────────────────────────────
    // Delegates to a single handler class that routes by context.
    //
    // {SObject}TriggerHandler handler = new {SObject}TriggerHandler();
    //
    // if (Trigger.isBefore) {
    //     if (Trigger.isInsert) {
    //         handler.beforeInsert(Trigger.new);
    //     } else if (Trigger.isUpdate) {
    //         handler.beforeUpdate(Trigger.new, Trigger.oldMap);
    //     } else if (Trigger.isDelete) {
    //         handler.beforeDelete(Trigger.old, Trigger.oldMap);
    //     }
    // } else if (Trigger.isAfter) {
    //     if (Trigger.isInsert) {
    //         handler.afterInsert(Trigger.new, Trigger.newMap);
    //     } else if (Trigger.isUpdate) {
    //         handler.afterUpdate(Trigger.new, Trigger.oldMap);
    //     } else if (Trigger.isDelete) {
    //         handler.afterDelete(Trigger.old, Trigger.oldMap);
    //     } else if (Trigger.isUndelete) {
    //         handler.afterUndelete(Trigger.new, Trigger.newMap);
    //     }
    // }

    // TODO: Uncomment one option above and remove the other
}
