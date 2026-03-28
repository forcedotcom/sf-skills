/**
 * Assigns Tenant_Maintenance_Access permission set to users linked to Tenant__c records.
 * When a Tenant is created or updated with User__c set, the linked user gets the permission set.
 */
public with sharing class TenantTriggerHandler {

    private static final String PERMISSION_SET_NAME = 'Tenant_Maintenance_Access';

    /**
     * Assign Tenant_Maintenance_Access to each user linked via Tenant__c.User__c.
     * Insert: all records with User__c set.
     * Update: records where User__c was set or changed to a non-null value.
     */
    public static void assignTenantMaintenanceAccess(List<Tenant__c> newList, Map<Id, Tenant__c> oldMap) {
        Set<Id> userIds = new Set<Id>();
        for (Tenant__c t : newList) {
            if (t.User__c == null) {
                continue;
            }
            if (oldMap == null) {
                userIds.add(t.User__c);
            } else {
                Tenant__c oldRec = oldMap.get(t.Id);
                if (oldRec == null || oldRec.User__c != t.User__c) {
                    userIds.add(t.User__c);
                }
            }
        }
        if (userIds.isEmpty()) {
            return;
        }

        List<PermissionSet> permSets = [
            SELECT Id
            FROM PermissionSet
            WHERE Name = :PERMISSION_SET_NAME
            AND IsOwnedByProfile = false
            LIMIT 1
        ];
        if (permSets.isEmpty()) {
            return;
        }
        Id permSetId = permSets[0].Id;

        Set<Id> alreadyAssigned = new Set<Id>();
        for (PermissionSetAssignment psa : [
            SELECT AssigneeId
            FROM PermissionSetAssignment
            WHERE PermissionSetId = :permSetId
            AND AssigneeId IN :userIds
        ]) {
            alreadyAssigned.add(psa.AssigneeId);
        }

        List<PermissionSetAssignment> toInsert = new List<PermissionSetAssignment>();
        for (Id uid : userIds) {
            if (alreadyAssigned.contains(uid)) {
                continue;
            }
            toInsert.add(new PermissionSetAssignment(
                PermissionSetId = permSetId,
                AssigneeId = uid
            ));
        }
        if (!toInsert.isEmpty()) {
            insert toInsert;
        }
    }
}
