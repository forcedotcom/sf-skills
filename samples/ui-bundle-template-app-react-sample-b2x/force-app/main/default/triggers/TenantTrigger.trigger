trigger TenantTrigger on Tenant__c (after insert, after update) {
    if (Trigger.isAfter && Trigger.isInsert) {
        TenantTriggerHandler.assignTenantMaintenanceAccess(Trigger.new, null);
    }
    if (Trigger.isAfter && Trigger.isUpdate) {
        TenantTriggerHandler.assignTenantMaintenanceAccess(Trigger.new, Trigger.oldMap);
    }
}
