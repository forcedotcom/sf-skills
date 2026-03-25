/**
 * Trigger Action for {SObject}: {ActionDescription}.
 *              Implements TriggerAction.{Context} from the Trigger Actions Framework.
 *              Register via Trigger_Action__mdt custom metadata to activate.
 *
 * @example
 * Trigger_Action__mdt record:
 *   Object__c           = {SObject}
 *   Apex_Class_Name__c  = TA_{SObject}_{ActionName}
 *   Before_Insert__c    = true
 *   Order__c            = 10
 */
public with sharing class TA_{SObject}_{ActionName} implements TriggerAction.BeforeInsert {

    /**
     * Executes before insert logic for {SObject} records
     * @param newList List of new {SObject} records being inserted
     */
    public void beforeInsert(List<{SObject}> newList) {
        if (newList == null || newList.isEmpty()) {
            return;
        }

        for ({SObject} record : newList) {
            // TODO: Implement action logic
        }
    }
}

// ─── ADDITIONAL CONTEXT EXAMPLES ─────────────────────────────────────────
//
// Before Update (access both old and new values):
//
// public class TA_{SObject}_{ActionName} implements TriggerAction.BeforeUpdate {
//     public void beforeUpdate(List<{SObject}> newList, List<{SObject}> oldList) {
//         Map<Id, {SObject}> oldMap = new Map<Id, {SObject}>(oldList);
//         for ({SObject} record : newList) {
//             {SObject} oldRecord = oldMap.get(record.Id);
//             if (record.Status__c != oldRecord.Status__c) {
//                 // Field changed — process
//             }
//         }
//     }
// }
//
// After Insert (create related records, enqueue async work):
//
// public class TA_{SObject}_{ActionName} implements TriggerAction.AfterInsert {
//     public void afterInsert(List<{SObject}> newList) {
//         // Collect IDs, query related data, perform DML outside loop
//     }
// }
//
// Multiple contexts in one class:
//
// public class TA_{SObject}_{ActionName}
//     implements TriggerAction.BeforeInsert, TriggerAction.BeforeUpdate {
//
//     public void beforeInsert(List<{SObject}> newList) { apply(newList); }
//     public void beforeUpdate(List<{SObject}> newList, List<{SObject}> oldList) { apply(newList); }
//
//     private void apply(List<{SObject}> records) {
//         // Shared logic
//     }
// }
