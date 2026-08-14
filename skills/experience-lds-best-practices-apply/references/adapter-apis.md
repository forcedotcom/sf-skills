# LDS UI API Adapter Reference

Per-adapter API docs (Syntax, Parameters, Returns, Usage) for every UI API wire adapter and imperative method, rendered verbatim from the same source the legacy `explore_lds_uiapi` MCP tool returned. Adapters are grouped by family below; each adapter is a `# \`<adapterName>\``block delimited by`---`. Grep for the backticked name (e.g. `` # `getRecord` ``) to jump to its entry.

## Adapter directory

### uiRecordApis

- `createRecord`
- `deleteRecord`
- `getRecord`
- `getRecords`
- `updateRecord`

### uiListsApis

- `createListInfo`
- `deleteListInfo`
- `getListInfoByName`
- `getListInfosByName`
- `getListInfosByObjectName`
- `getListObjectInfo`
- `getListPreferences`
- `getListRecordsByName`
- `updateListInfoByName`
- `updateListPreferences`

### uiRelatedListApis

- `getRelatedListCount`
- `getRelatedListInfo`
- `getRelatedListInfoBatch`
- `getRelatedListRecords`
- `getRelatedListRecordsBatch`
- `getRelatedListsInfo`

### uiObjectInfoApis

- `getObjectInfo`
- `getObjectInfos`
- `getPicklistValuesByRecordType`
- `getPicklistValues`

# `createRecord(recordInput)`

Creates a record.

## Syntax

```js
import { createRecord } from 'lightning/uiRecordApi';
createRecord(recordInput: Record): Promise<Record>;
```

## Parameters

- **`recordInput`** (Object, Required) – A RecordInput object used to create the record.

### `recordInput` Properties

- **`apiName`** (String, Required) – API name of a supported object.
- **`fields`** (Object) – Map of field names to field values.

## Returns

A Promise that resolves with the created record, containing data for the fields in the record layout.

## Usage

Use `createRecord` by passing in a `recordInput` object with `apiName` and `fields` properties.

```js
import { createRecord } from 'lightning/uiRecordApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';
import NAME_FIELD from '@salesforce/schema/Account.Name';

export default class CreateRecordExample extends LightningElement {
  name;

  handleInput(event) {
    this.name = event.target.value;
  }

  async handleCreate() {
    const fields = { [NAME_FIELD.fieldApiName]: this.name };
    const recordInput = { apiName: ACCOUNT_OBJECT.objectApiName, fields };

    try {
      const account = await createRecord(recordInput);
    } catch (error) {
      // Handle error
    }
  }
}
```

---

# `deleteRecord(recordId)`

Deletes a record.

## Syntax

```js
import { deleteRecord } from 'lightning/uiRecordApi';
deleteRecord(recordId: string): Promise<void>;
```

## Parameters

- **`recordId`** (String, Required) – The ID of the record to delete.

## Returns

A `Promise<void>` that resolves when the record is deleted.

## Usage

`deleteRecord` accepts a single record ID. To delete multiple records, use `Promise.all()` or Apex.

```js
import { LightningElement, wire } from 'lwc';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { refreshApex } from '@salesforce/apex';
import { deleteRecord } from 'lightning/uiRecordApi';
import getAccountList from '@salesforce/apex/AccountController.getAccountList';
import { reduceErrors } from 'c/ldsUtils';

export default class LdsDeleteRecord extends LightningElement {
  accounts;
  error;
  wiredAccountsResult;

  @wire(getAccountList)
  wiredAccounts(result) {
    this.wiredAccountsResult = result;
    if (result.data) {
      this.accounts = result.data;
      this.error = undefined;
    } else if (result.error) {
      this.error = result.error;
      this.accounts = undefined;
    }
  }

  async deleteAccount(event) {
    const recordId = event.target.dataset.recordid;

    try {
      await deleteRecord(recordId);
      this.dispatchEvent(
        new ShowToastEvent({
          title: 'Success',
          message: 'Account deleted',
          variant: 'success',
        }),
      );
      await refreshApex(this.wiredAccountsResult);
    } catch (error) {
      this.dispatchEvent(
        new ShowToastEvent({
          title: 'Error deleting record',
          message: reduceErrors(error).join(', '),
          variant: 'error',
        }),
      );
    }
  }
}
```

### Notes

- If a component is subscribed to the deleted record via a wire, it will receive a 404 error after deletion.
- Avoid calling `deleteRecord` from a record page for a record you want to delete, as it will result in a 404 error stating "The requested resource does not exist".

---

# `getRecord`

Use this wire adapter to retrieve a record’s data.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getRecord } from 'lightning/uiRecordApi';

@wire(getRecord, { recordId: string, fields: string|string[], optionalFields?: string|string[] })
propertyOrFunction;

@wire(getRecord, { recordId: string, layoutTypes: string|string[],
                    modes?: string|string[], optionalFields?: string|string[] })
