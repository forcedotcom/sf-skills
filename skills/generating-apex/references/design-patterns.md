# Apex Design Patterns

## Factory Pattern

### Purpose
Centralize object creation, enable dependency injection, simplify substitution/mocking.

### Implementation

```apex
public virtual class Factory {
    private static Factory instance;

    public static Factory getInstance() {
        if (instance == null) {
            instance = new Factory();
        }
        return instance;
    }

    @TestVisible
    private static void setInstance(Factory mockFactory) {
        instance = mockFactory;
    }

    // Service getters - virtual for mocking
    public virtual AccountService getAccountService() {
        return new AccountService();
    }

    public virtual ContactService getContactService() {
        return new ContactService();
    }

    public virtual PaymentGateway getPaymentGateway() {
        return new StripePaymentGateway();
    }
}
```

### Usage

```apex
public class OrderProcessor {
    private AccountService accountService;
    private PaymentGateway gateway;

    public OrderProcessor() {
        this(Factory.getInstance());
    }

    @TestVisible
    private OrderProcessor(Factory factory) {
        this.accountService = factory.getAccountService();
        this.gateway = factory.getPaymentGateway();
    }

    public void process(Order__c order) {
        Account acc = accountService.getAccount(order.Account__c);
        gateway.charge(order.Total__c);
    }
}
```


---

## Repository Pattern

### Purpose
Abstract data access, provide strongly-typed queries, enable DML mocking.

### Implementation

```apex
public virtual class AccountRepository {

    public virtual List<Account> getByIds(Set<Id> accountIds) {
        return [
            SELECT Id, Name, Industry, AnnualRevenue
            FROM Account
            WHERE Id IN :accountIds
            WITH USER_MODE
        ];
    }

    public virtual List<Account> getByIndustry(String industry) {
        return [
            SELECT Id, Name, AnnualRevenue
            FROM Account
            WHERE Industry = :industry
            WITH USER_MODE
        ];
    }

    public virtual Account getById(Id accountId) {
        List<Account> accounts = getByIds(new Set<Id>{accountId});
        return accounts.isEmpty() ? null : accounts[0];
    }

    public virtual void save(List<Account> accounts) {
        upsert accounts;
    }

    public virtual void remove(List<Account> accounts) {
        delete accounts;
    }
}
```

### Usage

```apex
public class AccountService {
    private AccountRepository repo;

    public AccountService() {
        this.repo = new AccountRepository();
    }

    @TestVisible
    private AccountService(AccountRepository repo) {
        this.repo = repo;
    }

    public List<Account> getTechnologyAccounts() {
        return repo.getByIndustry('Technology');
    }

    public void updateAccounts(List<Account> accounts) {
        repo.save(accounts);
    }
}
```

### Testing with Mock Repository

```apex
@isTest
private class AccountServiceTest {


---

## Selector Pattern

### Purpose
Centralize SOQL queries per object, enforce security, enable reuse.

### Implementation

```apex
public inherited sharing class AccountSelector {

    public List<Account> selectById(Set<Id> ids) {
        return [
            SELECT Id, Name, Industry, AnnualRevenue, BillingCity
            FROM Account
            WHERE Id IN :ids
            WITH USER_MODE
        ];
    }

    public List<Account> selectByIdWithContacts(Set<Id> ids) {
        return [
            SELECT Id, Name, Industry,
                (SELECT Id, FirstName, LastName, Email FROM Contacts)
            FROM Account
            WHERE Id IN :ids
            WITH USER_MODE
        ];
    }

    public List<Account> selectByName(String name) {
        return [
            SELECT Id, Name, Industry
            FROM Account
            WHERE Name LIKE :('%' + name + '%')
            WITH USER_MODE
            LIMIT 100
        ];
    }

    public List<Account> selectActiveByIndustry(String industry) {
        return [
            SELECT Id, Name, AnnualRevenue
            FROM Account
            WHERE Industry = :industry
            AND Status__c = 'Active'
            WITH USER_MODE
        ];
    }
}
```

### Usage

```apex
public class AccountService {
    private AccountSelector selector = new AccountSelector();

