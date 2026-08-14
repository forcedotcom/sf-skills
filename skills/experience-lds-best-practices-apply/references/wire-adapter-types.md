# LDS Wire Adapter Type Catalog

Reference for every type the LDS wire adapters return. Rendered from the LDS schema source — same formatter the `explore_lds_uiapi` MCP tool used. Grouped by category; type names match the `$ref` paths used in adapter docs (e.g., `#/types/coreTypes/Record`).

# primitives

## String

**Category:** primitives

**Description:** Text values

**Type:** `string`

## Number

**Category:** primitives

**Description:** Numeric values

**Type:** `number`

## Integer

**Category:** primitives

**Description:** Whole number values

**Type:** `integer`

## Boolean

**Category:** primitives

**Description:** True/false values

**Type:** `boolean`

## Object

**Category:** primitives

**Description:** Generic object type

**Type:** `object`

## Any

**Category:** primitives

**Description:** Any type value

**Type:** `any`

# fieldDataTypes

## address

**Category:** fieldDataTypes

**Description:** Address field type

**Type:** `string`

## base64

**Category:** fieldDataTypes

**Description:** Base64 encoded data

**Type:** `string`

## boolean

**Category:** fieldDataTypes

**Description:** Boolean field type

**Type:** `boolean`

## combobox

**Category:** fieldDataTypes

**Description:** Combobox field type

**Type:** `string`

## complexvalue

**Category:** fieldDataTypes

**Description:** Complex value type

**Type:** `object`

## currency

**Category:** fieldDataTypes

**Description:** Currency field type

**Type:** `number`

## date

**Category:** fieldDataTypes

**Description:** Date field type

**Type:** `string`

## datetime

**Category:** fieldDataTypes

**Description:** DateTime field type

**Type:** `string`

## double

**Category:** fieldDataTypes

**Description:** Double precision number

**Type:** `number`

## email

**Category:** fieldDataTypes

**Description:** Email field type

**Type:** `string`

## encryptedstring

**Category:** fieldDataTypes

**Description:** Encrypted string type

**Type:** `string`

## int

**Category:** fieldDataTypes

**Description:** Integer field type

**Type:** `integer`

## location

**Category:** fieldDataTypes

**Description:** Location/geolocation type

**Type:** `object`

## multipicklist

**Category:** fieldDataTypes

**Description:** Multi-select picklist

**Type:** `array`

## percent

**Category:** fieldDataTypes

**Description:** Percentage field type

**Type:** `number`

## phone

**Category:** fieldDataTypes

**Description:** Phone number field type

**Type:** `string`

## picklist

**Category:** fieldDataTypes

**Description:** Single-select picklist

**Type:** `string`

## reference

**Category:** fieldDataTypes

**Description:** Reference/lookup field type

**Type:** `string`

## string

**Category:** fieldDataTypes

**Description:** String field type

**Type:** `string`

## textarea

**Category:** fieldDataTypes

**Description:** Text area field type

**Type:** `string`

## time

**Category:** fieldDataTypes

**Description:** Time field type

**Type:** `string`

## url

**Category:** fieldDataTypes

**Description:** URL field type

**Type:** `string`

# coreTypes

## FieldValue

**Category:** coreTypes

**Description:** Individual field data container

**Type:** `object`

### Properties

- **displayValue**: Display-formatted value

  - Type: `string | null`

- **value**: Raw field value
  - Type: `any`

### Required Fields

- `value`

## Record

**Category:** coreTypes

**Description:** Individual record object

**Type:** `object`

### Properties

- **apiName**: API name of the record's object

  - Type: `string`

- **childRelationships**: Child relationship records (if requested)

  - Type: `object`

- **eTag**: Entity tag for caching

  - Type: `string`

- **fields**: Map of field API names to field values

  - Type: `object`
  - Map values: `#/types/coreTypes/FieldValue`

- **id**: Record ID

  - Type: `string`

- **lastModifiedById**: ID of user who last modified the record

  - Type: `string`

- **lastModifiedDate**: ISO 8601 date of last modification

  - Type: `string`
  - Format: `date-time`

- **recordTypeId**: Record type ID

  - Type: `string`

- **recordTypeInfo**: Record type information

  - One of:
    1. Reference: `#/types/recordTypes/RecordTypeInfo`
    2. Type: `null`

