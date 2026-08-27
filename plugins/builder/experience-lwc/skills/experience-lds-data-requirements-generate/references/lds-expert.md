# LDS Expert

Apply the LDS guidelines below when analyzing data requirements from PRDs, user asks, or LWC source files. Sections 1–3 produce structured requirement, validation, and recommendation entries from natural-language or code inputs; sections 4–5 detect and fix code-level anti-patterns in LWC source.

## 1 — Requirements Analysis for LDS data needs

For every data-related TODO, comment, or partial implementation in the LWC source, produce one requirement entry with these fields:

- **`operation`** — exactly one of `READ`, `CREATE`, `UPDATE`, `DELETE`. If the source phrasing is ambiguous (`"sync"`, `"refresh"`, `"manage"`), set `operation` to the single best fit and add a one-line note in `assumptions`.
- **`object`** — the Salesforce object API name (e.g. `Account`, `Gym__c`). Custom-object terms (`Gym`, `Property`, `Course`) require explicit `__c` resolution via the API-name validation rules below.
- **`fields`** — the list of field API names touched. Generic terms (`"phone"`, `"address"`, `"name"`, `"status"`) must be disambiguated to a specific API name.
- **`scope`** — exactly one of `SINGLE_RECORD`, `RELATED_LIST`, `MULTI_OBJECT`, `QUERY`. Drives adapter selection in section 3.
- **`trigger`** — exactly one of `MOUNT`, `USER_ACTION`, `EXTERNAL_EVENT`. Drives wire-vs-imperative selection in section 3.
- **`assumptions`** — (optional) one-line note present only when `operation` was inferred from ambiguous source phrasing (e.g. `"sync"` → `UPDATE — assumed based on verb context`).

Source code with clear, specific LDS implementations or non-data TODOs produces no entry. Comments that already explicitly acknowledge the need for clarification (`// TODO: confirm field API name with admin`) are considered resolved by the comment and produce no new entry.

## 2 — API name validation

For each Salesforce object or field reference in the source, produce one validation entry with these fields:

- **`reference`** — the object or field name as written (e.g. `Account.Phone`, `Gym__c.Capacity__c`).
- **`status`** — exactly one of `VERIFIED`, `UNVERIFIED`, `AMBIGUOUS`.
- **`source`** — for `VERIFIED`, the source of truth (e.g. `standard object — SObject describe`, `FieldDefinition row`). For `UNVERIFIED`/`AMBIGUOUS`, the missing input (e.g. `no SObject describe for Gym__c in target org`, `caller must select between Phone and MobilePhone`).
- **`resolution`** — the corrected API name with exact `__c` suffix and capitalization. For `UNVERIFIED`, prefix with `UNVERIFIED:` followed by the best-guess name.

**Auto-verified** references: standard objects with exact casing — `Account`, `Contact`, `Lead`, `Opportunity`, `Case`, `User`, `Task`, `Event`, `Product2`, `Pricebook2`, `Order`, `OrderItem`, `Asset`, `Contract`, `Campaign` — and their standard fields per the precision mapping below.

**Standard field precision mapping**

- `Account`: `Name`, `Phone`, `Website`, `BillingAddress`, `ShippingAddress`, `Industry`, `Type`, `Description`.
- `Contact`: `FirstName`, `LastName`, `Name`, `Email`, `Phone`, `MobilePhone`, `MailingAddress`, `Department`, `Title`.
- `Opportunity`: `Name`, `StageName`, `CloseDate`, `Amount`, `Probability`, `AccountId`, `Type`.
- `Case`: `Subject`, `Status`, `Priority`, `Origin`, `Description`, `ContactId`, `AccountId`.

**Generic-term disambiguation**

- `"phone"` → `Phone`, `MobilePhone`, `HomePhone`, `OtherPhone`, or `WorkPhone`.
- `"address"` → `BillingAddress`, `ShippingAddress`, `MailingAddress`, or `OtherAddress`.
- `"name"` → `Name` (full), `FirstName`, `LastName`, or `CompanyName` per object.
- `"status"` → `Status`, `StageName`, or the custom status field.

Do not emit `TODO` comments — the validation entry above is the production output.

## 3 — API recommendation

Use this priority order when selecting the data-access API for each requirement entry produced in section 1:

1. **GraphQL wire adapter (`lightning/graphql`)** — top choice for all read scenarios it supports.
2. **UI API / Lightning Data Service** — second choice for CRUD writes, metadata, layouts, picklists, and simple reads.
3. **Apex** — fallback only when GraphQL and UI API cannot meet the requirement.

**Decision framework**

| Requirement shape                              | Recommended API | Reason                                                      |
| ---------------------------------------------- | --------------- | ----------------------------------------------------------- |
| Read-only on UI-API-supported object/fields    | GraphQL         | Adapter supports it; reduces round trips                    |
| Multi-object / parent-child read               | GraphQL         | Nested queries in one call                                  |
| Filtering / sorting / pagination / aggregation | GraphQL         | SOQL-like + native cursor support                           |
| Single-record CRUD on supported object         | UI API          | `getRecord`, `createRecord`, `updateRecord`, `deleteRecord` |
| Metadata (picklists, object info, layouts)     | UI API          | `getPicklistValues`, `getObjectInfo`, `getLayout`           |
| Record-create with defaults                    | UI API          | `getRecordCreateDefaults` + `createRecord`                  |
| List views                                     | UI API          | `getListUi`, `getListInfoByName`                            |
| Multi-record atomic transaction                | Apex            | UI API has no atomic batch                                  |
| Object/field unsupported by UI API             | Apex            | UI API allowlist gap                                        |
| Custom business logic / elevated permissions   | Apex            | System context required                                     |