    public Map<Id, Account> getAccountsMap(Set<Id> ids) {
        return new Map<Id, Account>(selector.selectById(ids));
    }
}
```

---

## Builder Pattern

### Purpose
Construct complex objects step-by-step, improve readability.

### Implementation

```apex
public class AccountBuilder {
    private Account record;

    public AccountBuilder() {
        this.record = new Account();
    }

    public AccountBuilder withName(String name) {
        this.record.Name = name;
        return this;
    }

    public AccountBuilder withIndustry(String industry) {
        this.record.Industry = industry;
        return this;
    }

    public AccountBuilder withAnnualRevenue(Decimal revenue) {
        this.record.AnnualRevenue = revenue;
        return this;
    }

    public AccountBuilder withBillingAddress(String city, String state, String country) {
        this.record.BillingCity = city;
        this.record.BillingState = state;
        this.record.BillingCountry = country;
        return this;
    }

    public AccountBuilder withParent(Id parentId) {
        this.record.ParentId = parentId;
        return this;
    }

    public Account build() {
        return this.record;
    }

    public Account buildAndInsert() {
        insert this.record;
        return this.record;
    }
}
```

### Usage

```apex
// Fluent interface for building objects
Account acc = new AccountBuilder()
    .withName('Acme Corporation')
    .withIndustry('Technology')
    .withAnnualRevenue(1000000)
    .withBillingAddress('San Francisco', 'CA', 'USA')
    .buildAndInsert();

// In tests
Account testAccount = new AccountBuilder()
    .withName('Test Account')
    .build();  // Don't insert for unit tests
```

---

## Singleton Pattern

### Purpose
Ensure single instance, cache expensive operations.

### Implementation

```apex
public class ConfigurationService {
    private static ConfigurationService instance;
    private Map<String, String> settings;

    private ConfigurationService() {
        // Load settings once
        this.settings = new Map<String, String>();
        for (Configuration__mdt config : [SELECT DeveloperName, Value__c FROM Configuration__mdt]) {
            settings.put(config.DeveloperName, config.Value__c);
        }
    }

    public static ConfigurationService getInstance() {
        if (instance == null) {
            instance = new ConfigurationService();
        }
        return instance;
    }

    public String getSetting(String key) {
        return settings.get(key);
    }

    public String getSetting(String key, String defaultValue) {
        return settings.containsKey(key) ? settings.get(key) : defaultValue;
    }

    // For testing
    @TestVisible
    private static void reset() {
        instance = null;
    }
}
```

### Usage

```apex
String apiUrl = ConfigurationService.getInstance().getSetting('API_URL');
String timeout = ConfigurationService.getInstance().getSetting('TIMEOUT', '30000');
```

---

## Strategy Pattern

### Purpose
Define family of algorithms, make them interchangeable.

### Implementation

```apex
public interface DiscountStrategy {
    Decimal calculate(Decimal amount);
    String getDescription();
}

public class PercentageDiscount implements DiscountStrategy {
    private Decimal percentage;

    public PercentageDiscount(Decimal percentage) {
        this.percentage = percentage;
    }

    public Decimal calculate(Decimal amount) {
        return amount * (percentage / 100);
    }

    public String getDescription() {
        return percentage + '% off';
    }
}

public class FixedAmountDiscount implements DiscountStrategy {
    private Decimal fixedAmount;

    public FixedAmountDiscount(Decimal amount) {
        this.fixedAmount = amount;
    }

    public Decimal calculate(Decimal amount) {
        return Math.min(fixedAmount, amount);
    }

    public String getDescription() {
        return '$' + fixedAmount + ' off';
    }
}

