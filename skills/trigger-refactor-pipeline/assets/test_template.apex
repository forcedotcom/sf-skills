/**
 * Test class template for trigger handlers
 * 
 * INSTRUCTIONS:
 * 1. Replace [ObjectName] with your SObject (e.g., Opportunity)
 * 2. Replace [HandlerClass] with your handler class name
 * 3. Implement the setupTestData() method with your test records
 * 4. Add specific test methods for each handler method
 * 5. Ensure 100% code coverage
 */
@IsTest
private class [ObjectName]TriggerHandlerTest {
    
    /**
     * Setup test data that all test methods can use
     */
    @TestSetup
    static void setupTestData() {
        // TODO: Create test records here
        // Example:
        // List<Opportunity> testOpps = new List<Opportunity>();
        // for (Integer i = 0; i < 10; i++) {
        //     testOpps.add(new Opportunity(
        //         Name = 'Test Opp ' + i,
        //         StageName = 'Prospecting',
        //         CloseDate = Date.today().addDays(30),
        //         Amount = 5000
        //     ));
        // }
        // insert testOpps;
    }
    
    /**
     * Test beforeInsert handler - Positive case
     */
    @IsTest
    static void testBeforeInsert_Positive() {
        Test.startTest();
        
        // TODO: Create valid test records
        // List<Opportunity> testRecords = new List<Opportunity>{
        //     new Opportunity(
        //         Name = 'Valid Opp',
        //         StageName = 'Prospecting',
        //         CloseDate = Date.today().addDays(30),
        //         Amount = 10000
        //     )
        // };
        
        // Insert should succeed
        // insert testRecords;
        
        Test.stopTest();
        
        // TODO: Add assertions
        // List<Opportunity> inserted = [SELECT Id, Name FROM Opportunity WHERE Name = 'Valid Opp'];
        // System.Assert.areEqual(1, inserted.size(), 'Should insert 1 record');
    }
    
    /**
     * Test beforeInsert handler - Negative case
     */
    @IsTest
    static void testBeforeInsert_Negative() {
        Test.startTest();
        
        Boolean exceptionThrown = false;
        
        try {
            // TODO: Create invalid test records that should fail validation
            // List<Opportunity> testRecords = new List<Opportunity>{
            //     new Opportunity(
            //         Name = 'Invalid Opp',
            //         StageName = 'Closed Won',
            //         CloseDate = Date.today(),
            //         Amount = 500  // Below minimum
            //     )
            // };
            
            // insert testRecords;
            
        } catch (DmlException e) {
            exceptionThrown = true;
            // TODO: Assert error message
            // System.Assert.isTrue(e.getMessage().contains('must have Amount'),
            //     'Should throw validation error');
        }
        
        Test.stopTest();
        
        // System.Assert.isTrue(exceptionThrown, 'Should have thrown an exception');
    }
    
    /**
     * Test beforeUpdate handler - Positive case
     */
    @IsTest
    static void testBeforeUpdate_Positive() {
        // TODO: Query existing test data from @TestSetup
        // List<Opportunity> testOpps = [SELECT Id, StageName, Description FROM Opportunity LIMIT 1];
        
        Test.startTest();
        
        // TODO: Update records to trigger handler logic
        // testOpps[0].StageName = 'Qualification';
        // update testOpps;
        
        Test.stopTest();
        
        // TODO: Add assertions
        // Opportunity updated = [SELECT Description FROM Opportunity WHERE Id = :testOpps[0].Id];
        // System.Assert.isTrue(updated.Description.contains('Stage changed'),
        //     'Description should be updated');
    }
    
    /**
     * Test beforeUpdate handler - Negative case
     */
    @IsTest
    static void testBeforeUpdate_Negative() {
        // TODO: Implement negative test for beforeUpdate
        Test.startTest();
        
        // TODO: Attempt update that should fail
        
        Test.stopTest();
        
        // TODO: Assert failure occurred
    }
    
    /**
     * Test afterInsert handler - Positive case
     */
    @IsTest
    static void testAfterInsert_Positive() {
        Test.startTest();
        
        // TODO: Create and insert records
        
        Test.stopTest();
        
        // TODO: Query for related records created by handler
        // List<Task> createdTasks = [SELECT Id FROM Task];
        // System.Assert.areEqual(1, createdTasks.size(), 'Should create 1 task');
    }
    
    /**
     * Test afterUpdate handler - Positive case
     */
    @IsTest
    static void testAfterUpdate_Positive() {
        // TODO: Query existing test data
        // List<Opportunity> testOpps = [SELECT Id, StageName FROM Opportunity LIMIT 1];
        
        Test.startTest();
        
        // TODO: Update to trigger after-update logic
        // testOpps[0].StageName = 'Closed Won';
        // update testOpps;
        
        Test.stopTest();
        
        // TODO: Query for side effects (e.g., Tasks created)
        // List<Task> tasks = [SELECT Id, Subject FROM Task WHERE WhatId = :testOpps[0].Id];
        // System.Assert.areEqual(1, tasks.size(), 'Should create 1 task');
        // System.Assert.areEqual('Send thank-you', tasks[0].Subject);
    }
    
