/**
 * Bulk testing template for trigger and service validation
 *              Tests with 251+ records to ensure bulkification compliance.
 *              251 records crosses the 200-record trigger batch boundary.
 */
@IsTest
private class {{ClassName}}BulkTest {

    // Record counts for different test scenarios
    private static final Integer BULK_SIZE = 251;       // Crosses 200-batch boundary
    private static final Integer LARGE_BULK_SIZE = 501; // Multiple batch boundaries
    private static final Integer SINGLE_BATCH = 200;    // Single batch (edge case)

    // ═══════════════════════════════════════════════════════════════════════════
    // BULK INSERT TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests bulk insert with 251 records
     *              Verifies trigger handles multiple batch chunks correctly
     */
    @IsTest
    static void testBulkInsert_251Records_AllProcessed() {
        // GIVEN
        List<{{ObjectName}}> records = TestDataFactory.create{{ObjectName}}s(BULK_SIZE);

        // WHEN
        Test.startTest();
        Database.SaveResult[] results = Database.insert(records, false);
        Test.stopTest();

        // THEN - All records should be successfully inserted
        Integer successCount = 0;
        Integer failCount = 0;
        for (Database.SaveResult sr : results) {
            if (sr.isSuccess()) {
                successCount++;
            } else {
                failCount++;
                System.debug('Insert failed: ' + sr.getErrors()[0].getMessage());
            }
        }

        Assert.areEqual(BULK_SIZE, successCount,
            'All ' + BULK_SIZE + ' records should insert successfully');
        Assert.areEqual(0, failCount, 'No records should fail');

        // Verify governor limits
        assertGovernorLimitsNotExceeded();
    }