public class TieredDiscount implements DiscountStrategy {
    public Decimal calculate(Decimal amount) {
        if (amount > 1000) return amount * 0.15;
        if (amount > 500) return amount * 0.10;
        if (amount > 100) return amount * 0.05;
        return 0;
    }

    public String getDescription() {
        return 'Tiered discount based on amount';
    }
}
```

### Usage

```apex
public class PricingService {
    private Map<String, DiscountStrategy> strategies;

    public PricingService() {
        strategies = new Map<String, DiscountStrategy>{
            'PERCENTAGE_10' => new PercentageDiscount(10),
            'FIXED_50' => new FixedAmountDiscount(50),
            'TIERED' => new TieredDiscount()
        };
    }

    public Decimal applyDiscount(String discountType, Decimal amount) {
        DiscountStrategy strategy = strategies.get(discountType);
        if (strategy == null) {
            return 0;
        }
        return strategy.calculate(amount);
    }
}
```

---

## Unit of Work Pattern

### Purpose
Manage DML as single transaction, track changes, enable rollback.

### Basic Implementation

```apex
public class UnitOfWork {
    private List<SObject> newRecords = new List<SObject>();
    private List<SObject> dirtyRecords = new List<SObject>();
    private List<SObject> deletedRecords = new List<SObject>();

    public void registerNew(SObject record) {
        newRecords.add(record);
    }

    public void registerNew(List<SObject> records) {
        newRecords.addAll(records);
    }

    public void registerDirty(SObject record) {
        dirtyRecords.add(record);
    }

    public void registerDeleted(SObject record) {
        deletedRecords.add(record);
    }

    public void commitWork() {
        Savepoint sp = Database.setSavepoint();
        try {
            insert newRecords;
            update dirtyRecords;
            delete deletedRecords;
        } catch (Exception e) {
            Database.rollback(sp);
            throw e;
        }
    }
}
```

### Usage

```apex
public class OrderService {
    public void processOrder(Order__c order, List<OrderItem__c> items) {
        UnitOfWork uow = new UnitOfWork();

        // Register all changes
        uow.registerNew(order);
        uow.registerNew(items);

        Account acc = [SELECT Id, Order_Count__c FROM Account WHERE Id = :order.Account__c];
        acc.Order_Count__c = (acc.Order_Count__c ?? 0) + 1;
        uow.registerDirty(acc);

        // Single commit - all or nothing
        uow.commitWork();
    }
}
```

---

## Decorator Pattern

### Purpose
Add functionality dynamically without modifying original class. Stack behaviors flexibly.

### Implementation

```apex
// Base interface
public interface NotificationService {
    void send(String message, Id recipientId);
}

// Core implementation
public class EmailNotification implements NotificationService {
    public void send(String message, Id recipientId) {
        Messaging.SingleEmailMessage email = new Messaging.SingleEmailMessage();
        email.setTargetObjectId(recipientId);
        email.setPlainTextBody(message);
        Messaging.sendEmail(new List<Messaging.SingleEmailMessage>{ email });
    }
}

// Decorator base - wraps another NotificationService
public virtual class NotificationDecorator implements NotificationService {
    protected NotificationService wrapped;

    public NotificationDecorator(NotificationService service) {
        this.wrapped = service;
    }

    public virtual void send(String message, Id recipientId) {
        wrapped.send(message, recipientId);
    }
}

// Concrete decorator: Add logging
public class LoggingNotificationDecorator extends NotificationDecorator {
    public LoggingNotificationDecorator(NotificationService service) {
        super(service);
    }

    public override void send(String message, Id recipientId) {
        System.debug('Sending notification to: ' + recipientId);
        super.send(message, recipientId);
        System.debug('Notification sent successfully');
    }
}

// Concrete decorator: Add retry logic
public class RetryNotificationDecorator extends NotificationDecorator {
    private Integer maxRetries;

    public RetryNotificationDecorator(NotificationService service, Integer maxRetries) {
        super(service);
        this.maxRetries = maxRetries;
    }