- **systemModstamp**: System modification timestamp

  - Type: `string`

- **weakEtag**: Weak entity tag for comparison
  - Type: `number`

### Required Fields

- `apiName`
- `fields`
- `id`

## ErrorDetail

**Category:** coreTypes

**Description:** Error information object

**Type:** `object`

### Properties

- **errorCode**: Error code (e.g., 'UNKNOWN_EXCEPTION', 'INVALID_ID_FIELD')

  - Type: `string`

- **message**: Human-readable error message
  - Type: `string`

### Required Fields

- `errorCode`
- `message`

## FetchResponse

**Category:** coreTypes

**Description:** Error response object

**Type:** `object`

### Properties

- **status**: HTTP status code (400-599 range)

  - Type: `number`
  - Minimum: 400
  - Maximum: 599

- **body**: Error details from the underlying API

  - Type: `object`

- **headers**: HTTP response headers

  - Type: `object`

- **ok**: Always false for errors

  - Type: `boolean`
  - Constant: `false`

- **statusText**: HTTP status message

  - Type: `string`

- **errorType**: Always 'fetchResponse' for fetch errors
  - Type: `string`
  - Constant: `fetchResponse`

### Required Fields

- `status`
- `body`
- `ok`
- `errorType`

# batchTypes

## BatchResult

**Category:** batchTypes

**Description:** Individual batch result

**Type:** `object`

### Properties

- **statusCode**: HTTP status code for the individual request

  - Type: `number`

- **result**: The result data or error information
  - One of:
    1. Reference: `#/types/coreTypes/Record`
    2. Reference: `#/types/objectTypes/ObjectInfo`
    3. Reference: `#/types/relatedListTypes/RelatedListRecordCollection`
    4. Type: `array`

### Required Fields

- `statusCode`
- `result`

## SimplifiedBatchResults

**Category:** batchTypes

**Description:** Simplified batch results container

**Type:** `object`

### Properties

- **results**: Array of result objects
  - Type: `array`
  - Array of: `#/types/batchTypes/BatchResult`

### Required Fields

- `results`

## RecordBatchResult

**Category:** batchTypes

**Description:** Individual result in a batch

**Type:** `object`

### Properties

- **statusCode**: HTTP status code for the individual record request

  - Type: `number`

- **result**: Either a Record object or error array
  - One of:
    1. Reference: `#/types/coreTypes/Record`
    2. Type: `array`

### Required Fields

- `statusCode`
- `result`

## RecordsBatchResults

**Category:** batchTypes

**Description:** Batch of record results

**Type:** `object`

### Properties

- **results**: Array of result objects for each record request
  - Type: `array`
  - Array of: `#/types/batchTypes/RecordBatchResult`

### Required Fields

- `results`

# requestTypes

## RecordRequest

**Category:** requestTypes

**Description:** Request for specific records

**Type:** `object`

### Properties

- **recordIds**: Record IDs from supported objects

  - Type: `array`
  - Array of: `string`

- **fields**: Fields to return

  - Type: `array`
  - Array of: `string`

- **optionalFields**: Additional fields to return
  - Type: `array`
  - Array of: `string`

### Required Fields

- `recordIds`

## RelatedListParameter

**Category:** requestTypes

**Description:** Parameter for related list requests

**Type:** `object`

### Properties

- **relatedListId**: API name of a related list object

  - Type: `string`

- **fields**: API names of the related list's column fields

  - Type: `array`
  - Array of: `string`

- **optionalFields**: Additional fields in the related list

  - Type: `array`
  - Array of: `string`

- **pageSize**: Number of list records to return per page

  - Type: `number`

- **sortBy**: Field API name(s) to sort by

  - Type: `array`
  - Array of: `string`

- **where**: Filter for related list records in GraphQL syntax
  - Type: `string`

### Required Fields

- `relatedListId`

# recordTypes

## RecordTypeInfo

**Category:** recordTypes

**Description:** Record type metadata

**Type:** `object`

### Properties

- **available**: Whether this record type is available to the context user

  - Type: `boolean`

- **defaultRecordTypeMapping**: Whether this record type mapping is the default

  - Type: `boolean`

- **master**: Whether this record type is the master record type

  - Type: `boolean`

- **name**: The record type's label name

  - Type: `string`

