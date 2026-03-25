/**
 * DML Mocking Framework
 *
 * Enables true unit testing by replacing database operations with in-memory tracking.
 * Tests using this pattern run ~35x faster than tests with actual DML.
 *
 * @see https://www.jamessimone.net/blog/joys-of-apex/mocking-dml/
 */

// ═══════════════════════════════════════════════════════════════════════════
// INTERFACE: IDML
// Define the contract for DML operations
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Interface for DML operations - enables dependency injection
 */
public interface IDML {
    void doInsert(SObject record);
    void doInsert(List<SObject> records);
    void doUpdate(SObject record);
    void doUpdate(List<SObject> records);
    void doUpsert(SObject record);
    void doUpsert(List<SObject> records);
    void doDelete(SObject record);
    void doDelete(List<SObject> records);
}

// ═══════════════════════════════════════════════════════════════════════════
// PRODUCTION: DML
// Performs actual database operations
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Production implementation performing real database operations
 */
public class DML implements IDML {

    public void doInsert(SObject record) {
        insert record;
    }

    public void doInsert(List<SObject> records) {
        if (records != null && !records.isEmpty()) {
            insert records;
        }
    }

    public void doUpdate(SObject record) {
        update record;
    }

    public void doUpdate(List<SObject> records) {
        if (records != null && !records.isEmpty()) {
            update records;
        }
    }

    public void doUpsert(SObject record) {
        upsert record;
    }

    public void doUpsert(List<SObject> records) {
        if (records != null && !records.isEmpty()) {
            upsert records;
        }
    }

    public void doDelete(SObject record) {
        delete record;
    }