    public override void send(String message, Id recipientId) {
        Integer attempts = 0;
        while (attempts < maxRetries) {
            try {
                super.send(message, recipientId);
                return;
            } catch (Exception e) {
                attempts++;
                if (attempts >= maxRetries) throw e;
            }
        }
    }
}
```

### Usage

```apex
// Stack decorators as needed
NotificationService service = new EmailNotification();
service = new LoggingNotificationDecorator(service);
service = new RetryNotificationDecorator(service, 3);

// Now sends with logging + retry + email
service.send('Your order shipped!', userId);
```

### When to Use
- Adding cross-cutting concerns (logging, caching, validation)
- When inheritance leads to class explosion
- Stacking behaviors that can be combined independently

---

## Observer Pattern

### Purpose
Define one-to-many dependency where observers are notified of state changes automatically.

### Implementation

```apex
// Observer interface
public interface AccountObserver {
    void onAccountUpdated(Account oldAccount, Account newAccount);
}

// Subject that notifies observers
public class AccountSubject {
    private static List<AccountObserver> observers = new List<AccountObserver>();

    public static void attach(AccountObserver observer) {
        observers.add(observer);
    }

    public static void detach(AccountObserver observer) {
        Integer index = observers.indexOf(observer);
        if (index >= 0) observers.remove(index);
    }

    public static void notifyObservers(Account oldAccount, Account newAccount) {
        for (AccountObserver observer : observers) {
            observer.onAccountUpdated(oldAccount, newAccount);
        }
    }
}

// Concrete observers
public class SalesNotificationObserver implements AccountObserver {
    public void onAccountUpdated(Account oldAcc, Account newAcc) {
        if (newAcc.AnnualRevenue > 1000000 && (oldAcc.AnnualRevenue == null || oldAcc.AnnualRevenue <= 1000000)) {
            // Notify sales team about new enterprise account
            createTask(newAcc.OwnerId, 'New Enterprise Account: ' + newAcc.Name);
        }
    }

    private void createTask(Id ownerId, String subject) {
        insert new Task(OwnerId = ownerId, Subject = subject, Status = 'Open');
    }
}

public class IntegrationSyncObserver implements AccountObserver {
    public void onAccountUpdated(Account oldAcc, Account newAcc) {
        // Queue sync to external system
        System.enqueueJob(new AccountSyncQueueable(newAcc.Id));
    }
}
```

### Usage in Trigger

```apex
// TriggerHandler or Action class
public class AccountTriggerHandler {

    static {
        // Register observers once
        AccountSubject.attach(new SalesNotificationObserver());
        AccountSubject.attach(new IntegrationSyncObserver());
    }

    public void afterUpdate(List<Account> newList, Map<Id, Account> oldMap) {
        for (Account acc : newList) {
            AccountSubject.notifyObservers(oldMap.get(acc.Id), acc);
        }
    }
}
```

### Platform Events Alternative
For decoupled, async observers, use Platform Events:

```apex
// Publish event
EventBus.publish(new Account_Updated__e(Account_Id__c = acc.Id, Field_Changed__c = 'Status'));

// Subscribe via trigger on platform event
trigger AccountUpdatedSubscriber on Account_Updated__e (after insert) {
    // Handle event
}
```

---

## Command Pattern

### Purpose
Encapsulate requests as objects, enabling queuing, logging, undo, and parameterized execution.

### Implementation

```apex
// Command interface
public interface Command {
    void execute();
    void undo();
    String getDescription();
}

// Concrete command: Update Field
public class UpdateFieldCommand implements Command {
    private Id recordId;
    private String fieldName;
    private Object newValue;
    private Object oldValue;
    private SObjectType objectType;

    public UpdateFieldCommand(Id recordId, String fieldName, Object newValue) {
        this.recordId = recordId;
        this.fieldName = fieldName;
        this.newValue = newValue;
        this.objectType = recordId.getSObjectType();
    }

