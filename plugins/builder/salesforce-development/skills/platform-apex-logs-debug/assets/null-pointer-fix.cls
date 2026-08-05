/**
 * NULL POINTER EXCEPTION FIX PATTERNS
 *
 * Problem: System.NullPointerException when accessing null object properties
 * Detection: DEBUG LOG shows EXCEPTION_THROWN|NullPointerException
 *
 * This template demonstrates null-safe coding patterns.
 */

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 1: SOQL QUERY RETURNING NO RESULTS
// ═══════════════════════════════════════════════════════════════════════════

public class QueryNullSafety {

    // BEFORE: Dangerous - throws exception if no results
    public String getAccountNameUNSAFE(Id accountId) {
        Account acc = [SELECT Name FROM Account WHERE Id = :accountId];
        return acc.Name;  // NullPointerException if query returns nothing!
    }

    // AFTER: Safe - using List and isEmpty check
    public String getAccountNameSAFE(Id accountId) {
        List<Account> accounts = [SELECT Name FROM Account WHERE Id = :accountId LIMIT 1];

        if (accounts.isEmpty()) {
            return null;  // Or throw custom exception, or return default
        }

        return accounts[0].Name;
    }

    // AFTER: Safe - using Safe Navigation Operator (API 62.0+)
    public String getAccountNameSafeNav(Id accountId) {
        Account acc = [SELECT Name FROM Account WHERE Id = :accountId LIMIT 1];
        return acc?.Name;  // Returns null instead of throwing exception
    }

    // AFTER: With default value
    public String getAccountNameWithDefault(Id accountId, String defaultName) {
        List<Account> accounts = [SELECT Name FROM Account WHERE Id = :accountId LIMIT 1];
        return accounts.isEmpty() ? defaultName : accounts[0].Name;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 2: MAP ACCESS
// ═══════════════════════════════════════════════════════════════════════════

public class MapNullSafety {

    // BEFORE: Dangerous - Map.get() returns null for missing keys
    public void processAccountUNSAFE(Map<Id, Account> accountMap, Id targetId) {
        Account acc = accountMap.get(targetId);
        String name = acc.Name;  // NullPointerException if targetId not in map!
    }

    // AFTER: Check containsKey first
    public void processAccountSAFE(Map<Id, Account> accountMap, Id targetId) {
        if (accountMap.containsKey(targetId)) {
            Account acc = accountMap.get(targetId);
            String name = acc.Name;
            // Process...
        }
    }

    // AFTER: Check for null after get
    public void processAccountNullCheck(Map<Id, Account> accountMap, Id targetId) {
        Account acc = accountMap.get(targetId);
        if (acc != null) {
            String name = acc.Name;
            // Process...
        }
    }

    // AFTER: Safe navigation (API 62.0+)
    public String getAccountNameFromMap(Map<Id, Account> accountMap, Id targetId) {
        return accountMap.get(targetId)?.Name;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 3: RELATIONSHIP FIELDS
// ═══════════════════════════════════════════════════════════════════════════

public class RelationshipNullSafety {

    // BEFORE: Dangerous - parent record might be null
    public String getOwnerEmailUNSAFE(Contact c) {
        return c.Account.Owner.Email;  // Multiple potential null points!
    }

    // AFTER: Check each level
    public String getOwnerEmailSAFE(Contact c) {
        if (c == null) return null;
        if (c.Account == null) return null;
        if (c.Account.Owner == null) return null;
        return c.Account.Owner.Email;
    }

    // AFTER: Safe navigation chain (API 62.0+)
    public String getOwnerEmailSafeNav(Contact c) {
        return c?.Account?.Owner?.Email;
    }

    // AFTER: With default value
    public String getOwnerEmailWithDefault(Contact c, String defaultEmail) {
        String email = c?.Account?.Owner?.Email;
        return String.isBlank(email) ? defaultEmail : email;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 4: LIST ACCESS
// ═══════════════════════════════════════════════════════════════════════════

public class ListNullSafety {

    // BEFORE: Dangerous - list might be null or empty
    public Contact getFirstContactUNSAFE(List<Contact> contacts) {
        return contacts[0];  // IndexOutOfBoundsException if empty!
    }

    // AFTER: Check null and empty
    public Contact getFirstContactSAFE(List<Contact> contacts) {
        if (contacts == null || contacts.isEmpty()) {
            return null;
        }
        return contacts[0];
    }

    // Pattern: Null-safe iteration
    public void processContactsSAFE(List<Contact> contacts) {
        // This is safe - for loop on null list doesn't execute
        for (Contact c : contacts ?? new List<Contact>()) {
            // Process contact
        }
    }

    // Alternative: Early return
    public void processContactsEarlyReturn(List<Contact> contacts) {
        if (contacts == null || contacts.isEmpty()) {
            return;
        }

        for (Contact c : contacts) {
            // Process contact
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 5: STRING OPERATIONS
// ═══════════════════════════════════════════════════════════════════════════

public class StringNullSafety {

    // BEFORE: Dangerous - string might be null
    public Boolean containsKeywordUNSAFE(String text, String keyword) {
        return text.contains(keyword);  // NullPointerException if text is null!
    }

    // AFTER: Use String.isNotBlank() or String.isBlank()
    public Boolean containsKeywordSAFE(String text, String keyword) {
        if (String.isBlank(text) || String.isBlank(keyword)) {
            return false;
        }
        return text.contains(keyword);
    }

    // Pattern: Null-safe string comparison
    public Boolean isEqualSAFE(String a, String b) {
        // Both null = equal
        if (a == null && b == null) return true;
        // One null = not equal
        if (a == null || b == null) return false;
        // Both non-null = compare
        return a.equals(b);
    }

    // Pattern: Default value for null strings
    public String getNameWithDefault(Account acc) {
        return String.isBlank(acc?.Name) ? 'Unnamed Account' : acc.Name;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN 6: TRIGGER CONTEXT
// ═══════════════════════════════════════════════════════════════════════════

public class TriggerNullSafety {

    /**
     * In triggers, old values might not exist (insert)
     * and new values might not exist (delete)
     */
    public void handleTrigger() {
        // Safe: Check context first
        if (Trigger.isInsert) {
            // Trigger.old is null in insert context
            for (Account acc : (List<Account>)Trigger.new) {
                // Process new records
            }
        }

        if (Trigger.isUpdate) {
            Map<Id, Account> oldMap = (Map<Id, Account>)Trigger.oldMap;
            for (Account newAcc : (List<Account>)Trigger.new) {
                Account oldAcc = oldMap.get(newAcc.Id);
                // Both old and new are available
                if (oldAcc.Status__c != newAcc.Status__c) {
                    // Status changed
                }
            }
        }

        if (Trigger.isDelete) {
            // Trigger.new is null in delete context
            for (Account acc : (List<Account>)Trigger.old) {
                // Process deleted records
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// ANTI-PATTERN: OVER-DEFENSIVE CODING
// ═══════════════════════════════════════════════════════════════════════════

public class OverDefensiveCoding {

    /**
     * Don't check for null when it's impossible
     * This adds unnecessary code and cognitive load
     */

    // UNNECESSARY: Trigger.new is never null in insert/update context
    public void badExample() {
        if (Trigger.new != null && !Trigger.new.isEmpty()) {
            for (SObject record : Trigger.new) {
                // Trigger.new is guaranteed non-null in before/after insert/update
            }
        }
    }

    // CORRECT: Trust the platform guarantees
    public void goodExample() {
        for (Account acc : (List<Account>)Trigger.new) {
            // Just use it - Trigger.new is guaranteed in this context
        }
    }
}
