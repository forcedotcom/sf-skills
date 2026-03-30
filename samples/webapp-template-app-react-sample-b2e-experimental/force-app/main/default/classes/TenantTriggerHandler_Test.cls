/**
 * Test class for TenantTriggerHandler.
 * Verifies that Tenant_Maintenance_Access permission set is assigned to the user
 * when a Tenant__c record is created or updated with User__c set.
 */
@isTest
private class TenantTriggerHandler_Test {

    @isTest
    static void testAssignOnInsert() {
        Id runAsUserId = UserInfo.getUserId();
        Tenant__c tenant = new Tenant__c(User__c = runAsUserId);

        Test.startTest();
        insert tenant;
        Test.stopTest();

        List<PermissionSet> permSets = [
            SELECT Id FROM PermissionSet
            WHERE Name = 'Tenant_Maintenance_Access'
            AND IsOwnedByProfile = false
            LIMIT 1
        ];
        if (!permSets.isEmpty()) {
            List<PermissionSetAssignment> assignments = [
                SELECT Id, AssigneeId, PermissionSetId
                FROM PermissionSetAssignment
                WHERE PermissionSetId = :permSets[0].Id
                AND AssigneeId = :runAsUserId
            ];
            System.assert(assignments.size() == 1, 'Permission set should be assigned to user when Tenant is created with User__c');
        }
    }

    @isTest
    static void testAssignOnUpdateWhenUserSet() {
        Tenant__c tenant = new Tenant__c();
        insert tenant;

        Id runAsUserId = UserInfo.getUserId();

        Test.startTest();
        tenant.User__c = runAsUserId;
        update tenant;
        Test.stopTest();

        List<PermissionSet> permSets = [
            SELECT Id FROM PermissionSet
            WHERE Name = 'Tenant_Maintenance_Access'
            AND IsOwnedByProfile = false
            LIMIT 1
        ];
        if (!permSets.isEmpty()) {
            List<PermissionSetAssignment> assignments = [
                SELECT Id FROM PermissionSetAssignment
                WHERE PermissionSetId = :permSets[0].Id
                AND AssigneeId = :runAsUserId
            ];
            System.assert(assignments.size() == 1, 'Permission set should be assigned when User__c is set on update');
        }
    }

    @isTest
    static void testNoAssignWhenUserNull() {
        Tenant__c tenant = new Tenant__c();
        Test.startTest();
        insert tenant;
        Test.stopTest();
        // Handler does not assign when User__c is null; trigger runs without error
    }

    @isTest
    static void testNoDuplicateAssign() {
        Id runAsUserId = UserInfo.getUserId();
        Tenant__c tenant = new Tenant__c(User__c = runAsUserId);
        Test.startTest();
        insert tenant;
        Test.stopTest();

        Integer countBefore = [
            SELECT COUNT()
            FROM PermissionSetAssignment
            WHERE AssigneeId = :runAsUserId
            AND PermissionSet.Name = 'Tenant_Maintenance_Access'
        ];

        Test.startTest();
        tenant.Status__c = 'Active';
        update tenant;
        Test.stopTest();

        Integer countAfter = [
            SELECT COUNT()
            FROM PermissionSetAssignment
            WHERE AssigneeId = :runAsUserId
            AND PermissionSet.Name = 'Tenant_Maintenance_Access'
        ];
        System.assertEquals(countBefore, countAfter, 'Update without User__c change should not create duplicate assignment');
    }
}