propertyOrFunction;
```

## Parameters

- **`recordId`** (String, Required) – ID of a record from a supported object.
- **`fields`** (String[]) – Either `fields` or `layoutTypes` is required. A field or an array of fields to return. If a field is inaccessible, an error is returned. Use `optionalFields` if unsure about access.
- **`layoutTypes`** (String[]) – Either `fields` or `layoutTypes` is required. Specifies the fields to return. Options:
  - **`Compact`** – Retrieves a record’s key fields.
  - **`Full`** – Retrieves a full layout.
- **`modes`** (String[]) – Optional if `layoutTypes` is specified. Determines which fields to get from a layout. Options:
  - **`Create`** – For UI that lets a user create a record.
  - **`Edit`** – For UI that lets a user edit a record.
  - **`View`** – (Default) For UI that displays a record.
- **`optionalFields`** (String[]) – Optional fields. If accessible, they’re included; if not, they are ignored without error.

## Returns

- **`data`** – Record response.
- **`error`** – FetchResponse.

## Usage

This example retrieves a record and its field values:

```js
import { LightningElement, wire } from 'lwc';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import NAME_FIELD from '@salesforce/schema/Account.Name';
import OWNER_NAME_FIELD from '@salesforce/schema/Account.Owner.Name';
import PHONE_FIELD from '@salesforce/schema/Account.Phone';
import INDUSTRY_FIELD from '@salesforce/schema/Account.Industry';

export default class Example extends LightningElement {
  @wire(getRecord, {
    recordId: '001456789012345678',
    fields: [NAME_FIELD, INDUSTRY_FIELD],
    optionalFields: [PHONE_FIELD, OWNER_NAME_FIELD],
  })
  account;

  get name() {
    return getFieldValue(this.account.data, NAME_FIELD);
  }

  get phone() {
    return getFieldValue(this.account.data, PHONE_FIELD);
  }

  get industry() {
    return getFieldValue(this.account.data, INDUSTRY_FIELD);
  }

  get owner() {
    return getFieldValue(this.account.data, OWNER_NAME_FIELD);
  }
}
```

### Error Handling

Use a Promise with `then()` and `catch()` blocks. To display errors, use toasts from `lightning/platformShowToastEvent`.

```js
import { LightningElement, api, wire } from 'lwc';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { getRecord } from 'lightning/uiRecordApi';

const FIELDS = ['Contact.Name', 'Contact.Phone'];

export default class LoadContact extends LightningElement {
  @api recordId;
  contact;
  name;
  phone;
  @wire(getRecord, { recordId: '$recordId', fields: FIELDS })
  wiredRecord({ error, data }) {
    if (error) {
      let message = 'Unknown error';
      if (Array.isArray(error.body)) {
        message = error.body.map((e) => e.message).join(', ');
      } else if (typeof error.body.message === 'string') {
        message = error.body.message;
      }
      this.dispatchEvent(
        new ShowToastEvent({
          title: 'Error loading contact',
          message,
          variant: 'error',
        }),
      );
    } else if (data) {
      this.contact = data;
      this.name = this.contact.fields.Name.value;
      this.phone = this.contact.fields.Phone.value;
    }
  }
}
```

---

# `getRecords`

Use this wire adapter to retrieve data for multiple records across different objects or record types.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getRecords } from 'lightning/uiRecordApi';

@wire(getRecords, { records: [ { recordIds: string[], fields: string[] } ] })
propertyOrFunction;

@wire(getRecords, { records: [ { recordIds: string[], fields: string[], optionalFields?: string[] } ] })
propertyOrFunction;
```

## Parameters

- **`records`** (Object[], Required) – Array of record requests, which can span multiple objects or record types.

### `records` Properties

- **`recordIds`** (String[], Required) – Record IDs from supported objects.
- **`fields`** (String[]) – Fields to return. If a field is inaccessible, an error occurs. Use `optionalFields` if unsure about access.
- **`optionalFields`** (String[]) – Additional fields to return. Inaccessible fields are ignored without causing an error.

## Returns

- **`data`** – Batch Results.
- **`error`** – FetchResponse.

## Usage

For a single record, use `getRecord`.

### Example: Fetching Multiple Records

```js
import { LightningElement, wire } from 'lwc';
import { getRecords } from 'lightning/uiRecordApi';
import NAME_FIELD from '@salesforce/schema/User.Name';
import EMAIL_FIELD from '@salesforce/schema/User.Email';

export default class GetRecordsExample extends LightningElement {
  @wire(getRecords, {
    records: [
      {
        recordIds: ['005XXXXXXXXXXXXXXX'],
        fields: [NAME_FIELD],
        optionalFields: [EMAIL_FIELD],
      },
    ],
  })
  wiredRecords;
}
```

### Example: Fetching Records Across Multiple Objects

```js
import { LightningElement, wire } from 'lwc';
import { getRecords } from 'lightning/uiRecordApi';
import USER_NAME_FIELD from '@salesforce/schema/User.Name';
import ACCOUNT_NAME_FIELD from '@salesforce/schema/Account.Name';

export default class GetRecordsExample extends LightningElement {
  @wire(getRecords, {
    records: [
      { recordIds: ['005XXXXXXXXXXXXXXX'], fields: [USER_NAME_FIELD] },
      { recordIds: ['001XXXXXXXXXXXXXXX'], fields: [ACCOUNT_NAME_FIELD] },
    ],
  })
  wiredRecords;
}
```

### Error Handling

Errors are included in the `error` property. To identify subrequest errors, check `data.results[].result`.

```json
{
  "results": [
    {
      "statusCode": 200,
      "result": {
        "apiName": "Contact",
        "fields": {
          "Name": { "value": "Sean Forbes" },
          "Email": { "value": "sean@edge.com" }
        }
      }
    },
    {
      "statusCode": 400,
      "result": [
        {
          "errorCode": "UNKNOWN_EXCEPTION",
          "message": "Record ID is malformed"
        }
      ]
    }
  ]
}
```

