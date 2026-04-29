# Common Validation Rule Formula Patterns

## Required field (non-blank)

```
ISBLANK(Field__c)
```

Error: "Field is required."

## Required field only on specific record type

```
AND(
  RecordType.DeveloperName = "Enterprise",
  ISBLANK(Field__c)
)
```

## Numeric range check

```
OR(
  Amount__c <= 0,
  Amount__c > 1000000
)
```

Error: "Amount must be between 1 and 1,000,000."

## Date must be in the future

```
Close_Date__c <= TODAY()
```

Error: "Close date must be after today."

## Date comparison (end after start)

```
End_Date__c <= Start_Date__c
```

Error: "End date must be after start date."

## Field changed validation (update only)

```
AND(
  NOT(ISNEW()),
  ISCHANGED(Stage__c),
  ISPICKVAL(PRIORVALUE(Stage__c), "Closed Won")
)
```

Error: "Cannot change stage after Closed Won."

## Bypass with Custom Permission

Wrap any formula to allow admin bypass:

```
AND(
  NOT($Permission.Bypass_Validation_Rules),
  {your formula here}
)
```

## Regex pattern match (email format)

```
NOT(REGEX(Email__c, "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"))
```

## Cross-field dependency

```
AND(
  ISPICKVAL(Type__c, "Partner"),
  ISBLANK(Partner_Account__c)
)
```

Error: "Partner Account is required when Type is Partner."