- **recordTypeId**: The ID of the record type
  - Type: `string`

### Required Fields

- `available`
- `defaultRecordTypeMapping`
- `master`
- `name`
- `recordTypeId`

# objectTypes

## ObjectInfo

**Category:** objectTypes

**Description:** Object metadata

**Type:** `object`

### Properties

- **apiName**: API name of the object

  - Type: `string`

- **childRelationships**: Array of child relationship information

  - Type: `array`
  - Array of: `#/types/relationshipTypes/ChildRelationship`

- **createable**: Whether the object allows record creation

  - Type: `boolean`

- **custom**: Whether the object is custom

  - Type: `boolean`

- **defaultRecordTypeId**: ID of the default record type

  - Type: `string`

- **deletable**: Whether the object allows record deletion

  - Type: `boolean`

- **dependentFields**: Map of dependent field relationships

  - Type: `object`

- **eTag**: ETag for cache validation

  - Type: `string`

- **feedEnabled**: Whether Chatter feed is enabled for the object

  - Type: `boolean`

- **fields**: Map of field metadata keyed by field API name

  - Type: `object`

- **keyPrefix**: Three-character prefix for record IDs

  - Type: `string`

- **label**: Display label for the object

  - Type: `string`

- **labelPlural**: Plural display label for the object

  - Type: `string`

- **layoutable**: Whether the object supports page layouts

  - Type: `boolean`

- **mruEnabled**: Whether the object supports most recently used lists

  - Type: `boolean`

- **nameFields**: Array of field API names that make up the name field

  - Type: `array`
  - Array of: `string`

- **queryable**: Whether the object can be queried

  - Type: `boolean`

- **recordTypeInfos**: Map of record type information keyed by record type ID

  - Type: `object`
  - Map values: `#/types/recordTypes/RecordTypeInfo`

- **searchable**: Whether the object can be searched

  - Type: `boolean`

- **searchLayoutable**: Whether the object supports search layouts

  - Type: `boolean`

- **themeInfo**: Theme information for the object

  - Reference: `#/types/uiTypes/ThemeInfo`

- **updateable**: Whether the object allows record updates
  - Type: `boolean`

### Required Fields

- `apiName`
- `createable`
- `custom`
- `deletable`
- `updateable`

# picklistTypes

## PicklistValue

**Category:** picklistTypes

**Description:** Individual picklist option

**Type:** `object`

### Properties

- **attributes**: Additional attributes for the picklist value

  - One of:
    1. Type: `object`
    2. Type: `null`

- **label**: Display label shown to users

  - Type: `string`

- **validFor**: Array of controller value indexes this value is valid for

  - Type: `array`
  - Array of: `number`

- **value**: The actual picklist value stored in the database
  - Type: `string`

### Required Fields

- `label`
- `value`
- `validFor`

## PicklistValues

**Category:** picklistTypes

**Description:** Picklist field values

**Type:** `object`

### Properties

- **controllerValues**: Map of controlling field values to their indexes

  - Type: `object`
  - Map values: `number`

- **defaultValue**: Default picklist value object, if any

  - One of:
    1. Reference: `#/types/picklistTypes/PicklistValue`
    2. Type: `null`

- **eTag**: ETag for cache validation

  - Type: `string`

- **url**: URL to retrieve this picklist field's values

  - Type: `string`

- **values**: Array of available picklist values
  - Type: `array`
  - Array of: `#/types/picklistTypes/PicklistValue`

### Required Fields

- `values`
- `eTag`
- `url`

## PicklistFieldValues

**Category:** picklistTypes

**Description:** Picklist field information

**Type:** `object`

### Properties

- **controllerValues**: Map of controlling field values to their indexes

  - Type: `object`

- **defaultValue**: Default picklist value object, if any

  - One of:
    1. Reference: `#/types/picklistTypes/PicklistValue`
    2. Type: `null`

- **eTag**: ETag for the individual picklist field

  - Type: `string`

- **url**: URL to retrieve this specific picklist field's values

  - Type: `string`

- **values**: Array of available picklist values
  - Type: `array`
  - Array of: `#/types/picklistTypes/PicklistValue`

### Required Fields

- `values`
- `eTag`
- `url`

## PicklistValuesCollection

**Category:** picklistTypes

**Description:** Collection of picklist values

**Type:** `object`

### Properties