    /**
     * Tests bulk insert at exact batch boundary (200 records)
     */
    @IsTest
    static void testBulkInsert_ExactBatchSize_AllProcessed() {
        // GIVEN
        List<{{ObjectName}}> records = TestDataFactory.create{{ObjectName}}s(SINGLE_BATCH);

        // WHEN
        Test.startTest();
        insert records;
        Test.stopTest();

        // THEN
        Integer count = [SELECT COUNT() FROM {{ObjectName}}];
        Assert.areEqual(SINGLE_BATCH, count,
            'All ' + SINGLE_BATCH + ' records should be inserted');
        assertGovernorLimitsNotExceeded();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // BULK UPDATE TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests bulk update with 251 records
     *              Verifies update triggers handle multiple batches
     */
    @IsTest
    static void testBulkUpdate_251Records_AllUpdated() {
        // GIVEN - Insert records first
        List<{{ObjectName}}> records = TestDataFactory.create{{ObjectName}}s(BULK_SIZE);
        insert records;

        // Modify all records
        for ({{ObjectName}} rec : records) {
            // TODO: Update fields that trigger logic
            // rec.SomeField__c = 'Updated Value';
        }

        // WHEN
        Test.startTest();
        Database.SaveResult[] results = Database.update(records, false);
        Test.stopTest();

        // THEN
        Integer successCount = 0;
        for (Database.SaveResult sr : results) {
            if (sr.isSuccess()) {
                successCount++;
            }
        }

        Assert.areEqual(BULK_SIZE, successCount,
            'All ' + BULK_SIZE + ' records should update successfully');
        assertGovernorLimitsNotExceeded();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // BULK DELETE TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests bulk delete with 251 records
     *              Verifies delete triggers handle cleanup correctly
     */
    @IsTest
    static void testBulkDelete_251Records_AllDeleted() {
        // GIVEN
        List<{{ObjectName}}> records = TestDataFactory.create{{ObjectName}}s(BULK_SIZE);
        insert records;

        // WHEN
        Test.startTest();
        Database.DeleteResult[] results = Database.delete(records, false);
        Test.stopTest();

        // THEN
        Integer successCount = 0;
        for (Database.DeleteResult dr : results) {
            if (dr.isSuccess()) {
                successCount++;
            }
        }

        Assert.areEqual(BULK_SIZE, successCount,
            'All ' + BULK_SIZE + ' records should delete successfully');

        Integer remainingCount = [SELECT COUNT() FROM {{ObjectName}}];
        Assert.areEqual(0, remainingCount, 'No records should remain');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MIXED DML BULK TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests mixed operations in bulk
     *              Verifies partial success scenarios are handled
     */
    @IsTest
    static void testBulkMixedOperations_PartialSuccess() {
        // GIVEN - Some valid, some invalid records
        List<{{ObjectName}}> validRecords = TestDataFactory.create{{ObjectName}}s(200);
        List<{{ObjectName}}> invalidRecords = new List<{{ObjectName}}>();

        // Create invalid records (missing required fields or validation failures)
        for (Integer i = 0; i < 51; i++) {
            invalidRecords.add(new {{ObjectName}}(
                // TODO: Set up record that will fail validation
            ));
        }

        List<{{ObjectName}}> allRecords = new List<{{ObjectName}}>();
        allRecords.addAll(validRecords);
        allRecords.addAll(invalidRecords);

        // WHEN - Insert with allOrNone = false
        Test.startTest();
        Database.SaveResult[] results = Database.insert(allRecords, false);
        Test.stopTest();

        // THEN - Count successes and failures
        Integer successCount = 0;
        Integer failCount = 0;
        for (Database.SaveResult sr : results) {
            if (sr.isSuccess()) {
                successCount++;
            } else {
                failCount++;
            }
        }

        // Verify partial success handled correctly
        Assert.isTrue(successCount > 0, 'Some records should succeed');
        // Note: Uncomment if you expect failures
        // Assert.isTrue(failCount > 0, 'Some records should fail validation');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // GOVERNOR LIMIT VERIFICATION
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Helper method to verify governor limits not exceeded
     *              Call after Test.stopTest() to check limit usage
     */
    private static void assertGovernorLimitsNotExceeded() {
        // SOQL Queries (limit: 100)
        Assert.isTrue(Limits.getQueries() < 90,
            'SOQL queries approaching limit: ' + Limits.getQueries() + '/100');

        // DML Statements (limit: 150)
        Assert.isTrue(Limits.getDmlStatements() < 140,
            'DML statements approaching limit: ' + Limits.getDmlStatements() + '/150');

        // DML Rows (limit: 10,000)
        Assert.isTrue(Limits.getDmlRows() < 9500,
            'DML rows approaching limit: ' + Limits.getDmlRows() + '/10000');

        // Heap Size (limit: 6MB sync, 12MB async)
        Assert.isTrue(Limits.getHeapSize() < 5000000,
            'Heap size approaching limit: ' + Limits.getHeapSize() + '/6000000');

        // CPU Time (limit: 10,000ms sync, 60,000ms async)
        Assert.isTrue(Limits.getCpuTime() < 9000,
            'CPU time approaching limit: ' + Limits.getCpuTime() + '/10000');

        System.debug('═══════════════════════════════════════════════════════');
        System.debug('GOVERNOR LIMIT USAGE:');
        System.debug('  SOQL Queries: ' + Limits.getQueries() + '/100');
        System.debug('  DML Statements: ' + Limits.getDmlStatements() + '/150');
        System.debug('  DML Rows: ' + Limits.getDmlRows() + '/10000');
        System.debug('  Heap Size: ' + Limits.getHeapSize() + '/6000000');
        System.debug('  CPU Time: ' + Limits.getCpuTime() + 'ms /10000ms');
        System.debug('═══════════════════════════════════════════════════════');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // STRESS TESTS (Optional - Run sparingly)
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Stress test with 501 records (multiple batch boundaries)
     *              Use sparingly - consumes significant test execution time
     */
    @IsTest
    static void testStressTest_501Records_AllProcessed() {
        // GIVEN
        List<{{ObjectName}}> records = TestDataFactory.create{{ObjectName}}s(LARGE_BULK_SIZE);

        // WHEN
        Test.startTest();
        insert records;
        Test.stopTest();

        // THEN
        Integer count = [SELECT COUNT() FROM {{ObjectName}}];
        Assert.areEqual(LARGE_BULK_SIZE, count,
            'All ' + LARGE_BULK_SIZE + ' records should be processed');
        assertGovernorLimitsNotExceeded();
    }
}