### Example: Handling Errors in LWC

```js
import { LightningElement, api, wire } from 'lwc';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { getRecords } from 'lightning/uiRecordApi';

const FIELDS = ['Contact.Name', 'Contact.Phone'];

export default class LoadContact extends LightningElement {
  @api recordId;
  contacts;
  name;
  phone;
  @wire(getRecords, {
    records: [{ recordIds: ['005XXXXXXXXXXXXXXX'], fields: FIELDS }],
  })
  wiredRecord({ error, data }) {
    if (error) {
      let message = error.body.message || 'Unknown error';
      this.dispatchEvent(
        new ShowToastEvent({
          title: 'Error loading contacts',
          message,
          variant: 'error',
        }),
      );
    } else if (data) {
      this.contacts = data;
      this.name = this.contacts.results[0].result.fields.Name.value;
      this.phone = this.contacts.results[0].result.fields.Phone.value;
    }
  }
}
```

---

# `updateRecord(recordInput, clientOptions)`

Updates a record. Provide the record ID in `recordInput`.

## Syntax

```js
import { updateRecord } from 'lightning/uiRecordApi';
updateRecord(recordInput: Record, clientOptions?: Object): Promise<Record>;
```

## Parameters

- **`recordInput`** (Object, Required) – A RecordInput object used to update the record.
- **`clientOptions`** (Object, Optional) – To check for conflicts before updating, pass `{'ifUnmodifiedSince' : lastModifiedDate}` using the `LastModifiedDate` value.

### `recordInput` Properties

- **`fields`** (Object, Required) – Map of field names to field values.
- **`apiName`** (String) – Use `null` or omit this property when updating a record.
- **`triggerOtherEmail`** (Boolean) – For cases, specifies whether to send email to external users. Default: `false`.
- **`triggerUserEmail`** (Boolean) – For cases or leads, specifies whether to send internal user email notifications. Default: `false`.
- **`useDefaultRule`** (Boolean) – For cases or leads, specifies whether to use default assignment rules. Default: `false`.
- **`allowSaveOnDuplicate`** (Boolean) – Specifies whether to save a duplicate record. Default: `false`.

## Returns

A Promise that resolves with the updated record containing field data.

## Usage

```js
import { LightningElement, wire } from 'lwc';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { updateRecord } from 'lightning/uiRecordApi';
import { refreshApex } from '@salesforce/apex';
import getSingleContact from '@salesforce/apex/ContactController.getSingleContact';
import FIRSTNAME_FIELD from '@salesforce/schema/Contact.FirstName';
import LASTNAME_FIELD from '@salesforce/schema/Contact.LastName';
import ID_FIELD from '@salesforce/schema/Contact.Id';

export default class UpdateRecordExample extends LightningElement {
  @wire(getSingleContact) contact;
  contactId;

  updateContact() {
    const fields = {
      [ID_FIELD.fieldApiName]: this.contactId,
      [FIRSTNAME_FIELD.fieldApiName]: this.template.querySelector("[data-field='FirstName']").value,
      [LASTNAME_FIELD.fieldApiName]: this.template.querySelector("[data-field='LastName']").value,
    };

    updateRecord({ fields })
      .then(() => {
        this.dispatchEvent(
          new ShowToastEvent({
            title: 'Success',
            message: 'Contact updated',
            variant: 'success',
          }),
        );
        return refreshApex(this.contact);
      })
      .catch((error) => {
        this.dispatchEvent(
          new ShowToastEvent({
            title: 'Error updating record',
            message: error.body.message,
            variant: 'error',
          }),
        );
      });
  }
}
```

---

# `createListInfo`

Creates a list view for a supported object.

## Syntax

```js
import { createListInfo } from 'lightning/uiListsApi';

createListInfo({ objectApiName: 'Account', listViewApiName: 'MyAccountListView' });
```

## Parameters

- **`objectApiName`** (String, Required) – API name of a supported object.
- **`listViewApiName`** (String, Required) – API name of a list view (e.g., `"AllAccounts"`).
- **`displayColumns`** (String[]) – Field API names displayed in the list.
- **`filterLogicString`** (String) – Filter logic (e.g., `"(1 OR 2) and 3"`).
- **`filteredByInfo`** (Object) – Filtering details
- **`label`** (String) – Display label for the list.
- **`listShares`** (String[]) – Objects shared with if `visibility = "Shared"`.
- **`scope`** (Object) – Scope details
- **`visibility`** (String) – One of `"Private"`, `"Public"`, or `"Shared"`.

## Returns

- **`data`** – List Info
- **`error`** – FetchResponse.

## Usage

Creates a list view when the button is clicked.

### JavaScript

```js
import { createListInfo } from 'lightning/uiListsApi';
import { LightningElement } from 'lwc';

export default class CreateListInfo extends LightningElement {
  error;
  displayColumns;

  async createListView() {
    createListInfo({
      objectApiName: 'Account',
      listViewApiName: 'AllAccounts',
    })
      .then(({ data }) => (this.displayColumns = data.displayColumns))
      .catch(({ body }) => (this.error = body.message));
  }
}
```

---

# `deleteListInfo`

Use this function to delete a list view.

## Syntax

```js
import { deleteListInfo } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

deleteListInfo({ objectApiName: ACCOUNT_OBJECT, listViewApiName: 'MyAccountListView' });
```

## Parameters

- **`objectApiName`** (String, Required) - The API name of a supported object.
- **`listViewApiName`** (String, Required) - The API name of a list view, such as `"AllAccounts"`.