- **eTag**: ETag for cache validation

  - Type: `string`

- **picklistFieldValues**: Map of field API names to their picklist values
  - Type: `object`
  - Map values: `#/types/picklistTypes/PicklistFieldValues`

### Required Fields

- `eTag`
- `picklistFieldValues`

# relationshipTypes

## ChildRelationship

**Category:** relationshipTypes

**Description:** Child relationship metadata

**Type:** `object`

### Properties

- **childObjectApiName**: API name of the child object

  - Type: `string`

- **fieldName**: Name of the field that creates the relationship

  - Type: `string`

- **junctionIdListNames**: List of junction ID names for many-to-many relationships

  - Type: `array`
  - Array of: `string`

- **junctionReferenceTo**: Reference information for junction objects

  - Type: `array`
  - Array of: `string`

- **relationshipName**: Name of the relationship
  - Type: `string`

### Required Fields

- `childObjectApiName`
- `fieldName`
- `relationshipName`

# relatedListTypes

## RelatedListReference

**Category:** relatedListTypes

**Description:** Reference to related list

**Type:** `object`

### Properties

- **id**: ID of the related list reference

  - Type: `string`

- **inContextOfRecordId**: ID of the parent record for the related list

  - Type: `string`

- **listViewApiName**: API name of the related list

  - Type: `string`

- **objectApiName**: API name of the supported related list object

  - Type: `string`

- **parentObjectApiName**: API name for the parent object of the related list

  - Type: `string`

- **recordTypeId**: Record type ID for the parent of the related list

  - Type: `string`

- **relatedListId**: ID of the related list

  - Type: `string`

- **type**: Type of related list
  - Type: `string`

### Required Fields

- `id`
- `listViewApiName`
- `objectApiName`
- `parentObjectApiName`
- `relatedListId`
- `type`

## RelatedListColumn

**Category:** relatedListTypes

**Description:** Column information for related lists

**Type:** `object`

### Properties

- **dataType**: Field type

  - Type: `string`
  - Allowed values: `address`, `base64`, `boolean`, `combobox`, `complexvalue`, `currency`, `date`, `datetime`, `double`, `email`, `encryptedstring`, `int`, `location`, `multipicklist`, `percent`, `phone`, `picklist`, `reference`, `string`, `textarea`, `time`, `url`

- **fieldApiName**: The API name for the field

  - Type: `string`

- **filterable**: Indicates whether this column is filterable

  - Type: `boolean`

- **label**: The label of the field

  - Type: `string`

- **lookupId**: The ID of the field if the field is a reference

  - One of:
    1. Type: `string`
    2. Type: `null`

- **picklistValues**: The picklist values for this field

  - One of:
    1. Type: `array`
    2. Type: `null`

- **quickFilterOperator**: The operator used for quick filters on this column

  - Type: `string`

- **sortable**: Indicates whether the list column is sortable
  - Type: `boolean`

### Required Fields

- `dataType`
- `fieldApiName`
- `filterable`
- `label`
- `sortable`

## RelatedListInfo

**Category:** relatedListTypes

**Description:** Related list metadata

**Type:** `object`

### Properties

- **cloneable**: Indicates whether the related list can be cloned

  - Type: `boolean`

- **createable**: Indicates whether a new related list can be created

  - Type: `boolean`

- **deletable**: Indicates whether the related list can be deleted

  - Type: `boolean`

- **displayColumns**: All display columns for this related list

  - Type: `array`
  - Array of: `#/types/relatedListTypes/RelatedListColumn`

- **eTag**: ETag for cache validation

  - Type: `string`

- **fieldApiName**: The API name of the field in the child object that links to the parent object

  - Type: `string`

- **fields**: Related list fields queried

  - Type: `array`
  - Array of: `string`

- **filterable**: Indicates whether users can apply quick filters to the related list

  - Type: `boolean`

- **filterLogicString**: The filter logic string

  - Type: `string`

- **filteredByInfo**: Filtering information for the related list

  - Type: `array`
  - Array of: `#/types/listTypes/ListFilterByInfo`

- **label**: The related list display label

  - Type: `string`

- **listReference**: A reference to the related list

  - Reference: `#/types/relatedListTypes/RelatedListReference`

- **objectApiNames**: The API names for the objects returned in the related list

  - Type: `array`
  - Array of: `string`

