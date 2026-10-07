# Phase 5: Accounting Setup

All creates use `dispatch POST /sobjects/<Object>` with a JSON body.
All queries use `dispatch GET /query?q=<SOQL>`.

## Correct API Names

| Concept | API Object | Key Fields |
|---------|-----------|------------|
| Accounting Period | AccountingPeriod | Name, FinancialYear, StartDate, EndDate, Status (Open/Closed) |
| GL Account | GeneralLedgerAccount | AccountingCode (number), AccountingName (display), Type. Name is auto-generated. |
| GLAAR Rule | GeneralLedgerAcctAsgntRule | Name, TransactionType, LegalEntityId, Status, Priority, FilterCriteria |
| Journal Entry Rule | GeneralLedgerJrnlEntryRule | GeneralLedgerAcctAsgntRuleId, TransactionAmountField, Percentage, DebitGeneralLedgerAccountId, CreditGeneralLedgerAccountId |
| LE Accounting Period | LegalEntyAccountingPeriod | LegalEntityId, AccountingPeriodId, Status. Name is auto-generated. |

---

## Step 1: Accounting Periods

Compute dates at runtime. Use FY label format: `FY {YYYY}-{YY+1}` (e.g., `FY 2026-27`).

**Query existing:**
```text
dispatch GET /query?q=SELECT+Id,Name,FinancialYear,StartDate,EndDate,Status+FROM+AccountingPeriod+WHERE+FinancialYear='FY+<year>-<nextYearShort>'+ORDER+BY+StartDate
```

**Create monthly periods for gaps only.** Naming convention: `FY {year}-{nextYearShort}-{MonthName}{startDay}-{MonthName}{endDay}`

Example — January 2026:
```text
dispatch POST /sobjects/AccountingPeriod
{"Name": "FY 2026-27-January1-January31", "FinancialYear": "FY 2026-27", "StartDate": "2026-01-01", "EndDate": "2026-01-31", "Status": "Open"}
```

---

## Step 2: Legal Entity Accounting Periods

Link each accounting period to the Legal Entity.

**Query existing:**
```text
dispatch GET /query?q=SELECT+Id,LegalEntityId,AccountingPeriodId,Status+FROM+LegalEntyAccountingPeriod+WHERE+LegalEntityId='<LEGAL_ENTITY_ID>'
```

**Create missing linkages** (Name is auto-generated, do NOT include):
```text
dispatch POST /sobjects/LegalEntyAccountingPeriod
{"LegalEntityId": "<LE_ID>", "AccountingPeriodId": "<AP_ID>", "Status": "Open"}
```

---

## Step 3: General Ledger Accounts (11 total)

**Query by AccountingCode:**
```text
dispatch GET /query?q=SELECT+Id,Name,AccountingCode,AccountingName,Type+FROM+GeneralLedgerAccount+WHERE+AccountingCode+IN+('1110','1120','1210','2110','2120','2410','2510','4110','4210','5110','5200')+ORDER+BY+AccountingCode
```

| Code | AccountingName | Type |
|------|---------------|------|
| 1110 | Cash - Operating | Asset |
| 1120 | Cash - Premium Trust | Asset |
| 1210 | Premiums Receivable - Insured | Asset |
| 2110 | Accounts Payable - Carrier | Liability |
| 2120 | Accounts Payable - Carrier Fees | Liability |
| 2410 | Commission Payable | Liability |
| 2510 | Tax Payable | Liability |
| 4110 | Commission Income | Revenue |
| 4210 | Fee Income | Revenue |
| 5110 | Commission Expense | Expense |
| 5200 | Salaries & General Admin | Expense |

**Create** (Name is auto-generated, do NOT include):
```text
dispatch POST /sobjects/GeneralLedgerAccount
{"AccountingName": "Cash - Operating", "AccountingCode": "1110", "Type": "Asset", "LegalEntityId": "<LE_ID>"}
```

---

## Step 4: GLAAR Rules (Parent + Child)

GLAAR uses parent-child structure. Debit/credit accounts go on the CHILD, not the parent.

**Query existing parents:**
```text
dispatch GET /query?q=SELECT+Id,Name,TransactionType,LegalEntityId,Status,FilterCriteria,Priority+FROM+GeneralLedgerAcctAsgntRule+ORDER+BY+Name
```

**Query existing children:**
```text
dispatch GET /query?q=SELECT+Id,GeneralLedgerAcctAsgntRuleId,TransactionAmountField,Percentage,DebitGeneralLedgerAccountId,CreditGeneralLedgerAccountId+FROM+GeneralLedgerJrnlEntryRule+ORDER+BY+GeneralLedgerAcctAsgntRuleId
```

**Default rule — Posted Invoice Assignment:**

Parent (create as Inactive first — Active requires child journal entry rule to exist; valid Status values: Active, Inactive — no Draft):
```text
dispatch POST /sobjects/GeneralLedgerAcctAsgntRule
{"Name": "Posted Invoice Assignment Rule", "TransactionType": "InvoiceLine", "LegalEntityId": "<LE_ID>", "Status": "Inactive", "FilterCriteria": "All", "Priority": 1}
```

Child:
```text
dispatch POST /sobjects/GeneralLedgerJrnlEntryRule
{"GeneralLedgerAcctAsgntRuleId": "<RULE_ID>", "TransactionAmountField": "ChargeAmount", "Percentage": 100, "DebitGeneralLedgerAccountId": "<GL_1210_ID>", "CreditGeneralLedgerAccountId": "<GL_2110_ID>"}
```

Activate parent after child exists:
```text
dispatch PATCH /sobjects/GeneralLedgerAcctAsgntRule/<RULE_ID>
{"Status": "Active"}
```

**Available TransactionType values:** Invoice, InvoiceLine, InvoiceLineTax, CreditMemo, CreditMemoLine, CreditMemoLineTax, Payment, Refund, PaymentLineInvoice, PaymentLineInvoiceLine, CreditMemoInvApplication, CreditMemoLineInvoiceLine, RefundLinePayment, DebitMemoLine, DebitMemoLineTax