## Returns

If a list view is deleted successfully, there is no response.  
In case of an error, it returns:

- **`error`** – FetchResponse

## Usage

This example deletes a list view when the button is clicked.

### **JavaScript**

```js
import { deleteListInfo } from 'lightning/uiListsApi';
import { LightningElement, api } from 'lwc';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class DeleteListInfo extends LightningElement {
  errorMessage;
  deleted;

  @api async deleteListView() {
    deleteListInfo({
      objectApiName: ACCOUNT_OBJECT.objectApiName,
      listViewApiName: 'AllAccounts_deleteListInfoTest',
    })
      .then(() => {
        this.deleted = true;
        this.errorMessage = undefined;
      })
      .catch((error) => {
        this.errorMessage = error.body.message;
        this.deleted = undefined;
      });
  }
}
```

---

# `getListInfoByName`

Use this wire adapter to get the metadata for a list view.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getListInfoByName } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class Example extends LightningElement {
  @wire(getListInfoByName, {
    objectApiName: ACCOUNT_OBJECT,
    listViewApiName: 'AllAccounts',
  })
  propertyOrFunction;
}
```

## Parameters

- **`objectApiName`** (String, Required) - The API name of a supported object.
- **`listViewApiName`** (String, Required) - The API name of a list view, such as `"AllAccounts"`.

## Returns

- **`data`** – List Info
- **`error`** – FetchResponse

## Usage

This example fetches the List Info by API name, then iterates through the list of display columns in the List Info.

### **JavaScript**

```js
import { LightningElement, wire } from 'lwc';
import { getListInfoByName } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class WireListInfoByName extends LightningElement {
  error;
  displayColumns;

  @wire(getListInfoByName, {
    objectApiName: ACCOUNT_OBJECT.objectApiName,
    listViewApiName: 'AllAccounts',
  })
  listInfo({ error, data }) {
    if (data) {
      this.displayColumns = data.displayColumns;
      this.error = undefined;
    } else if (error) {
      this.error = error;
      this.displayColumns = undefined;
    }
  }
}
```

---

# `getListInfosByName`

Use this wire adapter to get the metadata for a batch of list views.

## Syntax

```js
import { getListInfosByName } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class KeywordResults extends LightningElement {
  @wire(getListInfosByName, {
    names: ['Account.AllAccounts'],
  })
  getListInfosByNameWire({ data }) {
    if (data && data.results) {
      this.listInfos = data.results.map(({ result }) => result);
    }
  }
}
```

## Parameters

- **`names`** (String[], Required) - An array of comma-separated strings of list view names. A list view name starts with an entity name, a dot, and then the name of the list view, like `"Account.AllAccounts"`.

## Returns

- A **`results`** object with Simplified Batch Results and status codes.
- **`error`** – FetchResponse

## Usage

This example fetches the list information by API name, then iterates through the list of display columns in the list information.

### **JavaScript**

```js
import { LightningElement, wire } from 'lwc';
import { getListInfosByName } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class WireListInfosByName extends LightningElement {
  listInfos;

  @wire(getListInfosByName, {
    names: ['${ACCOUNT_OBJECT.objectApiName}.AllAccounts'],
  })
  listInfo({ error, data }) {
    if (data) {
      this.listInfos = data.results.map(({ result }) => result);
    }
  }
}
```

---

# `getListInfosByObjectName`

Use this wire to get the list views associated with a supported object.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getListInfosByObjectName } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class Example extends LightningElement {
  @wire(getListInfosByObjectName, {
    objectApiName: ACCOUNT_OBJECT,
    pageSize: 10,
    recentListsOnly: true,
  })
  propertyOrFunction;
}
```

## Parameters

- **`objectApiName`** (String, Required) - The API name of a supported object.
- **`pageSize`** (Number) - The number of list records viewed at one time. The default value is `20`. Valid values are `1–2000`.
- **`pageToken`** (Number) - A token that represents the page offset. To indicate where the page starts, use this value with the `pageSize` parameter. The maximum offset is `2000`, and the default is `0`.
- **`q`** (String) - A search term to filter the results. Wildcards are supported.
- **`recentListsOnly`** (Boolean) - Indicates whether to get recent lists only (`true`) or not (`false`). The default is `false`.

## Returns

- **`data`** – List Info Summary Collection
- **`error`** – FetchResponse

## Usage

This example fetches the list of list views for an object and displays the list view labels.

### **JavaScript**

```js
import { LightningElement, wire } from 'lwc';
import { getListInfosByObjectName } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class GetListOfLists extends LightningElement {
  error;
  lists;

  @wire(getListInfosByObjectName, {
    objectApiName: ACCOUNT_OBJECT.objectApiName,
    pageSize: 10,
  })
  listOfLists({ error, data }) {
    if (data) {
      this.lists = data.lists;
      this.error = undefined;
    } else if (error) {
      this.error = error;
      this.lists = undefined;
    }
  }
}
```

---

# `getListObjectInfo`

