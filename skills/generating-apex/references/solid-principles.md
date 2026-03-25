# SOLID Principles in Apex

## Overview

SOLID principles guide object-oriented design for maintainable, flexible code.

| Principle | Summary |
|-----------|---------|
| **S**ingle Responsibility | One reason to change |
| **O**pen/Closed | Open for extension, closed for modification |
| **L**iskov Substitution | Subtypes must be substitutable |
| **I**nterface Segregation | Small, specific interfaces |
| **D**ependency Inversion | Depend on abstractions |

---

## S - Single Responsibility Principle

> "A module should have one, and only one, reason to change."

### Problem: Multiple Responsibilities

```apex
// BAD: Class has multiple reasons to change
public class OrderProcessor {
    public void processOrder(Order__c order) {
        // Validate order (reason 1: validation rules change)
        if (order.Total__c <= 0) {
            throw new ValidationException('Invalid total');
        }

        // Calculate tax (reason 2: tax rules change)
        Decimal tax = order.Total__c * 0.08;
        order.Tax__c = tax;

        // Send email (reason 3: notification requirements change)
        Messaging.SingleEmailMessage email = new Messaging.SingleEmailMessage();
        email.setToAddresses(new List<String>{order.Customer_Email__c});
        Messaging.sendEmail(new List<Messaging.Email>{email});

        // Save to database (reason 4: persistence logic changes)
        update order;
    }
}
```

### Solution: Separate Responsibilities

```apex
// GOOD: Each class has single responsibility
public class OrderValidator {
    public void validate(Order__c order) {
        if (order.Total__c <= 0) {
            throw new ValidationException('Invalid total');
        }
    }
}

public class TaxCalculator {
    public Decimal calculate(Decimal amount) {
        return amount * 0.08;
    }
}

public class OrderNotificationService {
    public void sendConfirmation(Order__c order) {
        // Email logic
    }
}

public class OrderService {
    private OrderValidator validator;
    private TaxCalculator taxCalc;
    private OrderNotificationService notifier;

    public void processOrder(Order__c order) {
        validator.validate(order);
        order.Tax__c = taxCalc.calculate(order.Total__c);
        update order;
        notifier.sendConfirmation(order);
    }
}
```

---

## O - Open/Closed Principle

> "Software entities should be open for extension, but closed for modification."

### Problem: Modifying Existing Code

```apex
// BAD: Must modify class to add new discount type
public class DiscountCalculator {
    public Decimal calculate(String discountType, Decimal amount) {
        if (discountType == 'PERCENTAGE') {
            return amount * 0.1;
        } else if (discountType == 'FIXED') {
            return 50;
        } else if (discountType == 'VIP') {  // Added later
            return amount * 0.2;
        }
        // Keep adding else-if for each new type...
        return 0;
    }
}
```

### Solution: Extend Without Modifying

```apex
// GOOD: Add new discount types without changing existing code
public interface DiscountStrategy {
    Decimal calculate(Decimal amount);
}

public class PercentageDiscount implements DiscountStrategy {
    private Decimal rate;

    public PercentageDiscount(Decimal rate) {
        this.rate = rate;
    }

    public Decimal calculate(Decimal amount) {
        return amount * rate;
    }
}

public class FixedDiscount implements DiscountStrategy {
    private Decimal fixedAmount;

    public FixedDiscount(Decimal fixedAmount) {
        this.fixedAmount = fixedAmount;
    }

    public Decimal calculate(Decimal amount) {
        return fixedAmount;
    }
}

// To add VIP discount: create new class, no modification needed
public class VIPDiscount implements DiscountStrategy {
    public Decimal calculate(Decimal amount) {
        return amount * 0.2;
    }
}

public class DiscountCalculator {
    private Map<String, DiscountStrategy> strategies;

    public Decimal calculate(String type, Decimal amount) {
        DiscountStrategy strategy = strategies.get(type);
        return strategy?.calculate(amount) ?? 0;
    }
}
```

### Real-World Example: Trigger Actions Framework

TAF follows OCP - add new behaviors via metadata configuration without modifying the trigger or handler.

---

## L - Liskov Substitution Principle

> "Subtypes must be substitutable for their base types."

### Problem: Subtype Breaks Contract

```apex
// BAD: Lead violates SObject update contract when converted
public class RecordUpdater {
    public void updateRecord(SObject record) {
        // This fails for converted Leads!
        if (record instanceof Lead) {
            Lead l = (Lead)record;
            if ([SELECT IsConverted FROM Lead WHERE Id = :l.Id].IsConverted) {
                return;  // Can't update converted lead
            }
        }
        update record;
    }
}
```

### Solution: Design for Substitutability