    /**
     * Test bulk operations - 200+ records
     * Critical for validating bulkification
     */
    @IsTest
    static void testBulkInsert() {
        Test.startTest();
        
        // TODO: Create 200+ records
        // List<Opportunity> bulkOpps = new List<Opportunity>();
        // for (Integer i = 0; i < 200; i++) {
        //     bulkOpps.add(new Opportunity(
        //         Name = 'Bulk Opp ' + i,
        //         StageName = 'Prospecting',
        //         CloseDate = Date.today().addDays(30),
        //         Amount = 10000
        //     ));
        // }
        
        // insert bulkOpps;
        
        Test.stopTest();
        
        // TODO: Assert all records inserted successfully
        // List<Opportunity> inserted = [SELECT Id FROM Opportunity WHERE Name LIKE 'Bulk Opp%'];
        // System.Assert.areEqual(200, inserted.size(), 'Should insert all 200 records');
    }
    
    /**
     * Test bulk update with mixed scenarios
     * Some records qualify for logic, others don't
     */
    @IsTest
    static void testBulkUpdate_Mixed() {
        // Create test data
        List<Opportunity> testOpps = new List<Opportunity>();
        for (Integer i = 0; i < 50; i++) {
            testOpps.add(new Opportunity(
                Name = 'Bulk Update Opp ' + i,
                StageName = 'Prospecting',
                CloseDate = Date.today().addDays(30),
                Amount = 10000
            ));
        }
        insert testOpps;
        
        Test.startTest();
        
        // Update half to trigger logic, half to not trigger
        for (Integer i = 0; i < testOpps.size(); i++) {
            if (Math.mod(i, 2) == 0) {
                // TODO: Set condition that triggers handler logic
                // testOpps[i].StageName = 'Closed Won';
            } else {
                // TODO: Set condition that doesn't trigger handler logic
                // testOpps[i].Amount = 15000;
            }
        }
        
        // update testOpps;
        
        Test.stopTest();
        
        // TODO: Assert only qualifying records triggered side effects
        // List<Task> tasks = [SELECT Id FROM Task WHERE WhatId IN :testOpps];
        // System.Assert.areEqual(25, tasks.size(), 'Should create tasks for 25 qualifying records');
    }
    
    /**
     * Test governor limits are not exceeded
     */
    @IsTest
    static void testGovernorLimits() {
        Test.startTest();
        
        // TODO: Create maximum allowed records
        // List<Opportunity> maxOpps = new List<Opportunity>();
        // for (Integer i = 0; i < 200; i++) {
        //     maxOpps.add(new Opportunity(
        //         Name = 'Limit Test ' + i,
        //         StageName = 'Closed Won',
        //         CloseDate = Date.today(),
        //         Amount = 10000
        //     ));
        // }
        
        // insert maxOpps;
        
        Test.stopTest();
        
        // Assert we're under governor limits
        System.Assert.isTrue(Limits.getDmlStatements() < Limits.getLimitDmlStatements(),
            'Should not exceed DML statement limit');
        System.Assert.isTrue(Limits.getQueries() < Limits.getLimitQueries(),
            'Should not exceed SOQL query limit');
    }
    
    /**
     * Test with null or empty collections
     * Ensures handler doesn't break with edge cases
     */
    @IsTest
    static void testWithEmptyCollection() {
        Test.startTest();
        
        // TODO: Call handler methods with empty lists
        // OpportunityTriggerHandler handler = new OpportunityTriggerHandler();
        // handler.beforeInsert(new List<Opportunity>());
        
        Test.stopTest();
        
        // If we get here without exception, test passes
        System.Assert.isTrue(true, 'Handler should handle empty collections gracefully');
    }
    
    /**
     * Helper method to create test data inline
     * Use when @TestSetup is not sufficient
     */
    private static List<Opportunity> createTestOpportunities(Integer count) {
        List<Opportunity> testOpps = new List<Opportunity>();
        
        for (Integer i = 0; i < count; i++) {
            testOpps.add(new Opportunity(
                Name = 'Test Opp ' + i,
                StageName = 'Prospecting',
                CloseDate = Date.today().addDays(30),
                Amount = 10000
            ));
        }
        
        return testOpps;
    }
    
    /**
     * Helper method to assert task creation
     */
    private static void assertTasksCreated(List<Id> oppIds, Integer expectedCount, String subject) {
        List<Task> tasks = [
            SELECT Id, Subject, WhatId
            FROM Task
            WHERE WhatId IN :oppIds
        ];
        
        System.Assert.areEqual(expectedCount, tasks.size(),
            'Should create ' + expectedCount + ' task(s)');
        
        if (expectedCount > 0) {
            System.Assert.areEqual(subject, tasks[0].Subject,
                'Task subject should match');
        }
    }
}