This wire adapter gets the metadata for a list view object.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getListObjectInfo } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class Example extends LightningElement {
  @wire(getListObjectInfo, { objectApiName: ACCOUNT_OBJECT })
  propertyOrFunction;
}
```

## Parameters

- **`objectApiName`** (String, Required) - The API name of a supported object.

## Returns

- **`data`** – List Object Info
- **`error`** – FetchResponse

## Usage

This example fetches the list object info for an object and then displays the list of columns for the object.

### **JavaScript**

```js
import { LightningElement, wire } from 'lwc';
import { getListObjectInfo } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class WireListInfoByName extends LightningElement {
  error;
  columns;

  @wire(getListObjectInfo, {
    objectApiName: ACCOUNT_OBJECT.objectApiName,
  })
  listObjectInfo({ error, data }) {
    if (data) {
      this.columns = data.columns;
      this.error = undefined;
    } else if (error) {
      this.error = error;
      this.columns = undefined;
    }
  }
}
```

---

# `getListPreferences`

Use this wire adapter to get the preferences for a list view.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getListPreferences } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class Example extends LightningElement {
  @wire(getListPreferences, {
    objectApiName: ACCOUNT_OBJECT,
    listViewApiName: 'AllAccounts',
  })
  propertyOrFunction;
}
```

## Parameters

- **`objectApiName`** (String, Required) - The API name of a supported object.
- **`listViewApiName`** (String, Required) - The API name of a list view, such as `"AllAccounts"`.

## Returns

- **`data`** – List Preferences
- **`error`** – FetchResponse

## Usage

This example fetches the preferences for a list view and displays the column widths for each displayed column.

### **JavaScript**

```js
import { LightningElement, wire } from 'lwc';
import { getListPreferences } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class GetListPrefs extends LightningElement {
  error;
  columnWidths;

  @wire(getListPreferences, {
    objectApiName: ACCOUNT_OBJECT.objectApiName,
    listViewApiName: 'AllAccounts',
  })
  listPrefs({ error, data }) {
    if (data) {
      this.columnWidths = Object.entries(data.columnWidths);
      this.error = undefined;
    } else if (error) {
      this.error = error;
      this.columnWidths = undefined;
    }
  }
}
```

---

# `getListRecordsByName`

Use this wire adapter to get record data for a list view.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getListRecordsByName } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class Example extends LightningElement {
  @wire(getListRecordsByName, {
    objectApiName: ACCOUNT_OBJECT,
    listViewApiName: 'AllAccounts',
    fields: ['Account.Name', 'Account.Id'],
    sortBy: ['Account.Name'],
  })
  propertyOrFunction;
}
```

## Parameters

- **`objectApiName`** (String, Required) - The API name of a supported object.
- **`listViewApiName`** (String, Required) - The API name of a list view, such as `"AllAccounts"`.
- **`fields`** (String[]) - Additional fields queried for the records returned. These fields don’t create visible columns. If the field isn’t available to the user, an error occurs.
- **`optionalFields`** (String[]) - Additional fields queried for the records returned. These fields don’t create visible columns. If the field isn’t available to the user, no error occurs, and the field isn’t included in the records.
- **`pageSize`** (Integer) - The number of list records viewed at one time. The default value is `50`. Valid values are `1–2000`.
- **`searchTerm`** (String) - A search term to filter the results. Wildcards are supported.
- **`sortBy`** (String) - The API name of the field the list view is sorted by. Preceding with `-` sorts in descending order (e.g., `"-CreatedDate"`).
- **`where`** (String) - The filter applied to returned records using GraphQL syntax.
- **`pageToken`** (Integer) - A token that represents the page offset. Use with `pageSize` to control pagination.

## Returns

- **`data`** – List Record Collection
- **`error`** – FetchResponse

## Usage

This example fetches list view records by API name and iterates through the records. The `handleNextPage` click handler retrieves the next set of records.

### **JavaScript**

```js
import { LightningElement, wire } from 'lwc';
import { getListRecordsByName } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class GetListRecords extends LightningElement {
  error;
  records;
  pageToken;
  nextPageToken;

  @wire(getListRecordsByName, {
    objectApiName: ACCOUNT_OBJECT.objectApiName,
    listViewApiName: 'AllAccounts',
    fields: ['Account.Id', 'Account.Name'],
    sortBy: ['Account.Name'],
    pageSize: 10,
    pageToken: '$pageToken',
  })
  listRecords({ error, data }) {
    if (data) {
      this.records = data.records;
      this.nextPageToken = data?.nextPageToken;
      this.error = undefined;
    } else if (error) {
      this.error = error;
    }
  }

  handleNextPage(event) {
    event.stopPropagation();
    if (this.nextPageToken) {
      this.pageToken = this.nextPageToken;
    }
  }
}
```

For backward pagination, use the `previousPageToken` property returned by `getListRecordsByName`.

---

# `updateListInfoByName`

Use this function to update a list view’s metadata.

## Syntax

```js
import { updateListInfoByName } from 'lightning/uiListsApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