- **orderedByInfo**: Ordering information for the related list

  - Type: `array`
  - Array of: `#/types/listTypes/ListOrderByInfo`

- **optionalFields**: Additional related list fields queried

  - Type: `array`
  - Array of: `string`

- **restrictColumnsToLayout**: Indicates whether metadata was retrieved for only the list columns in the page layout

  - Type: `boolean`

- **updateable**: Indicates whether the related list can be updated

  - Type: `boolean`

- **url**: URL to access the related list

  - Type: `string`

- **userPreferences**: User preferences for the related list

  - Reference: `#/types/listTypes/ListUserPreference`

- **visibility**: The related list's visibility

  - Type: `string`

- **visibilityEditable**: Indicates whether the visibility of the related list can be edited
  - Type: `boolean`

### Required Fields

- `cloneable`
- `createable`
- `deletable`
- `displayColumns`
- `fieldApiName`
- `filterable`
- `label`
- `listReference`
- `updateable`
- `visibility`
- `visibilityEditable`

## RelatedListInfoBatch

**Category:** relatedListTypes

**Description:** Batch of related list metadata

**Type:** `object`

### Properties

- **results**: Array of RelatedListInfo objects for each requested related list
  - Type: `array`
  - Array of: `#/types/relatedListTypes/RelatedListInfo`

### Required Fields

- `results`

## RelatedListCount

**Category:** relatedListTypes

**Description:** Related list count information

**Type:** `object`

### Properties

- **count**: The number of records in the related list

  - Type: `number`

- **hasMore**: Indicates whether there are more records than the provided count

  - Type: `boolean`

- **listReference**: Reference information for the related list
  - Reference: `#/types/relatedListTypes/RelatedListReference`

### Required Fields

- `count`
- `hasMore`
- `listReference`

## RelatedListRecordCollection

**Category:** relatedListTypes

**Description:** Collection of related list records

**Type:** `object`

### Properties

- **count**: Total number of records available in the related list

  - Type: `number`

- **currentPageToken**: Token representing the current page offset

  - Type: `string`

- **currentPageUrl**: URL for the current page of results

  - Type: `string`

- **fields**: List of fields requested when these records were fetched

  - Type: `array`
  - Array of: `string`

- **listInfoETag**: ETag for the related list information

  - Type: `string`

- **listReference**: Reference information for the related list

  - Reference: `#/types/relatedListTypes/RelatedListReference`

- **nextPageToken**: Token for the next page, if available

  - One of:
    1. Type: `string`
    2. Type: `null`

- **nextPageUrl**: URL for the next page, if available

  - One of:
    1. Type: `string`
    2. Type: `null`

- **optionalFields**: List of optional fields requested when these records were fetched

  - Type: `array`
  - Array of: `string`

- **pageSize**: Number of records per page

  - Type: `number`

- **previousPageToken**: Token for the previous page, if available

  - One of:
    1. Type: `string`
    2. Type: `null`

- **previousPageUrl**: URL for the previous page, if available

  - One of:
    1. Type: `string`
    2. Type: `null`

- **records**: Array of record objects

  - Type: `array`
  - Array of: `#/types/coreTypes/Record`

- **sortBy**: Sort criteria applied to the records

  - Type: `string`

- **where**: Filter clause applied to the records
  - Type: `string`

### Required Fields

- `count`
- `listReference`
- `pageSize`
- `records`

## RelatedListSummary

**Category:** relatedListTypes

**Description:** Summary of related list

**Type:** `object`

### Properties

- **apiName**: API name of the related list

  - Type: `string`

- **displayColumns**: Array of display column information

  - Type: `array`
  - Array of: `#/types/relatedListTypes/RelatedListColumn`

- **id**: Unique identifier for the related list

  - Type: `string`

- **label**: Display label for the related list

  - Type: `string`

- **listReference**: Reference information for the related list

  - Reference: `#/types/relatedListTypes/RelatedListReference`

- **orderedByInfo**: Array of ordering information

  - Type: `array`
  - Array of: `#/types/listTypes/ListOrderByInfo`

- **relatedListId**: Unique identifier for the related list

  - Type: `string`

- **url**: URL to access the related list
  - Type: `string`

### Required Fields

- `apiName`
- `displayColumns`
- `id`
- `label`
- `listReference`
- `relatedListId`
- `url`