    public void doDelete(List<SObject> records) {
        if (records != null && !records.isEmpty()) {
            delete records;
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// TEST MOCK: DMLMock
// Tracks operations without hitting the database
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Mock DML implementation for fast unit tests
 *
 * Usage:
 *   DMLMock.reset();
 *   MyService service = new MyService(new DMLMock());
 *   service.doSomething();
 *   Assert.areEqual(1, DMLMock.InsertedRecords.size());
 */
@IsTest
public class DMLMock implements IDML {

    // ═══════════════════════════════════════════════════════════════════
    // TRACKED OPERATIONS
    // ═══════════════════════════════════════════════════════════════════

    public static List<SObject> InsertedRecords = new List<SObject>();
    public static List<SObject> UpdatedRecords = new List<SObject>();
    public static List<SObject> UpsertedRecords = new List<SObject>();
    public static List<SObject> DeletedRecords = new List<SObject>();

    // Counter for generating unique fake IDs
    private static Integer idCounter = 1;

    // ═══════════════════════════════════════════════════════════════════
    // DML OPERATIONS
    // ═══════════════════════════════════════════════════════════════════

    public void doInsert(SObject record) {
        doInsert(new List<SObject>{ record });
    }

    public void doInsert(List<SObject> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        for (SObject record : records) {
            // Generate fake ID to simulate database insert
            if (record.Id == null) {
                record.Id = generateFakeId(record.getSObjectType());
            }
            InsertedRecords.add(record);
        }
    }

    public void doUpdate(SObject record) {
        doUpdate(new List<SObject>{ record });
    }

    public void doUpdate(List<SObject> records) {
        if (records != null && !records.isEmpty()) {
            UpdatedRecords.addAll(records);
        }
    }

    public void doUpsert(SObject record) {
        doUpsert(new List<SObject>{ record });
    }

    public void doUpsert(List<SObject> records) {
        if (records != null && !records.isEmpty()) {
            for (SObject record : records) {
                if (record.Id == null) {
                    record.Id = generateFakeId(record.getSObjectType());
                }
            }
            UpsertedRecords.addAll(records);
        }
    }

    public void doDelete(SObject record) {
        doDelete(new List<SObject>{ record });
    }

    public void doDelete(List<SObject> records) {
        if (records != null && !records.isEmpty()) {
            DeletedRecords.addAll(records);
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // UTILITY METHODS
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Reset all tracked operations - call at start of each test
     */
    public static void reset() {
        InsertedRecords.clear();
        UpdatedRecords.clear();
        UpsertedRecords.clear();
        DeletedRecords.clear();
        idCounter = 1;
    }

    /**
     * Generate a valid Salesforce ID for testing
     * Uses the object's key prefix for realistic IDs
     */
    private static Id generateFakeId(Schema.SObjectType sObjectType) {
        String keyPrefix = sObjectType.getDescribe().getKeyPrefix();
        if (keyPrefix == null) {
            keyPrefix = '000';  // Fallback for objects without prefix
        }
        String idBody = String.valueOf(idCounter++).leftPad(12, '0');
        return Id.valueOf(keyPrefix + idBody);
    }

    // ═══════════════════════════════════════════════════════════════════
    // HELPER METHODS FOR ASSERTIONS
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Get inserted records of a specific SObject type
     */
    public static List<SObject> getInsertedOfType(Schema.SObjectType sObjectType) {
        List<SObject> result = new List<SObject>();
        for (SObject record : InsertedRecords) {
            if (record.getSObjectType() == sObjectType) {
                result.add(record);
            }
        }
        return result;
    }

    /**
     * Get updated records of a specific SObject type
     */
    public static List<SObject> getUpdatedOfType(Schema.SObjectType sObjectType) {
        List<SObject> result = new List<SObject>();
        for (SObject record : UpdatedRecords) {
            if (record.getSObjectType() == sObjectType) {
                result.add(record);
            }
        }
        return result;
    }

    /**
     * Get deleted records of a specific SObject type
     */
    public static List<SObject> getDeletedOfType(Schema.SObjectType sObjectType) {
        List<SObject> result = new List<SObject>();
        for (SObject record : DeletedRecords) {
            if (record.getSObjectType() == sObjectType) {
                result.add(record);
            }
        }
        return result;
    }

    /**
     * Check if any records of a specific type were inserted
     */
    public static Boolean wasInserted(Schema.SObjectType sObjectType) {
        return !getInsertedOfType(sObjectType).isEmpty();
    }

    /**
     * Check if any records of a specific type were updated
     */
    public static Boolean wasUpdated(Schema.SObjectType sObjectType) {
        return !getUpdatedOfType(sObjectType).isEmpty();
    }

    /**
     * Check if any records of a specific type were deleted
     */
    public static Boolean wasDeleted(Schema.SObjectType sObjectType) {
        return !getDeletedOfType(sObjectType).isEmpty();
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXAMPLE: Service Using Injected DML
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Example service class demonstrating DML injection
 */
public class AccountService {

    private IDML dml;

    // Production constructor - uses real DML
    public AccountService() {
        this(new DML());
    }

    // Test constructor - accepts mock DML
    @TestVisible
    private AccountService(IDML dml) {
        this.dml = dml;
    }

    public Id createAccount(Account acc) {
        if (acc == null) {
            throw new IllegalArgumentException('Account cannot be null');
        }
        dml.doInsert(acc);
        return acc.Id;
    }

    public void updateAccounts(List<Account> accounts) {
        dml.doUpdate(accounts);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXAMPLE: Test Class Using DML Mock
// ═══════════════════════════════════════════════════════════════════════════

@IsTest
private class AccountServiceTest {

    @IsTest
    static void testCreateAccount_Success() {
        // Arrange
        DMLMock.reset();
        AccountService service = new AccountService(new DMLMock());
        Account testAcc = new Account(Name = 'Test Corp', Industry = 'Technology');

        // Act
        Test.startTest();
        Id accountId = service.createAccount(testAcc);
        Test.stopTest();

        // Assert
        Assert.isNotNull(accountId, 'Should have generated ID');
        Assert.areEqual(1, DMLMock.InsertedRecords.size(), 'Should have 1 insert');
        Assert.isTrue(DMLMock.wasInserted(Account.SObjectType), 'Account was inserted');

        Account inserted = (Account) DMLMock.InsertedRecords[0];
        Assert.areEqual('Test Corp', inserted.Name, 'Name should match');
        Assert.areEqual('Technology', inserted.Industry, 'Industry should match');
    }

    @IsTest
    static void testCreateAccount_NullInput_ThrowsException() {
        // Arrange
        DMLMock.reset();
        AccountService service = new AccountService(new DMLMock());

        // Act/Assert
        try {
            service.createAccount(null);
            Assert.fail('Expected IllegalArgumentException');
        } catch (IllegalArgumentException e) {
            Assert.isTrue(e.getMessage().contains('null'), 'Error should mention null');
        }

        // Verify no DML occurred
        Assert.areEqual(0, DMLMock.InsertedRecords.size(), 'No records should be inserted');
    }
}