updateListInfoByName({
  objectApiName: ACCOUNT_OBJECT,
  listViewApiName: 'MyAccountListView',
  label: 'NewListViewLabel',
});
```

## Parameters

- **`objectApiName`** (String, Required) - The API name of a supported object.
- **`listViewApiName`** (String, Required) - The API name of a list view, such as `"AllAccounts"`.
- **`displayColumns`** (String[]) - The display columns (field API names) for the list.
- **`filterLogicString`** (String) - The filter logic string, such as `"(1 OR 2) and 3"`. Indexes start with 1.
- **`filteredByInfo`** (Object) - Filtering information for the list. See List Filter By Info Input.
- **`label`** (String) - The list’s display label. For example, `"All Accounts"`.
- **`listShares`** (String[]) - Objects the list is shared with, if `visibility` is set to `Shared`.
- **`scope`** (Object) - The scope information for the list. See List Scope Input.
- **`visibility`** (String) - The list’s visibility. Valid values are: `"Private"`, `"Public"`, `"Shared"`.

## Returns

- **`data`** – List Info
- **`error`** – FetchResponse

## Usage

This example updates the list view’s label when the button is clicked.

### **JavaScript**

```js
import { updateListInfoByName } from 'lightning/uiListsApi';
import { LightningElement, api } from 'lwc';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class UpdateListInfo extends LightningElement {
  error;
  label;

  @api async updateListView() {
    updateListInfoByName({
      objectApiName: ACCOUNT_OBJECT.objectApiName,
      listViewApiName: 'AllAccounts',
      label: 'New Label',
    })
      .then((result) => {
        this.label = result.data.label;
      })
      .catch((error) => {
        this.error = error;
      });
  }
}
```

---

# `updateListPreferences`

Use this function to update the preferences for a list view.

## Syntax

```js
import { updateListPreferences } from "lightning/uiListsApi";
import ACCOUNT_OBJECT from "@salesforce/schema/Account";

export default class UpdateListPrefExample extends LightningElement {
  updateListPreferences({
    objectApiName: ACCOUNT_OBJECT,
    listViewApiName: "AllAccounts",
  });
}
```

## Parameters

- **`objectApiName`** (String, Required) - The API name of a supported object.
- **`listViewApiName`** (String, Required) - The API name of a list view, such as `"AllAccounts"`.
- **`columnWidths`** (Object) - The column-width preferences for the list. Pass in a key-value pair with the name of the column and an integer.
- **`columnWrap`** (Object) - The column-wrapping preferences for the list. Pass in a key-value pair with the name of the column and a boolean.
- **`listReference`** (Object) - The reference information for the list.
- **`orderedBy`** (String[]) - The ordering preference for the list. See List Order Input.

## Returns

- **`data`** – List Info
- **`error`** – FetchResponse

## Usage

This example updates a list view’s preferences and displays the updated values.

### **JavaScript**

```js
import { updateListPreferences } from 'lightning/uiListsApi';
import { LightningElement, api } from 'lwc';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class UpdateListPrefs extends LightningElement {
  error;
  columnWidths;

  @api async updateListViewPrefs() {
    updateListPreferences({
      objectApiName: ACCOUNT_OBJECT.objectApiName,
      listViewApiName: 'AllAccounts',
      columnWidths: {
        Type: 200,
        'Owner.Alias': 200,
        Phone: 200,
        BillingState: 250,
        Name: 250,
      },
    })
      .then((result) => {
        this.columnWidths = Object.entries(result.data.columnWidths);
      })
      .catch((error) => {
        this.error = error;
      });
  }
}
```

---

# `getRelatedListCount`

Use this wire adapter to get the `RelatedList` record count.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getRelatedListCount } from 'lightning/uiRelatedListApi';

export default class LdsGetRelatedListCount extends LightningElement {
  @wire(getRelatedListCount, {
      parentRecordId: '<PARENT_RECORD_ID_PLACEHOLDER>',
      relatedListId: 'Contacts',
  })
}
```

## Parameters

- **`parentRecordId`** (String, Required) – The ID of the parent record, such as an Account ID.
- **`relatedListId`** (String, Required) – The API name of a related list object, such as Contacts, Opportunities, or Cases.
- **`maxCount`** (Number) – The maximum number of records to return. Default is 20.

## Returns

- **`data`** – Related List Record Count.
- **`error`** – FetchResponse.

## Usage

This example fetches the record count for a related list.

### **JavaScript**

```js
import { LightningElement, wire } from 'lwc';
import { getRelatedListCount } from 'lightning/uiRelatedListApi';

export default class WireGetRelatedListCount extends LightningElement {
  error;
  responseData;

  @wire(getRelatedListCount, {
    parentRecordId: '<PARENT_RECORD_ID_PLACEHOLDER>',
    relatedListId: 'Contacts',
  })
  listInfo({ error, data }) {
    if (data) {
      this.responseData = data;
      this.error = undefined;
    } else if (error) {
      this.error = error;
      this.responseData = undefined;
    }
  }
}
```

---

# `getRelatedListInfo`

Use this wire adapter to get metadata for `RelatedList`.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getRelatedListInfo } from 'lightning/uiRelatedListApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class LdsGetRelatedListInfo extends LightningElement {
  @wire(getRelatedListInfo, {
      parentObjectApiName: ACCOUNT_OBJECT.objectApiName,
      relatedListId: 'Contacts',
      recordTypeId: '012000000000000AAA', // optional
      fields: ['Contact.Name', 'Contact.Id'], // optional
      optionalFields: ['Contact.OptionalField'], // optional
      restrictColumnsToLayout: false // optional
  })
}
```

## Parameters

- **`parentObjectApiName`** (String, Required) – API name of a parent object, such as `Account`.
- **`relatedListId`** (String, Required) – API name of a related list object, such as `Contacts`, `Opportunities`, or `Cases`.
- **`recordTypeId`** (String) – ID of the parent record type. If not provided, the default record type is used.
- **`fields`** (String[]) – API names of related list fields to query. If a field is inaccessible, an error is returned.
- **`optionalFields`** (String[]) – Additional fields to query. Inaccessible fields are ignored but do not cause an error.
- **`restrictColumnsToLayout`** (Boolean) – If `true`, retrieves only list columns in the page layout; if `false`, retrieves all columns. Default is `true`.

## Returns

- **`data`** – Related List Info.
- **`error`** – FetchResponse.

---

# `getRelatedListInfoBatch`

Use this wire adapter to get metadata for a batch of `RelatedLists`.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getRelatedListInfoBatch } from 'lightning/uiRelatedListApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class LdsGetRelatedListInfoBatch extends LightningElement {
  @wire(getRelatedListInfoBatch, {
    parentObjectApiName: ACCOUNT_OBJECT.objectApiName,
    relatedListNames: ['Contacts', 'Opportunities'],
  })
}
```