**Output contract** — for each requirement from section 1, produce one recommendation entry with:

- **`dataNeed`** — one-sentence description referencing the source requirement.
- **`api`** — exactly one of `GraphQL`, `UIAPI`, `Apex`.
- **`reason`** — one sentence pointing at the row above that selected the API.
- **`adapter`** — the specific adapter or method (e.g. `@wire(graphql, ...)`, `getRecord`, `@AuraEnabled Apex method <name>`).

When the source contains no data needs, produce an empty list. Do not emit `TODO` comments in the LWC code or PRD — the recommendation entry is the production output.

## 4 — Wire adapter migration to state managers

When the source uses any of the legacy `@wire` adapters below, produce one migration entry per adapter occurrence — including the file location, the legacy adapter, the modern replacement, and the call-site code change required.

| Legacy `@wire` adapter                                      | Replacement (`lightning/stateManagersUiapi`) |
| ----------------------------------------------------------- | -------------------------------------------- |
| `graphql` (from `lightning/graphql`)                        | `smGraphQL`                                  |
| `getLayout` (from `lightning/uiLayoutApi`)                  | `smLayout`                                   |
| `getObjectInfo` (from `lightning/uiObjectInfoApi`)          | `smObjectInfo`                               |
| `getObjectInfos` (from `lightning/uiObjectInfoApi`)         | `smObjectInfos`                              |
| `getRecord` (from `lightning/uiRecordApi`)                  | `smRecord`                                   |
| `getRelatedListInfo` (from `lightning/uiRelatedListApi`)    | `smRelatedListInfo`                          |
| `getRelatedListRecords` (from `lightning/uiRelatedListApi`) | `smRelatedListRecords`                       |
| `getRelatedListsInfo` (from `lightning/uiRelatedListApi`)   | `smRelatedListsInfo`                         |

**Scope rules**

- Only `@wire` usages of the legacy adapters trigger an entry. Imperative usage of the same modules is out of scope.
- Bare import statements without `@wire` usage produce no entry.
- Other `@wire` adapters not in the table produce no entry.

Produce the migration entry directly in the output; do not emit `TODO` comments to defer the migration.

## 5 — GraphQL `refresh` usage (anti-pattern fixes)

When the source uses `@wire(graphql, ...)` from `lightning/graphql` and any of the patterns below occurs, produce one fix entry with the corrected code per the corresponding correct pattern below. The `lightning/uiGraphQLApi` `refreshGraphQL` standalone function is a different API and is out of scope.

**Anti-patterns**

```js
// BAD — not destructuring refresh from the wire result
@wire(graphql, { query: myQuery })
wiredResult({ data, errors }) {
  this.data = data;
}
handleRefresh() { /* refresh unavailable */ }

// BAD — not awaiting the refresh promise when downstream code depends on it
async handleRefresh() {
  this._refresh();
  this.processData(); // may run before refresh completes
}

// BAD — calling refresh without an existence check (wire may not have resolved)
handleRefresh() { this._refresh(); }

// BAD — mutation without refreshing the related GraphQL query
async handleCreateContact() {
  await executeMutation({ query: createContactMutation });
  // cache stale — must refresh
}

// BAD — external data change (Apex / CDC / LMS) without refreshing the GraphQL query
async handleUpdateViaApex() { await updateRecordsApex({ ... }); }
subscribe('/data/AccountChangeEvent', -1, (msg) => { /* no refresh */ });
handleRecordUpdate(msg) { if (msg.objectApiName === 'Contact') { /* no refresh */ } }
```

**Correct patterns**

```js
@wire(graphql, { query: contactsQuery })
wiredContacts({ data, errors, refresh }) {
  this.contacts = data?.uiapi?.query?.Contact?.edges?.map(e => e.node);
  this.errors = errors;
  this._refreshContacts = refresh;
}

async handleRefresh() {
  if (this._refreshContacts) {
    await this._refreshContacts();
  }
}

async handleCreateContact() {
  await executeMutation({ query: createContactMutation, variables: { /* ... */ } });
  if (this._refreshContacts) {
    await this._refreshContacts();
  }
}

async handleUpdateViaApex() {
  await updateRecordsApex({ recordIds: this.ids });
  if (this._refreshRecords) {
    await this._refreshRecords();
  }
}

subscribeToChanges() {
  subscribe('/data/AccountChangeEvent', -1, async (message) => {
    if (this._refreshAccounts) {
      await this._refreshAccounts();
    }
  });
}

async handleRecordUpdate(message) {
  if (message.objectApiName === 'Contact' && this._refreshContacts) {
    await this._refreshContacts();
  }
}
```

For each occurrence, produce the corrected snippet directly; do not flag the issue with a `TODO`. When the source has no `@wire(graphql, ...)` usage, produce an empty list.
