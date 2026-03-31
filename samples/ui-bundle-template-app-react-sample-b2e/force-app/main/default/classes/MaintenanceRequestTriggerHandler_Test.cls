/**
 * Test class for MaintenanceRequestTriggerHandler
 * Validates automatic worker assignment, status updates to Assigned, and scheduled date setting
 */
@isTest
private class MaintenanceRequestTriggerHandler_Test {

    /**
     * Setup test data for all test methods
     */
    @testSetup
    static void setupTestData() {
        // Create test maintenance workers with different specialties
        List<Maintenance_Worker__c> workers = new List<Maintenance_Worker__c>{
            new Maintenance_Worker__c(
                Name = 'John Plumber',
                Type__c = 'Plumbing',
                IsActive__c = true,
                Rating__c = 4.5,
                Phone__c = '555-0001'
            ),
            new Maintenance_Worker__c(
                Name = 'Jane Electrician',
                Type__c = 'Electrical',
                IsActive__c = true,
                Rating__c = 4.8,
                Phone__c = '555-0002'
            ),
            new Maintenance_Worker__c(
                Name = 'Bob HVAC',
                Type__c = 'HVAC (Heating & Cooling)',
                IsActive__c = true,
                Rating__c = 4.2,
                Phone__c = '555-0003'
            ),
            new Maintenance_Worker__c(
                Name = 'Alice Appliance',
                Type__c = 'Appliance Repair',
                IsActive__c = true,
                Rating__c = 4.7,
                Phone__c = '555-0004'
            ),
            new Maintenance_Worker__c(
                Name = 'Charlie Pest',
                Type__c = 'Pest Control',
                IsActive__c = true,
                Rating__c = 4.3,
                Phone__c = '555-0005'
            ),
            new Maintenance_Worker__c(
                Name = 'Inactive Worker',
                Type__c = 'Plumbing',
                IsActive__c = false,
                Rating__c = 5.0,
                Phone__c = '555-0006'
            )
        };
        insert workers;
    }

    /**
     * Test that plumbing requests are assigned to plumbing workers
     */
    @isTest
    static void testPlumbingRequestAssignment() {
        // Query for plumbing worker
        Maintenance_Worker__c plumber = [SELECT Id FROM Maintenance_Worker__c WHERE Type__c = 'Plumbing' AND IsActive__c = true LIMIT 1];

        Test.startTest();
        Maintenance_Request__c request = new Maintenance_Request__c(
            Type__c = 'Plumbing',
            Description__c = 'Leaky faucet in bathroom',
            Priority__c = 'Standard'
        );
        insert request;
        Test.stopTest();

        // Verify assignment
        Maintenance_Request__c insertedRequest = [
            SELECT Id, Assigned_Worker__c, Status__c, Scheduled__c, Type__c
            FROM Maintenance_Request__c
            WHERE Id = :request.Id
        ];

        System.assertEquals(plumber.Id, insertedRequest.Assigned_Worker__c, 'Worker should be assigned');
        System.assertEquals('Assigned', insertedRequest.Status__c, 'Status should be Assigned');
        System.assertNotEquals(null, insertedRequest.Scheduled__c, 'Scheduled date should be set');

        // Verify scheduled date is approximately 3 days from now (within 1 minute tolerance)
        DateTime expectedDate = DateTime.now().addDays(3);
        Long timeDiff = Math.abs(insertedRequest.Scheduled__c.getTime() - expectedDate.getTime());
        System.assert(timeDiff < 60000, 'Scheduled date should be 3 days from now');
    }