## Parameters

- **`parentObjectApiName`** (String, Required) – API name of a parent object, such as `Account`.
- **`relatedListNames`** (String[], Required) – Array of related list API names, such as `Contacts`, `Opportunities`, or `Cases`. In the wire adapter code, `relatedListNames` maps to `relatedListIds` in the User Interface API resource.
- **`recordTypeId`** (String) – ID of the parent record type. If not provided, the default record type is used.

## Returns

- **`data`** – Simplified Batch Results.
- **`error`** – FetchResponse.

---

# `getRelatedListRecords`

Use this wire adapter to get `RelatedList` records. Related lists display details and links to records associated with a specific record, such as contacts, cases, notes, or files related to an account.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getRelatedListRecords } from 'lightning/uiRelatedListApi';

export default class LdsGetRelatedListRecords extends LightningElement {
  @wire(getRelatedListRecords, {
    parentRecordId: '<PARENT_RECORD_ID_PLACEHOLDER>',
    relatedListId: 'Contacts',
    fields: ['Contact.Name','Contact.Id'],
    sortBy: ['Contact.Name']
  })
}
```

## Parameters

- **`parentRecordId`** (String, Required) – ID of the parent record, such as an Account ID.
- **`relatedListId`** (String, Required) – API name of a related list or child relationship (e.g., `Contacts`, `Opportunities`, `Cases`). For custom objects, use `Custom_Objects__r`.
- **`fields`** (String[]) – API names of the related list’s column fields. For standard fields on custom objects, use `Custom_Object__c.FieldName`; for custom fields, use `Custom_Object__c.FieldName__c`.
- **`optionalFields`** (String[]) – Additional fields in the related list.
- **`pageSize`** (Number) – Number of records per page (default: 50, range: 1-1999).
- **`sortBy`** (String[]) – API name of the field to sort by. Accepts one value per request.
- **`where`** (String) – Filter for related list records. Semi-joins and anti-joins are not supported.

## Returns

- **`data`** – Related List Record Collection.
- **`error`** – FetchResponse.

---

# `getRelatedListRecordsBatch`

Use this wire adapter to get records for a batch of `RelatedLists`.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getRelatedListRecordsBatch } from 'lightning/uiRelatedListApi';

export default class LdsGetRelatedListRecordsBatch extends LightningElement {
  @wire(getRelatedListRecordsBatch, {
    parentRecordId: '<PARENT_RECORD_ID_PLACEHOLDER>',
    relatedListParameters: [
      {
        relatedListId: 'Contacts',
        fields: ['Contact.Name', 'Contact.Id'],
        sortBy: ['Contact.Name']
      },
      {
        relatedListId: 'Opportunities',
        fields: ['Opportunity.Name', 'Opportunity.Amount'],
        sortBy: ['Opportunity.Amount'],
        where: "{ and: [{ Name: { like: \"ACME%\" }}] }"
      }
    ]
  })
}
```

## Parameters

- **`parentRecordId`** (String, Required) – ID of the parent record, such as an Account ID.
- **`relatedListParameters`** (Object[], Required) – Array of related list parameter collections.

### **`relatedListParameters` Properties**

- **`relatedListId`** (String, Required) – API name of a related list object, such as `Contacts`, `Opportunities`, or `Cases`.
- **`fields`** (String[]) – API names of the related list’s column fields.
- **`optionalFields`** (String[]) – Additional fields in the related list.
- **`pageSize`** (Number) – Number of list records to return per page.
- **`sortBy`** (String[]) – Field API name(s) to sort by. Accepts one value per request.
- **`where`** (String) – Filter for related list records in GraphQL syntax.

## Returns

- **`data`** – Simplified Batch Results.
- **`error`** – FetchResponse.

---

# `getRelatedListsInfo`

Use this wire adapter to get metadata for `RelatedLists` in an object’s default layout.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getRelatedListsInfo } from 'lightning/uiRelatedListApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class LdsGetRelatedListsInfo extends LightningElement {
  @wire(getRelatedListsInfo, {
    parentObjectApiName: ACCOUNT_OBJECT.objectApiName,
    recordTypeId: '012000000000000AAA' // optional
  })
}
```

## Parameters

- **`parentObjectApiName`** (String, Required) – API name of a parent object, such as `Account`.
- **`recordTypeId`** (String) – ID of the parent record type.

## Returns

- **`data`** – Related List Summary Collection.
- **`error`** – FetchResponse.

---

# `getObjectInfo`

Use this wire adapter to get metadata about a specific object, including its fields, child relationships, record types, and theme.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getObjectInfo } from 'lightning/uiObjectInfoApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class Example extends LightningElement {
  @wire(getObjectInfo, { objectApiName: ACCOUNT_OBJECT })
  propertyOrFunction;
}
```

## Parameters

- **`objectApiName`** (String, Required) – API name of a supported object.

## Returns

- **`data`** – Object Info.
- **`error`** – FetchResponse.