```apex
// GOOD: Interface defines clear contract
public interface Updatable {
    Boolean canUpdate();
    void performUpdate();
}

public class AccountUpdater implements Updatable {
    private Account record;

    public Boolean canUpdate() {
        return true;  // Accounts can always be updated
    }

    public void performUpdate() {
        update record;
    }
}

public class LeadUpdater implements Updatable {
    private Lead record;

    public Boolean canUpdate() {
        return ![SELECT IsConverted FROM Lead WHERE Id = :record.Id].IsConverted;
    }

    public void performUpdate() {
        if (canUpdate()) {
            update record;
        }
    }
}

// Consumer doesn't need type checking
public class RecordService {
    public void updateRecord(Updatable record) {
        if (record.canUpdate()) {
            record.performUpdate();
        }
    }
}
```

---

## I - Interface Segregation Principle

> "Clients should not be forced to depend on interfaces they don't use."

### Problem: Fat Interface

```apex
// BAD: Interface forces unnecessary implementations
public interface RecordProcessor {
    void validate(SObject record);
    void calculate(SObject record);
    void sendNotification(SObject record);
    void createAuditLog(SObject record);
    void syncToExternal(SObject record);
}

// Simple processor forced to implement everything
public class SimpleProcessor implements RecordProcessor {
    public void validate(SObject record) { /* actual logic */ }
    public void calculate(SObject record) { /* actual logic */ }

    // Forced to implement these even though not needed
    public void sendNotification(SObject record) { }
    public void createAuditLog(SObject record) { }
    public void syncToExternal(SObject record) { }
}
```

### Solution: Small, Focused Interfaces

```apex
// GOOD: Segregated interfaces
public interface Validatable {
    void validate(SObject record);
}

public interface Calculable {
    void calculate(SObject record);
}

public interface Notifiable {
    void sendNotification(SObject record);
}

public interface Auditable {
    void createAuditLog(SObject record);
}

// Implement only what you need
public class SimpleProcessor implements Validatable, Calculable {
    public void validate(SObject record) { /* logic */ }
    public void calculate(SObject record) { /* logic */ }
}

public class FullProcessor implements Validatable, Calculable, Notifiable, Auditable {
    public void validate(SObject record) { /* logic */ }
    public void calculate(SObject record) { /* logic */ }
    public void sendNotification(SObject record) { /* logic */ }
    public void createAuditLog(SObject record) { /* logic */ }
}
```

### Salesforce Example: Database.Batchable Options

```apex
// Implement only what you need
public class SimpleBatch implements Database.Batchable<SObject> {
    // Just the required interface
}

public class StatefulBatch implements Database.Batchable<SObject>, Database.Stateful {
    // Add stateful when needed
}

public class CalloutBatch implements Database.Batchable<SObject>, Database.AllowsCallouts {
    // Add callouts when needed
}
```

---

## D - Dependency Inversion Principle

> "High-level modules should not depend on low-level modules. Both should depend on abstractions."

### Problem: Direct Dependencies

```apex
// BAD: High-level class depends on concrete implementation
public class OrderService {
    private EmailService emailService;      // Concrete class
    private StripePaymentGateway gateway;   // Concrete class

    public OrderService() {
        this.emailService = new EmailService();
        this.gateway = new StripePaymentGateway();
    }

    public void processOrder(Order__c order) {
        gateway.charge(order.Total__c);
        emailService.send(order.Customer_Email__c);
    }
}
```

### Solution: Depend on Abstractions

```apex
// GOOD: Depend on interfaces, inject implementations
public interface PaymentGateway {
    PaymentResult charge(Decimal amount);
}

public interface NotificationService {
    void send(String recipient, String message);
}

public class StripeGateway implements PaymentGateway {
    public PaymentResult charge(Decimal amount) {
        // Stripe-specific logic
    }
}

public class EmailNotification implements NotificationService {
    public void send(String recipient, String message) {
        // Email-specific logic
    }
}

// High-level class depends on abstractions
public class OrderService {
    private PaymentGateway gateway;
    private NotificationService notifier;

    // Constructor injection
    public OrderService(PaymentGateway gateway, NotificationService notifier) {
        this.gateway = gateway;
        this.notifier = notifier;
    }

    public void processOrder(Order__c order) {
        gateway.charge(order.Total__c);
        notifier.send(order.Customer_Email__c, 'Order confirmed');
    }
}

// Easy to test with mocks
@isTest
static void testOrderService() {
    PaymentGateway mockGateway = new MockPaymentGateway();
    NotificationService mockNotifier = new MockNotificationService();

    OrderService service = new OrderService(mockGateway, mockNotifier);
    // Test without real payment or email
}
```

---

## Summary

| Principle | Violation Sign | Solution |
|-----------|---------------|----------|
| SRP | Class has multiple reasons to change | Split into focused classes |
| OCP | Adding features requires modifying existing code | Use strategy pattern, interfaces |
| LSP | Type checking before using base type | Redesign hierarchy, use composition |
| ISP | Empty method implementations | Split into smaller interfaces |
| DIP | Creating concrete dependencies in constructor | Inject dependencies via constructor |