    /**
     * Test that electrical requests are assigned to electrical workers
     */
    @isTest
    static void testElectricalRequestAssignment() {
        Maintenance_Worker__c electrician = [SELECT Id FROM Maintenance_Worker__c WHERE Type__c = 'Electrical' AND IsActive__c = true LIMIT 1];

        Test.startTest();
        Maintenance_Request__c request = new Maintenance_Request__c(
            Type__c = 'Electrical',
            Description__c = 'Outlet not working',
            Priority__c = 'High'
        );
        insert request;
        Test.stopTest();

        Maintenance_Request__c insertedRequest = [
            SELECT Id, Assigned_Worker__c, Status__c
            FROM Maintenance_Request__c
            WHERE Id = :request.Id
        ];

        System.assertEquals(electrician.Id, insertedRequest.Assigned_Worker__c, 'Electrician should be assigned');
        System.assertEquals('Assigned', insertedRequest.Status__c, 'Status should be Assigned');
    }

    /**
     * Test that HVAC requests are assigned to HVAC workers
     */
    @isTest
    static void testHVACRequestAssignment() {
        Maintenance_Worker__c hvacWorker = [SELECT Id FROM Maintenance_Worker__c WHERE Type__c = 'HVAC (Heating & Cooling)' AND IsActive__c = true LIMIT 1];

        Test.startTest();
        Maintenance_Request__c request = new Maintenance_Request__c(
            Type__c = 'HVAC',
            Description__c = 'AC not cooling',
            Priority__c = 'High'
        );
        insert request;
        Test.stopTest();

        Maintenance_Request__c insertedRequest = [
            SELECT Id, Assigned_Worker__c, Status__c
            FROM Maintenance_Request__c
            WHERE Id = :request.Id
        ];

        System.assertEquals(hvacWorker.Id, insertedRequest.Assigned_Worker__c, 'HVAC worker should be assigned');
        System.assertEquals('Assigned', insertedRequest.Status__c, 'Status should be Assigned');
    }

    /**
     * Test that appliance requests are assigned to appliance repair workers
     */
    @isTest
    static void testApplianceRequestAssignment() {
        Maintenance_Worker__c applianceWorker = [SELECT Id FROM Maintenance_Worker__c WHERE Type__c = 'Appliance Repair' AND IsActive__c = true LIMIT 1];

        Test.startTest();
        Maintenance_Request__c request = new Maintenance_Request__c(
            Type__c = 'Appliance',
            Description__c = 'Dishwasher not draining',
            Priority__c = 'Standard'
        );
        insert request;
        Test.stopTest();

        Maintenance_Request__c insertedRequest = [
            SELECT Id, Assigned_Worker__c, Status__c
            FROM Maintenance_Request__c
            WHERE Id = :request.Id
        ];

        System.assertEquals(applianceWorker.Id, insertedRequest.Assigned_Worker__c, 'Appliance worker should be assigned');
        System.assertEquals('Assigned', insertedRequest.Status__c, 'Status should be Assigned');
    }

    /**
     * Test that pest requests are assigned to pest control workers
     */
    @isTest
    static void testPestRequestAssignment() {
        Maintenance_Worker__c pestWorker = [SELECT Id FROM Maintenance_Worker__c WHERE Type__c = 'Pest Control' AND IsActive__c = true LIMIT 1];

        Test.startTest();
        Maintenance_Request__c request = new Maintenance_Request__c(
            Type__c = 'Pest',
            Description__c = 'Ants in kitchen',
            Priority__c = 'Standard'
        );
        insert request;
        Test.stopTest();

        Maintenance_Request__c insertedRequest = [
            SELECT Id, Assigned_Worker__c, Status__c
            FROM Maintenance_Request__c
            WHERE Id = :request.Id
        ];

        System.assertEquals(pestWorker.Id, insertedRequest.Assigned_Worker__c, 'Pest control worker should be assigned');
        System.assertEquals('Assigned', insertedRequest.Status__c, 'Status should be Assigned');
    }