## Usage

Use `getObjectInfo` for a single object. For multiple objects, use `getObjectInfos`.

This example retrieves record type IDs and finds the ID for the record type named "Special Account":

```js
import { LightningElement, api, wire, track } from 'lwc';
import { getObjectInfo } from 'lightning/uiObjectInfoApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class RecordFormWithRecordType extends LightningElement {
  @api recordId;
  @api objectApiName;
  @track objectInfo;

  @wire(getObjectInfo, { objectApiName: ACCOUNT_OBJECT })
  objectInfo;

  get recordTypeId() {
    const rtis = this.objectInfo.data.recordTypeInfos;
    return Object.keys(rtis).find((rti) => rtis[rti].name === 'Special Account');
  }
}
```

---

# `getObjectInfos`

Use this wire adapter to get metadata for multiple objects, including fields, child relationships, record types, and themes.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getObjectInfos } from 'lightning/uiObjectInfoApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';
import OPPORTUNITY_OBJECT from '@salesforce/schema/Opportunity';

export default class GetObjectInfosExample extends LightningElement {
  @wire(getObjectInfos, { objectApiNames: [ACCOUNT_OBJECT, OPPORTUNITY_OBJECT] })
  propertyOrFunction;
}
```

## Parameters

- **`objectApiNames`** (String[], Required) – API names of supported objects.

## Returns

- **`data`** – Contains a `results` object with Object Info metadata and status codes.
- **`error`** – FetchResponse.

### Response Structure

The metadata for each requested object is returned in `data.results` in the same order they were requested. If an object has an error, the error code and message are included in `data.results[].result`. The `error` object is returned only if the server call fails.

```json
{
  "results": [
    {
      "result": ObjectInfo1,
      "statusCode": 200
    },
    {
      "result": ObjectInfo2,
      "statusCode": 200
    },
    {
      "result": [
        {
          "errorCode": "FORBIDDEN",
          "message": "You don't have access to this record. Ask your administrator for help or to request access."
        }
      ],
      "statusCode": 403
    }
  ]
}
```

---

# `getPicklistValuesByRecordType`

Use this wire adapter to retrieve values for all picklists of a specified record type.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getPicklistValuesByRecordType } from 'lightning/uiObjectInfoApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';

export default class Example extends LightningElement {
  @wire(getPicklistValuesByRecordType, {
    objectApiName: ACCOUNT_OBJECT,
    recordTypeId: '012000000000000AAA',
  })
  propertyOrFunction;
}
```

## Parameters

- **`objectApiName`** (String, Required) – API name of a supported object.
- **`recordTypeId`** (String, Required) – ID of the record type. Use the Object Info `defaultRecordTypeId` property from `getObjectInfo`.

## Returns

- **`data`** – Picklist Values Collection.
- **`error`** – FetchResponse.

---

# `getPicklistValues`

Use this wire adapter to retrieve picklist values for a specified field.

## Syntax

```js
import { LightningElement, wire } from 'lwc';
import { getPicklistValues } from 'lightning/uiObjectInfoApi';
import INDUSTRY_FIELD from '@salesforce/schema/Account.Industry';

export default class Example extends LightningElement {
  @wire(getPicklistValues, { recordTypeId: '012000000000000AAA', fieldApiName: INDUSTRY_FIELD })
  propertyOrFunction;
}
```

## Parameters

- **`recordTypeId`** (String, Required) – ID of the record type. Use the Object Info `defaultRecordTypeId` property from `getObjectInfo`. If no default record type exists, the master record type is `012000000000000AAA`.
- **`fieldApiName`** (String, Required) – API name of the picklist field on a supported object.

## Returns

- **`data`** – Picklist Values.
- **`error`** – FetchResponse.

## Usage

Picklist values are scoped to a record type. For dependent picklists, `getPicklistValues` returns data for controlling fields and their mappings.

Both `recordTypeId` and `fieldApiName` are required. Use `getObjectInfo` to retrieve `defaultRecordTypeId` and pass it reactively to `getPicklistValues`.

This example retrieves the Rating field picklist values (`Hot`, `Warm`, `Cold`) from the Account object:

```js
import { LightningElement, wire } from 'lwc';
import { getObjectInfo, getPicklistValues } from 'lightning/uiObjectInfoApi';
import ACCOUNT_OBJECT from '@salesforce/schema/Account';
import RATING_FIELD from '@salesforce/schema/Account.Rating';

export default class WireGetRatingPicklist extends LightningElement {
  accountRecordTypeId;
  ratings;

  @wire(getObjectInfo, { objectApiName: ACCOUNT_OBJECT })
  results({ error, data }) {
    if (data) {
      this.accountRecordTypeId = data.defaultRecordTypeId;
      this.error = undefined;
    } else {
      this.error = error;
      this.accountRecordTypeId = undefined;
    }
  }

  @wire(getPicklistValues, { recordTypeId: '$accountRecordTypeId', fieldApiName: RATING_FIELD })
  picklistResults({ error, data }) {
    if (data) {
      this.ratings = data.values;
      this.error = undefined;
    } else {
      this.error = error;
      this.ratings = undefined;
    }
  }
}
```

### Example Response

```json
[
  { "attributes": null, "label": "Hot", "validFor": [], "value": "Hot" },
  { "attributes": null, "label": "Warm", "validFor": [], "value": "Warm" },
  { "attributes": null, "label": "Cold", "validFor": [], "value": "Cold" }
]
```
