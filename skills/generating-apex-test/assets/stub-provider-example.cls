/**
 * StubProvider Examples
 *
 * The Stub API enables dynamic mocking of interfaces and virtual classes.
 * Use when you need conditional logic or method tracking in your mocks.
 *
 * @see https://developer.salesforce.com/docs/atlas.en-us.apexref.meta/apexref/apex_interface_System_StubProvider.htm
 * @see https://blog.beyondthecloud.dev/blog/salesforce-mock-in-apex-tests
 */

// ═══════════════════════════════════════════════════════════════════════════
// EXAMPLE 1: Simple StubProvider for Interface
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Interface to be stubbed
 */
public interface IAccountService {
    Account getAccount(Id accountId);
    List<Account> getAccounts(Set<Id> accountIds);
    Integer getAccountCount();
    void updateAccount(Account acc);
}

/**
 * Basic stub implementation with configurable responses
 */
@IsTest
public class AccountServiceStub implements System.StubProvider {

    // Track method calls for verification
    public List<String> calledMethods = new List<String>();
    public Map<String, List<Object>> methodParams = new Map<String, List<Object>>();

    // Configurable responses
    private Map<String, Object> responses = new Map<String, Object>();

    /**
     * Configure what a method should return
     */
    public AccountServiceStub whenCalled(String methodName, Object response) {
        responses.put(methodName, response);
        return this;
    }

    /**
     * Required StubProvider method
     */
    public Object handleMethodCall(
        Object stubbedObject,
        String stubbedMethodName,
        Type returnType,
        List<Type> paramTypes,
        List<String> paramNames,
        List<Object> paramValues
    ) {
        // Track this call
        calledMethods.add(stubbedMethodName);
        methodParams.put(stubbedMethodName, paramValues);

        // Return configured response if available
        if (responses.containsKey(stubbedMethodName)) {
            return responses.get(stubbedMethodName);
        }

        // Default responses based on return type
        if (returnType == Account.class) {
            return new Account(Id = generateFakeId(), Name = 'Default Stub Account');
        }
        if (returnType == List<Account>.class) {
            return new List<Account>{
                new Account(Id = generateFakeId(), Name = 'Stub Account 1')
            };
        }
        if (returnType == Integer.class) {
            return 0;
        }

        return null;
    }

    /**
     * Verify a method was called
     */
    public Boolean wasCalled(String methodName) {
        return calledMethods.contains(methodName);
    }

    /**
     * Get call count for a method
     */
    public Integer getCallCount(String methodName) {
        Integer count = 0;
        for (String called : calledMethods) {
            if (called == methodName) {
                count++;
            }
        }
        return count;
    }

