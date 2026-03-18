trigger MaintenanceRequestTrigger on Maintenance_Request__c (before insert) {
    if (Trigger.isBefore && Trigger.isInsert) {
        MaintenanceRequestTriggerHandler.handleBeforeInsert(Trigger.new);
    }
}