    /**
     * Test bulk insert with multiple request types
     */
    @isTest
    static void testBulkRequestAssignment() {
        Test.startTest();
        List<Maintenance_Request__c> requests = new List<Maintenance_Request__c>{
            new Maintenance_Request__c(Type__c = 'Plumbing', Description__c = 'Leak 1', Priority__c = 'High'),
            new Maintenance_Request__c(Type__c = 'Electrical', Description__c = 'Issue 1', Priority__c = 'Standard'),
            new Maintenance_Request__c(Type__c = 'Plumbing', Description__c = 'Leak 2', Priority__c = 'Standard'),
            new Maintenance_Request__c(Type__c = 'HVAC', Description__c = 'AC Issue', Priority__c = 'High'),
            new Maintenance_Request__c(Type__c = 'Appliance', Description__c = 'Fridge Issue', Priority__c = 'Standard')
        };
        insert requests;
        Test.stopTest();

        List<Maintenance_Request__c> insertedRequests = [
            SELECT Id, Assigned_Worker__c, Status__c, Type__c
            FROM Maintenance_Request__c
            WHERE Id IN :requests
        ];

        // Verify all requests were assigned
        for (Maintenance_Request__c req : insertedRequests) {
            System.assertNotEquals(null, req.Assigned_Worker__c, 'All requests should have assigned workers');
            System.assertEquals('Assigned', req.Status__c, 'All requests should be Assigned');
        }

        System.assertEquals(5, insertedRequests.size(), 'All 5 requests should be inserted');
    }

    /**
     * Test that requests without type are not assigned
     */
    @isTest
    static void testRequestWithoutType() {
        Test.startTest();
        Maintenance_Request__c request = new Maintenance_Request__c(
            Description__c = 'General maintenance',
            Priority__c = 'Standard'
        );
        insert request;
        Test.stopTest();

        Maintenance_Request__c insertedRequest = [
            SELECT Id, Assigned_Worker__c, Status__c
            FROM Maintenance_Request__c
            WHERE Id = :request.Id
        ];

        System.assertEquals(null, insertedRequest.Assigned_Worker__c, 'Worker should not be assigned without type');
    }

    /**
     * Test that inactive workers are not assigned
     */
    @isTest
    static void testInactiveWorkerNotAssigned() {
        // Delete all active plumbing workers
        delete [SELECT Id FROM Maintenance_Worker__c WHERE Type__c = 'Plumbing' AND IsActive__c = true];

        Test.startTest();
        Maintenance_Request__c request = new Maintenance_Request__c(
            Type__c = 'Plumbing',
            Description__c = 'Emergency leak',
            Priority__c = 'High'
        );
        insert request;
        Test.stopTest();

        Maintenance_Request__c insertedRequest = [
            SELECT Id, Assigned_Worker__c, Status__c
            FROM Maintenance_Request__c
            WHERE Id = :request.Id
        ];

        System.assertEquals(null, insertedRequest.Assigned_Worker__c, 'Inactive worker should not be assigned');
    }

    /**
     * Test that requests with non-New status are not automatically processed
     */
    @isTest
    static void testNonNewStatusNotProcessed() {
        // Query for plumbing worker
        Maintenance_Worker__c plumber = [SELECT Id FROM Maintenance_Worker__c WHERE Type__c = 'Plumbing' AND IsActive__c = true LIMIT 1];

        Test.startTest();
        // Create a request with status explicitly set to 'In Progress'
        Maintenance_Request__c request = new Maintenance_Request__c(
            Type__c = 'Plumbing',
            Description__c = 'Manually assigned request',
            Priority__c = 'Standard',
            Status__c = 'In Progress'
        );
        insert request;
        Test.stopTest();

        // Verify the request was not processed by trigger (no worker assigned)
        Maintenance_Request__c insertedRequest = [
            SELECT Id, Assigned_Worker__c, Status__c, Scheduled__c
            FROM Maintenance_Request__c
            WHERE Id = :request.Id
        ];

        System.assertEquals(null, insertedRequest.Assigned_Worker__c, 'Worker should not be auto-assigned for non-New status');
        System.assertEquals('In Progress', insertedRequest.Status__c, 'Status should remain as originally set');
        System.assertEquals(null, insertedRequest.Scheduled__c, 'Scheduled date should not be set by trigger');
    }
}