    // Fake ID generator
    private static Integer idCounter = 1;
    private static Id generateFakeId() {
        String idBody = String.valueOf(idCounter++).leftPad(12, '0');
        return Id.valueOf('001' + idBody);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXAMPLE 2: Using the Stub in Tests
// ═══════════════════════════════════════════════════════════════════════════

@IsTest
private class AccountServiceStubTest {

    @IsTest
    static void testWithConfiguredResponse() {
        // Arrange - Configure stub responses
        AccountServiceStub stub = new AccountServiceStub()
            .whenCalled('getAccountCount', 42)
            .whenCalled('getAccount', new Account(Name = 'Configured Account'));

        // Create stubbed instance
        IAccountService service = (IAccountService) Test.createStub(
            IAccountService.class,
            stub
        );

        // Act
        Test.startTest();
        Integer count = service.getAccountCount();
        Account acc = service.getAccount(null);
        Test.stopTest();

        // Assert - Verify responses
        Assert.areEqual(42, count, 'Should return configured count');
        Assert.areEqual('Configured Account', acc.Name, 'Should return configured account');

        // Assert - Verify calls were tracked
        Assert.isTrue(stub.wasCalled('getAccountCount'), 'getAccountCount was called');
        Assert.isTrue(stub.wasCalled('getAccount'), 'getAccount was called');
        Assert.areEqual(1, stub.getCallCount('getAccountCount'), 'Called once');
    }

    @IsTest
    static void testDefaultResponses() {
        // Arrange - No configured responses
        AccountServiceStub stub = new AccountServiceStub();
        IAccountService service = (IAccountService) Test.createStub(
            IAccountService.class,
            stub
        );

        // Act
        Test.startTest();
        Account acc = service.getAccount(null);
        Test.stopTest();

        // Assert - Verify default response
        Assert.isNotNull(acc, 'Should return default account');
        Assert.areEqual('Default Stub Account', acc.Name, 'Should have default name');
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXAMPLE 3: Conditional StubProvider
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Stub with conditional logic based on parameters
 */
@IsTest
public class ConditionalStub implements System.StubProvider {

    public Object handleMethodCall(
        Object stubbedObject,
        String stubbedMethodName,
        Type returnType,
        List<Type> paramTypes,
        List<String> paramNames,
        List<Object> paramValues
    ) {
        // Conditional response based on method and params
        if (stubbedMethodName == 'getAccount') {
            Id requestedId = (Id) paramValues[0];

            // Return different accounts based on ID pattern
            String idStr = String.valueOf(requestedId);
            if (idStr.startsWith('001')) {
                return new Account(Id = requestedId, Name = 'Standard Account');
            } else if (idStr.startsWith('0018')) {
                return new Account(Id = requestedId, Name = 'Person Account');
            }
        }

        if (stubbedMethodName == 'getAccountCount') {
            // Simulate different counts for different scenarios
            return 100;
        }

        return null;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXAMPLE 4: Exception-Throwing Stub
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Stub that throws exceptions for error testing
 */
@IsTest
public class ErrorStub implements System.StubProvider {

    private String methodToFail;
    private String errorMessage;

    public ErrorStub failOn(String methodName, String message) {
        this.methodToFail = methodName;
        this.errorMessage = message;
        return this;
    }

    public Object handleMethodCall(
        Object stubbedObject,
        String stubbedMethodName,
        Type returnType,
        List<Type> paramTypes,
        List<String> paramNames,
        List<Object> paramValues
    ) {
        if (stubbedMethodName == methodToFail) {
            throw new AuraHandledException(errorMessage);
        }
        return null;
    }
}

@IsTest
private class ErrorStubTest {

    @IsTest
    static void testErrorHandling() {
        // Arrange
        ErrorStub stub = new ErrorStub().failOn('getAccount', 'Account not found');
        IAccountService service = (IAccountService) Test.createStub(
            IAccountService.class,
            stub
        );

        // Act/Assert
        try {
            service.getAccount(null);
            Assert.fail('Expected AuraHandledException');
        } catch (AuraHandledException e) {
            Assert.areEqual('Account not found', e.getMessage());
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXAMPLE 5: Universal Mock (Flexible Stub)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Highly flexible stub that can mock any interface
 *
 * Inspired by: Suraj Pillai's UniversalMock pattern
 */
@IsTest
public class UniversalMock implements System.StubProvider {

    // Store method -> return value mappings
    private Map<String, Object> returnValues = new Map<String, Object>();

    // Store method -> exception mappings
    private Map<String, Exception> exceptions = new Map<String, Exception>();

    // Track all calls
    private List<MethodCall> calls = new List<MethodCall>();

    public class MethodCall {
        public String methodName;
        public List<Object> arguments;
        public Datetime calledAt;

        public MethodCall(String methodName, List<Object> arguments) {
            this.methodName = methodName;
            this.arguments = arguments;
            this.calledAt = Datetime.now();
        }
    }

    /**
     * Configure return value for a method
     */
    public UniversalMock setReturnValue(String methodName, Object value) {
        returnValues.put(methodName, value);
        return this;
    }

    /**
     * Configure exception for a method
     */
    public UniversalMock throwException(String methodName, Exception e) {
        exceptions.put(methodName, e);
        return this;
    }

    public Object handleMethodCall(
        Object stubbedObject,
        String stubbedMethodName,
        Type returnType,
        List<Type> paramTypes,
        List<String> paramNames,
        List<Object> paramValues
    ) {
        // Track the call
        calls.add(new MethodCall(stubbedMethodName, paramValues));

        // Throw configured exception
        if (exceptions.containsKey(stubbedMethodName)) {
            throw exceptions.get(stubbedMethodName);
        }

        // Return configured value
        if (returnValues.containsKey(stubbedMethodName)) {
            return returnValues.get(stubbedMethodName);
        }

        // Return type-appropriate defaults
        if (returnType == Boolean.class) return false;
        if (returnType == Integer.class) return 0;
        if (returnType == String.class) return '';
        if (returnType == List<SObject>.class) return new List<SObject>();

        return null;
    }

    /**
     * Get all calls to a specific method
     */
    public List<MethodCall> getCalls(String methodName) {
        List<MethodCall> result = new List<MethodCall>();
        for (MethodCall call : calls) {
            if (call.methodName == methodName) {
                result.add(call);
            }
        }
        return result;
    }

    /**
     * Verify method was called with specific arguments
     */
    public Boolean wasCalledWith(String methodName, List<Object> expectedArgs) {
        for (MethodCall call : getCalls(methodName)) {
            if (call.arguments.equals(expectedArgs)) {
                return true;
            }
        }
        return false;
    }
}