    public void execute() {
        // Store old value for undo
        SObject record = Database.query(
            'SELECT ' + fieldName + ' FROM ' + objectType + ' WHERE Id = :recordId'
        );
        this.oldValue = record.get(fieldName);

        // Apply new value
        record.put(fieldName, newValue);
        update record;
    }

    public void undo() {
        SObject record = objectType.newSObject(recordId);
        record.put(fieldName, oldValue);
        update record;
    }

    public String getDescription() {
        return 'Update ' + objectType + '.' + fieldName + ' to ' + newValue;
    }
}

// Command invoker with history
public class CommandInvoker {
    private List<Command> history = new List<Command>();
    private List<Command> queue = new List<Command>();

    public void addToQueue(Command cmd) {
        queue.add(cmd);
    }

    public void executeQueue() {
        for (Command cmd : queue) {
            cmd.execute();
            history.add(cmd);
            // Log for audit trail
            System.debug('Executed: ' + cmd.getDescription());
        }
        queue.clear();
    }

    public void undoLast() {
        if (!history.isEmpty()) {
            Command lastCommand = history.remove(history.size() - 1);
            lastCommand.undo();
        }
    }
}
```

### Usage

```apex
CommandInvoker invoker = new CommandInvoker();

// Queue multiple field updates
invoker.addToQueue(new UpdateFieldCommand(accountId, 'Status__c', 'Active'));
invoker.addToQueue(new UpdateFieldCommand(accountId, 'Priority__c', 'High'));

// Execute all
invoker.executeQueue();

// Undo last operation
invoker.undoLast();
```

### Use Cases
- Wizard/multi-step processes with undo
- Audit trail with replayable operations
- Batch processing with deferred execution
- Macro recording and playback

---

## Facade Pattern

### Purpose
Provide simplified interface to complex subsystems. Reduce coupling between client and implementation details.

### Implementation

```apex
// Complex subsystems
public class CustomerVerificationService {
    public Boolean verifyIdentity(String customerId) {
        // Complex identity verification logic
        return true;
    }
}

public class CreditCheckService {
    public Integer getCreditScore(String customerId) {
        // Call external credit bureau
        return 720;
    }

    public Decimal getAvailableCredit(String customerId) {
        return 50000.00;
    }
}

public class RiskAssessmentService {
    public String assessRisk(Integer creditScore, Decimal requestedAmount) {
        if (creditScore > 700 && requestedAmount < 25000) return 'LOW';
        if (creditScore > 600) return 'MEDIUM';
        return 'HIGH';
    }
}

public class LoanApplicationService {
    public Id createApplication(Id accountId, Decimal amount) {
        Loan_Application__c app = new Loan_Application__c(
            Account__c = accountId,
            Amount__c = amount,
            Status__c = 'Pending'
        );
        insert app;
        return app.Id;
    }
}

// FACADE: Simplified interface
public class LoanFacade {
    private CustomerVerificationService verificationService;
    private CreditCheckService creditService;
    private RiskAssessmentService riskService;
    private LoanApplicationService applicationService;

    public LoanFacade() {
        this.verificationService = new CustomerVerificationService();
        this.creditService = new CreditCheckService();
        this.riskService = new RiskAssessmentService();
        this.applicationService = new LoanApplicationService();
    }

    // Single method hides all complexity
    public LoanResult applyForLoan(Id accountId, String customerId, Decimal amount) {
        LoanResult result = new LoanResult();

        // Step 1: Verify customer
        if (!verificationService.verifyIdentity(customerId)) {
            result.success = false;
            result.message = 'Identity verification failed';
            return result;
        }

        // Step 2: Check credit
        Integer creditScore = creditService.getCreditScore(customerId);
        Decimal availableCredit = creditService.getAvailableCredit(customerId);

        if (amount > availableCredit) {
            result.success = false;
            result.message = 'Requested amount exceeds available credit';
            return result;
        }

        // Step 3: Assess risk
        String riskLevel = riskService.assessRisk(creditScore, amount);

        // Step 4: Create application
        result.applicationId = applicationService.createApplication(accountId, amount);
        result.success = true;
        result.riskLevel = riskLevel;
        result.message = 'Loan application submitted successfully';

        return result;
    }

