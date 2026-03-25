/**
 * Test class for {{ClassName}}
 *              Tests core functionality with positive, negative, and bulk scenarios.
 * @coverage    Target: 90%+
 */
@IsTest
private class {{ClassName}}Test {

    // ═══════════════════════════════════════════════════════════════════════════
    // TEST DATA SETUP
    // ═══════════════════════════════════════════════════════════════════════════

    @TestSetup
    static void setupTestData() {
        // Create test data using Test Data Factory pattern
        // This data is available to all test methods and rolled back after each
        List<{{ObjectName}}> records = TestDataFactory.create{{ObjectName}}s(5);
        insert records;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // POSITIVE TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests successful {{methodUnderTest}} with valid input
     */
    @IsTest
    static void test{{MethodUnderTest}}_ValidInput_Success() {
        // ─────────────────────────────────────────────────────────────────────
        // GIVEN - Set up test conditions
        // ─────────────────────────────────────────────────────────────────────
        {{ObjectName}} testRecord = [SELECT Id, Name FROM {{ObjectName}} LIMIT 1];
        // TODO: Add any additional setup needed

        // ─────────────────────────────────────────────────────────────────────
        // WHEN - Execute the method under test
        // ─────────────────────────────────────────────────────────────────────
        Test.startTest();
        {{ReturnType}} result = {{ClassName}}.{{methodUnderTest}}(testRecord);
        Test.stopTest();

        // ─────────────────────────────────────────────────────────────────────
        // THEN - Verify expected outcomes
        // ─────────────────────────────────────────────────────────────────────
        Assert.isNotNull(result, 'Result should not be null');
        // TODO: Add specific assertions for expected values
        // Assert.areEqual(expectedValue, result, 'Result should match expected value');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NEGATIVE TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests {{methodUnderTest}} throws exception with null input
     */
    @IsTest
    static void test{{MethodUnderTest}}_NullInput_ThrowsException() {
        // ─────────────────────────────────────────────────────────────────────
        // GIVEN - Null input
        // ─────────────────────────────────────────────────────────────────────
        {{ObjectName}} nullRecord = null;

        // ─────────────────────────────────────────────────────────────────────
        // WHEN/THEN - Verify exception is thrown
        // ─────────────────────────────────────────────────────────────────────
        try {
            Test.startTest();
            {{ClassName}}.{{methodUnderTest}}(nullRecord);
            Test.stopTest();
            Assert.fail('Expected exception was not thrown');
        } catch (IllegalArgumentException e) {
            Assert.isTrue(
                e.getMessage().containsIgnoreCase('null') ||
                e.getMessage().containsIgnoreCase('required'),
                'Error message should indicate null/required issue: ' + e.getMessage()
            );
        }
    }

    /**
     * Tests {{methodUnderTest}} handles invalid data gracefully
     */
    @IsTest
    static void test{{MethodUnderTest}}_InvalidData_ReturnsError() {
        // ─────────────────────────────────────────────────────────────────────
        // GIVEN - Invalid input data
        // ─────────────────────────────────────────────────────────────────────
        {{ObjectName}} invalidRecord = new {{ObjectName}}(
            // TODO: Set invalid field values that should fail validation
        );

        // ─────────────────────────────────────────────────────────────────────
        // WHEN - Execute with invalid data
        // ─────────────────────────────────────────────────────────────────────
        Test.startTest();
        // TODO: Call method and capture result/exception
        Test.stopTest();

        // ─────────────────────────────────────────────────────────────────────
        // THEN - Verify appropriate error handling
        // ─────────────────────────────────────────────────────────────────────
        // TODO: Assert error message or state
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // BULK TESTS (251+ records)
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests {{methodUnderTest}} handles bulk operations (251 records)
     *              251 records crosses the 200-record trigger batch boundary
     */
    @IsTest
    static void test{{MethodUnderTest}}_BulkOperation_Success() {
        // ─────────────────────────────────────────────────────────────────────
        // GIVEN - 251 records (crosses 200-record batch boundary)
        // ─────────────────────────────────────────────────────────────────────
        List<{{ObjectName}}> bulkRecords = TestDataFactory.create{{ObjectName}}s(251);

        // ─────────────────────────────────────────────────────────────────────
        // WHEN - Process bulk records
        // ─────────────────────────────────────────────────────────────────────
        Test.startTest();
        insert bulkRecords;  // Triggers fire in batches of 200, then 51
        Test.stopTest();

        // ─────────────────────────────────────────────────────────────────────
        // THEN - Verify all records processed without governor limit issues
        // ─────────────────────────────────────────────────────────────────────
        Integer recordCount = [SELECT COUNT() FROM {{ObjectName}}];
        Assert.isTrue(recordCount >= 251, 'All 251 records should be processed');

        // Verify governor limits not approached
        Assert.isTrue(Limits.getQueries() < 90,
            'SOQL queries should stay well under limit: ' + Limits.getQueries() + '/100');
        Assert.isTrue(Limits.getDmlStatements() < 140,
            'DML statements should stay under limit: ' + Limits.getDmlStatements() + '/150');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // EDGE CASE TESTS
    // ═══════════════════════════════════════════════────────────────────────────

    /**
     * Tests {{methodUnderTest}} with empty list input
     */
    @IsTest
    static void test{{MethodUnderTest}}_EmptyList_NoError() {
        // ─────────────────────────────────────────────────────────────────────
        // GIVEN - Empty list
        // ─────────────────────────────────────────────────────────────────────
        List<{{ObjectName}}> emptyList = new List<{{ObjectName}}>();

        // ─────────────────────────────────────────────────────────────────────
        // WHEN - Process empty list
        // ─────────────────────────────────────────────────────────────────────
        Test.startTest();
        // TODO: Call method with empty list
        Test.stopTest();

        // ─────────────────────────────────────────────────────────────────────
        // THEN - Should handle gracefully (no exception)
        // ─────────────────────────────────────────────────────────────────────
        // TODO: Assert appropriate handling
    }
}