## RelatedListSummaryCollection

**Category:** relatedListTypes

**Description:** Collection of related list summaries

**Type:** `object`

### Properties

- **count**: Total number of related lists in the collection

  - Type: `number`

- **currentPageToken**: Token representing the current page offset

  - Type: `string`

- **currentPageUrl**: URL for the current page of results

  - Type: `string`

- **eTag**: ETag for cache validation

  - Type: `string`

- **lists**: Array of related list summary objects

  - Type: `array`
  - Array of: `#/types/relatedListTypes/RelatedListSummary`

- **nextPageToken**: Token for the next page, if available

  - One of:
    1. Type: `string`
    2. Type: `null`

- **nextPageUrl**: URL for the next page, if available

  - One of:
    1. Type: `string`
    2. Type: `null`

- **objectApiName**: API name of the parent object

  - Type: `string`

- **pageSize**: Number of items per page

  - Type: `number`

- **previousPageToken**: Token for the previous page, if available

  - One of:
    1. Type: `string`
    2. Type: `null`

- **previousPageUrl**: URL for the previous page, if available
  - One of:
    1. Type: `string`
    2. Type: `null`

### Required Fields

- `count`
- `eTag`
- `lists`
- `objectApiName`
- `pageSize`

# listTypes

## ListFilterByInfo

**Category:** listTypes

**Description:** Filter information for lists

**Type:** `object`

### Properties

- **fieldApiName**: The API name for the field used to filter the list

  - Type: `string`

- **label**: The label for the field used to filter the list

  - Type: `string`

- **operandLabels**: The values used to filter the list

  - Type: `array`
  - Array of: `string`

- **operator**: The filter operator
  - Type: `string`
  - Allowed values: `Contains`, `Equals`, `Excludes`, `GreaterOrEqual`, `GreaterThan`, `Includes`, `LessOrEqual`, `LessThan`, `NotContain`, `NotEqual`, `StartsWith`, `Within`

### Required Fields

- `fieldApiName`
- `label`
- `operandLabels`
- `operator`

## ListOrderByInfo

**Category:** listTypes

**Description:** Ordering information for lists

**Type:** `object`

### Properties

- **fieldApiName**: The API name for the field

  - Type: `string`

- **isAscending**: Indicates whether the list column is ascending or descending

  - Type: `boolean`

- **label**: The localized label of the field
  - Type: `string`

### Required Fields

- `fieldApiName`
- `isAscending`
- `label`

## ListUserPreference

**Category:** listTypes

**Description:** User preferences for lists

**Type:** `object`

### Properties

- **columnWidths**: Column width preferences as a map of field names to widths

  - Type: `object`
  - Map values: `number`

- **columnWrap**: Column text wrapping preferences as a map of field names to wrap settings

  - Type: `object`
  - Map values: `boolean`

- **orderedBy**: Ordering information for the related list

  - Reference: `#/types/listTypes/ListOrderByInfo`

- **preferencesId**: The related list ID for the user preferences
  - Type: `string`

### Required Fields

- `preferencesId`

# uiTypes

## ThemeInfo

**Category:** uiTypes

**Description:** Theme information for objects

**Type:** `object`

### Properties

- **color**: Hex color code for the object's theme

  - Type: `string`
  - Pattern: `^#[0-9A-Fa-f]{6}$`

- **iconUrl**: URL to the object's icon
  - Type: `string`
  - Format: `uri`

### Required Fields

- `color`
- `iconUrl`

## FilteredLookupInfo

**Category:** uiTypes

**Description:** Information for filtered lookup fields

**Type:** `object`

### Properties

- **controllingFields**: Fields that control the filtering

  - Type: `array`
  - Array of: `string`

- **dependent**: Whether the lookup is dependent on other fields

  - Type: `boolean`

- **optionalFilter**: Whether the filter is optional
  - Type: `boolean`

### Required Fields

- `dependent`
- `optionalFilter`

# collectionTypes

## RecordCollection

**Category:** collectionTypes

**Description:** Collection of records

**Type:** `object`

### Properties

- **count**: Total number of records in the collection

  - Type: `number`

- **records**: Array of record objects
  - Type: `array`
  - Array of: `#/types/coreTypes/Record`

### Required Fields

- `count`
- `records`