    public class LoanResult {
        public Boolean success;
        public Id applicationId;
        public String riskLevel;
        public String message;
    }
}
```

### Usage

```apex
// Client code is simple - no knowledge of subsystems
LoanFacade facade = new LoanFacade();
LoanFacade.LoanResult result = facade.applyForLoan(accountId, 'CUST-123', 15000.00);

if (result.success) {
    System.debug('Loan approved with risk level: ' + result.riskLevel);
} else {
    System.debug('Loan denied: ' + result.message);
}
```

### When to Use
- Simplifying access to complex subsystems
- Creating API layers for external integrations
- Reducing dependencies on multiple services
- Providing entry points for different client needs

---

## Domain Class Pattern

> 💡 *Principles inspired by "Clean Apex Code" by Pablo Gonzalez.
> [Purchase the book](https://link.springer.com/book/10.1007/979-8-8688-1411-2) for complete coverage.*

### Purpose

Encapsulate business rules in domain-specific classes, making code read like plain English and enabling reuse across the application.

### Implementation

```apex
/**
 * Domain class encapsulating Account business rules
 * Rules live here, not scattered across triggers/services
 */
public class AccountRules {

    public static Boolean isStrategicAccount(Account account) {
        return isEnterpriseCustomer(account) &&
               isHighValue(account) &&
               isInTargetMarket(account);
    }

    public static Boolean isEnterpriseCustomer(Account account) {
        return account.Type == 'Enterprise' &&
               account.NumberOfEmployees > 500;
    }

    public static Boolean isHighValue(Account account) {
        return account.AnnualRevenue != null &&
               account.AnnualRevenue > 1000000;
    }

    public static Boolean isInTargetMarket(Account account) {
        Set<String> targetIndustries = new Set<String>{
            'Technology', 'Finance', 'Healthcare'
        };
        Set<String> targetCountries = new Set<String>{
            'United States', 'Canada', 'United Kingdom'
        };

        return targetIndustries.contains(account.Industry) &&
               targetCountries.contains(account.BillingCountry);
    }

    public static Boolean requiresExecutiveApproval(Account account, Decimal dealValue) {
        return isStrategicAccount(account) && dealValue > 500000;
    }

    public static Boolean isEligibleForDiscount(Account account) {
        return account.Customer_Since__c != null &&
               account.Customer_Since__c.monthsBetween(Date.today()) > 24 &&
               isHighValue(account);
    }
}
```

### Usage

```apex
// Reads like plain English
public void processOpportunity(Opportunity opp, Account account) {
    if (AccountRules.isStrategicAccount(account)) {
        assignToEnterpriseTeam(opp);
    }

    if (AccountRules.requiresExecutiveApproval(account, opp.Amount)) {
        routeForApproval(opp);
    }

    if (AccountRules.isEligibleForDiscount(account)) {
        applyLoyaltyDiscount(opp);
    }
}
```

### When to Use

- Business rules are reused across multiple classes
- Complex boolean logic needs to be readable
- Rules change frequently (centralized = easier updates)
- You want trigger/service code to read like business requirements

### Relationship to Other Patterns

| Pattern | Relationship |
|---------|--------------|
| Selector | Domain class uses Selector for data access |
| Service | Service orchestrates, Domain validates |
| Repository | Domain class is data-agnostic |
| Strategy | Domain rules can use Strategy for variations |

---

## Abstraction Level Management

> 💡 *Principles inspired by "Clean Apex Code" by Pablo Gonzalez.
> [Purchase the book](https://link.springer.com/book/10.1007/979-8-8688-1411-2) for complete coverage.*

### Purpose

Ensure each method operates at a consistent level of abstraction. Don't mix high-level orchestration with low-level implementation details.

### The Problem

```apex
// BAD: Mixed abstraction levels
public void processNewCustomer(Account account) {
    // HIGH-LEVEL: Validation
    validateAccount(account);

    // LOW-LEVEL: String manipulation (doesn't belong here)
    String sanitizedPhone = account.Phone.replaceAll('[^0-9]', '');
    if (sanitizedPhone.length() == 10) {
        sanitizedPhone = '1' + sanitizedPhone;
    }
    account.Phone = '+' + sanitizedPhone;

    // HIGH-LEVEL: Save
    insert account;

    // LOW-LEVEL: HTTP details (doesn't belong here)
    HttpRequest req = new HttpRequest();
    req.setEndpoint('https://api.crm.com/customers');
    req.setMethod('POST');
    req.setHeader('Content-Type', 'application/json');
    req.setBody(JSON.serialize(account));
    Http http = new Http();
    HttpResponse res = http.send(req);

    // HIGH-LEVEL: Notification
    sendWelcomeEmail(account);
}
```

### The Solution

```apex
// GOOD: Consistent high-level abstraction
public void processNewCustomer(Account account) {
    validateAccount(account);
    normalizePhoneNumber(account);
    insert account;
    syncToExternalCRM(account);
    sendWelcomeEmail(account);
}

