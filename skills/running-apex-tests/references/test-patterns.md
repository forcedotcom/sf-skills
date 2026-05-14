<!-- Parent: running-apex-tests/SKILL.md -->

# Test Patterns & Templates

## Pattern 1: Basic Test Class

Use template: `assets/basic-test.cls`

```apex
@IsTest
private class AccountServiceTest {

    @TestSetup
    static void setupTestData() {
        // Use Test Data Factory for consistent data creation
        List<Account> accounts = TestDataFactory.createAccounts(5);
        insert accounts;
    }

    @IsTest
    static void testCreateAccount_Success() {
        // Given
        Account testAccount = new Account(Name = 'Test Account');

        // When
        Test.startTest();
        Id accountId = AccountService.createAccount(testAccount);
        Test.stopTest();

        // Then
        Assert.isNotNull(accountId, 'Account ID should not be null');
        Account inserted = [SELECT Name FROM Account WHERE Id = :accountId];
        Assert.areEqual('Test Account', inserted.Name, 'Account name should match');
    }

    @IsTest
    static void testCreateAccount_NullInput_ThrowsException() {
        // Given
        Account nullAccount = null;

        // When/Then
        try {
            Test.startTest();
            AccountService.createAccount(nullAccount);
            Test.stopTest();
            Assert.fail('Expected IllegalArgumentException was not thrown');
        } catch (IllegalArgumentException e) {
            Assert.isTrue(e.getMessage().contains('cannot be null'),
                'Error message should mention null: ' + e.getMessage());
        }
    }
}
```

## Pattern 2: Bulk Test (251+ Records)

Use template: `assets/bulk-test.cls`

```apex
@IsTest
static void testBulkInsert_251Records() {
    // Given - 251 records crosses the 200-record batch boundary
    List<Account> accounts = TestDataFactory.createAccounts(251);

    // When
    Test.startTest();
    insert accounts;  // Triggers fire in batches of 200, then 51
    Test.stopTest();

    // Then
    Integer count = [SELECT COUNT() FROM Account];
    Assert.areEqual(251, count, 'All 251 accounts should be inserted');

    // Verify no governor limits hit
    Assert.isTrue(Limits.getQueries() < 100,
        'Should not approach SOQL limit: ' + Limits.getQueries());
}
```

## Pattern 3: Mock Callout Test

Use template: `assets/mock-callout-test.cls`

```apex
@IsTest
private class ExternalAPIServiceTest {

    // Mock class for HTTP callouts
    private class MockHttpResponse implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setBody('{"success": true, "data": {"id": "12345"}}');
            return res;
        }
    }

    @IsTest
    static void testCallExternalAPI_Success() {
        // Given
        Test.setMock(HttpCalloutMock.class, new MockHttpResponse());

        // When
        Test.startTest();
        String result = ExternalAPIService.callAPI('test-endpoint');
        Test.stopTest();

        // Then
        Assert.isTrue(result.contains('success'), 'Response should indicate success');
    }
}
```

## Pattern 4: Test Data Factory

Use template: `assets/test-data-factory.cls`

```apex
@IsTest
public class TestDataFactory {

    public static List<Account> createAccounts(Integer count) {
        List<Account> accounts = new List<Account>();
        for (Integer i = 0; i < count; i++) {
            accounts.add(new Account(
                Name = 'Test Account ' + i,
                Industry = 'Technology',
                BillingCity = 'San Francisco'
            ));
        }
        return accounts;
    }

    public static List<Contact> createContacts(Integer count, Id accountId) {
        List<Contact> contacts = new List<Contact>();
        for (Integer i = 0; i < count; i++) {
            contacts.add(new Contact(
                FirstName = 'Test',
                LastName = 'Contact ' + i,
                AccountId = accountId,
                Email = 'test' + i + '@example.com'
            ));
        }
        return contacts;
    }

    // Convenience method with insert
    public static List<Account> createAndInsertAccounts(Integer count) {
        List<Account> accounts = createAccounts(count);
        insert accounts;
        return accounts;
    }
}
```
