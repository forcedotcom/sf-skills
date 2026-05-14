<!-- Parent: handling-sf-data/SKILL.md -->
# CRUD Workflow Example

Complete end-to-end example of data operations using handling-sf-data skill.

## Scenario

Create a Deal Desk workflow test environment with:
- Accounts with varying revenue tiers
- Contacts as decision makers
- Opportunities at different stages

## Phase 1: Discovery (sf-metadata)

```
Skill(skill="sf-metadata")
Request: "Describe object Account in org dev - show required fields and picklist values"
```

**Response shows:**
- Required: Name
- Picklists: Industry, Type, Rating

## Phase 2: Create Records

### sf CLI - Single Record
```bash
sf data create record \
  --sobject Account \
  --values "Name='Enterprise Corp' Industry='Technology' AnnualRevenue=5000000" \
  --target-org dev \
  --json
```

**Output:**
```json
{
  "status": 0,
  "result": {
    "id": "001XXXXXXXXXXXX",
    "success": true
  }
}
```

### sf CLI - Query Created Record
```bash
sf data query \
  --query "SELECT Id, Name, Industry, AnnualRevenue FROM Account WHERE Name = 'Enterprise Corp'" \
  --target-org dev \
  --json
```

## Phase 3: Update Records

### Update Single Record
```bash
sf data update record \
  --sobject Account \
  --record-id 001XXXXXXXXXXXX \
  --values "Rating='Hot' Type='Customer - Direct'" \
  --target-org dev
```

### Verify Update
```bash
sf data get record \
  --sobject Account \
  --record-id 001XXXXXXXXXXXX \
  --target-org dev
```

## Phase 4: Create Related Records

### Create Contact for Account
```bash
sf data create record \
  --sobject Contact \
  --values "FirstName='John' LastName='Smith' AccountId='001XXXXXXXXXXXX' Title='CTO'" \
  --target-org dev
```

### Create Opportunity
```bash
sf data create record \
  --sobject Opportunity \
  --values "Name='Enterprise Deal' AccountId='001XXXXXXXXXXXX' StageName='Prospecting' CloseDate=2025-03-31 Amount=250000" \
  --target-org dev
```

## Phase 5: Query Relationships

### Parent-to-Child (Subquery)
```bash
sf data query \
  --query "SELECT Id, Name, (SELECT Id, Name, Title FROM Contacts), (SELECT Id, Name, Amount, StageName FROM Opportunities) FROM Account WHERE Name = 'Enterprise Corp'" \
  --target-org dev \
  --json
```

### Child-to-Parent (Dot Notation)
```bash
sf data query \
  --query "SELECT Id, Name, Account.Name, Account.Industry FROM Contact WHERE Account.Name = 'Enterprise Corp'" \
  --target-org dev
```

## Phase 6: Delete Records

### Delete in Correct Order
Children first, then parents:

```bash
# Delete Opportunities
sf data delete record \
  --sobject Opportunity \
  --record-id 006XXXXXXXXXXXX \
  --target-org dev

# Delete Contacts
sf data delete record \
  --sobject Contact \
  --record-id 003XXXXXXXXXXXX \
  --target-org dev

# Delete Account
sf data delete record \
  --sobject Account \
  --record-id 001XXXXXXXXXXXX \
  --target-org dev
```

## Anonymous Apex Alternative

For complex operations, use Anonymous Apex:

```apex
// Create complete hierarchy in one transaction
Account acc = new Account(
    Name = 'Enterprise Corp',
    Industry = 'Technology',
    AnnualRevenue = 5000000
);
insert acc;

Contact con = new Contact(
    FirstName = 'John',
    LastName = 'Smith',
    AccountId = acc.Id,
    Title = 'CTO'
);
insert con;

Opportunity opp = new Opportunity(
    Name = 'Enterprise Deal',
    AccountId = acc.Id,
    ContactId = con.Id,
    StageName = 'Prospecting',
    CloseDate = Date.today().addDays(90),
    Amount = 250000
);
insert opp;

System.debug('Created hierarchy: Account=' + acc.Id + ', Contact=' + con.Id + ', Opp=' + opp.Id);
```

Execute:
```bash
sf apex run --file create-hierarchy.apex --target-org dev
```

## Validation Score

```
Score: 125/130 ⭐⭐⭐⭐⭐ Excellent
├─ Query Efficiency: 25/25 (indexed fields, no N+1)
├─ Bulk Safety: 23/25 (single records OK for demo)
├─ Data Integrity: 20/20 (all required fields)
├─ Security & FLS: 20/20 (no PII exposed)
├─ Test Patterns: 12/15 (single record demo)
├─ Cleanup & Isolation: 15/15 (proper delete order)
└─ Documentation: 10/10 (fully documented)
```
