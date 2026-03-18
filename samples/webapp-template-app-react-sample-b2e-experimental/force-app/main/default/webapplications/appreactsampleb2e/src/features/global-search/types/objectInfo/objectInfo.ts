import type { GetObjectInfosQuery, GetPicklistValuesQuery } from "../schema";

// Generic utility types for extracting array item types
type ArrayItem<T> = T extends (infer Item)[] ? Item : never;
type NonNullableArrayItem<T> = NonNullable<ArrayItem<NonNullable<T>>>;

// ObjectInfos extraction
export type GetObjectInfosQueryObjectInfos = NonNullable<
	GetObjectInfosQuery["uiapi"]["objectInfos"]
>;
export type GetObjectInfosQueryObjectInfo = NonNullableArrayItem<GetObjectInfosQueryObjectInfos>;
export type GetObjectInfosQueryField = NonNullableArrayItem<
	GetObjectInfosQueryObjectInfo["fields"]
>;

// ObjectInfoResult types
export type ObjectInfoResult = Omit<GetObjectInfosQueryObjectInfo, "fields"> & {
	fields: Record<string, GetObjectInfosQueryField>;
};
export type ObjectInfoBatchResponse = {
	results: { result: ObjectInfoResult; statusCode: number }[];
};

// Picklist values extraction
export type GetPicklistValuesQueryObjectInfos = GetPicklistValuesQuery["uiapi"]["objectInfos"];
export type GetPicklistValuesQueryObjectInfo =
	NonNullableArrayItem<GetPicklistValuesQueryObjectInfos>;
export type GetPicklistValuesQueryField = NonNullableArrayItem<
	GetPicklistValuesQueryObjectInfo["fields"]
>;

// Extract picklist-specific field type (the one with picklistValuesByRecordTypeIDs)
type GetPicklistValuesQueryPicklistField = Extract<
	GetPicklistValuesQueryField,
	{ picklistValuesByRecordTypeIDs?: unknown }
>;

// Extract types from picklistValuesByRecordTypeIDs
type PicklistValuesByRecordTypeIDs =
	GetPicklistValuesQueryPicklistField["picklistValuesByRecordTypeIDs"];
type PicklistValuesByRecordTypeID = NonNullable<
	NonNullable<PicklistValuesByRecordTypeIDs> extends (infer Item)[] ? Item : null
>;

// Extract individual picklist value type
type PicklistValues = NonNullable<PicklistValuesByRecordTypeID>["picklistValues"];
export type PicklistValue = NonNullable<
	NonNullable<PicklistValues> extends (infer Item)[] ? Item : null
>;