// Low-level details extracted to focused methods
private void normalizePhoneNumber(Account account) {
    if (String.isBlank(account.Phone)) return;

    String digitsOnly = account.Phone.replaceAll('[^0-9]', '');
    if (digitsOnly.length() == 10) {
        digitsOnly = '1' + digitsOnly;
    }
    account.Phone = '+' + digitsOnly;
}

private void syncToExternalCRM(Account account) {
    CRMIntegrationService.syncCustomer(account);
}
```

### Abstraction Layers in Apex

```
┌─────────────────────────────────────────────────────────────┐
│  TRIGGER LAYER                                              │
│  - Routes events to handlers                                │
│  - No business logic                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  HANDLER/SERVICE LAYER (High-level)                         │
│  - Orchestrates business operations                         │
│  - Coordinates between components                           │
│  - Each step is a method call, not implementation           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  DOMAIN LAYER (Business rules)                              │
│  - Encapsulates business logic                              │
│  - AccountRules, OpportunityRules, etc.                     │
│  - Pure logic, no infrastructure                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  DATA ACCESS LAYER (Low-level)                              │
│  - Selectors for SOQL                                       │
│  - Repositories for DML                                     │
│  - Integration services for external calls                  │
└─────────────────────────────────────────────────────────────┘
```

### Guidelines

| Level | Should Contain | Should NOT Contain |
|-------|---------------|-------------------|
| High (Orchestration) | Method calls, flow control | SOQL, DML, string parsing |
| Mid (Domain) | Business rules, validation | HTTP calls, database queries |
| Low (Data Access) | SOQL, DML, HTTP | Business decisions |

### Signs of Mixed Abstraction

- A method has both `[SELECT ...]` and business logic
- HTTP request building next to email sending
- String manipulation in a method that also updates records
- Governor limit checks scattered among business rules

### Benefits

- Each method is easier to understand in isolation
- Methods at the same level can be tested with similar techniques
- Changes to implementation don't affect orchestration
- Code reads like a high-level description of the process

---

## Pattern Selection Guide

| Need | Pattern |
|------|---------|
| Centralize object creation | Factory |
| Abstract data access | Repository / Selector |
| Build complex objects | Builder |
| Single cached instance | Singleton |
| Interchangeable algorithms | Strategy |
| Transactional DML | Unit of Work |
| Add behavior without modification | Decorator |
| React to state changes | Observer |
| Queue/undo operations | Command |
| Simplify complex systems | Facade |
| Encapsulate business rules | Domain Class |
| Consistent method structure | Abstraction Levels |
