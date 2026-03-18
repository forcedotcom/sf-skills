export type Maybe<T> = T | null;
export type InputMaybe<T> = Maybe<T>;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
export type MakeEmpty<T extends { [key: string]: unknown }, K extends keyof T> = {
	[_ in K]?: never;
};
export type Incremental<T> =
	| T
	| { [P in keyof T]?: P extends " $fragmentName" | "__typename" ? T[P] : never };
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
	ID: { input: string; output: string };
	String: { input: string; output: string };
	Boolean: { input: boolean; output: boolean };
	Int: { input: number; output: number };
	Float: { input: number; output: number };
	Base64: { input: string; output: string };
	/** An arbitrary precision signed decimal */
	BigDecimal: { input: number | string; output: number };
	/** An arbitrary precision signed integer */
	BigInteger: { input: number; output: number };
	/** An 8-bit signed integer */
	Byte: { input: number; output: number };
	/** A UTF-16 code unit; a character on Unicode's BMP */
	Char: { input: number; output: number };
	Currency: { input: number | string; output: number };
	Date: { input: string; output: string };
	DateTime: { input: string; output: string };
	Double: { input: number | string; output: number };
	Email: { input: string; output: string };
	EncryptedString: { input: string; output: string };
	/** Can be set to an ID or a Reference to the result of another mutation operation. */
	IdOrRef: { input: string; output: string };
	JSON: { input: string; output: string };
	Latitude: { input: number | string; output: number };
	/** A 64-bit signed integer */
	Long: { input: number; output: number };
	LongTextArea: { input: string; output: string };
	Longitude: { input: number | string; output: number };
	MultiPicklist: { input: string; output: string };
	Percent: { input: number | string; output: number };
	PhoneNumber: { input: string; output: string };
	Picklist: { input: string; output: string };
	RichTextArea: { input: string; output: string };
	/** A 16-bit signed integer */
	Short: { input: number; output: number };
	TextArea: { input: string; output: string };
	Time: { input: string; output: string };
	Url: { input: string; output: string };
};

export enum DataType {
	Address = "ADDRESS",
	Anytype = "ANYTYPE",
	Base64 = "BASE64",
	Boolean = "BOOLEAN",
	Combobox = "COMBOBOX",
	Complexvalue = "COMPLEXVALUE",
	Currency = "CURRENCY",
	Date = "DATE",
	Datetime = "DATETIME",
	Double = "DOUBLE",
	Email = "EMAIL",
	Encryptedstring = "ENCRYPTEDSTRING",
	Int = "INT",
	Json = "JSON",
	Junctionidlist = "JUNCTIONIDLIST",
	Location = "LOCATION",
	Long = "LONG",
	Multipicklist = "MULTIPICKLIST",
	Percent = "PERCENT",
	Phone = "PHONE",
	Picklist = "PICKLIST",
	Reference = "REFERENCE",
	String = "STRING",
	Textarea = "TEXTAREA",
	Time = "TIME",
	Url = "URL",
}

export enum FieldExtraTypeInfo {
	ExternalLookup = "EXTERNAL_LOOKUP",
	ImageUrl = "IMAGE_URL",
	IndirectLookup = "INDIRECT_LOOKUP",
	Personname = "PERSONNAME",
	Plaintextarea = "PLAINTEXTAREA",
	Richtextarea = "RICHTEXTAREA",
	SwitchablePersonname = "SWITCHABLE_PERSONNAME",
}

/** Input for ObjectInfo and PickValues */
export type ObjectInfoInput = {
	apiName: Scalars["String"]["input"];
	fieldNames?: InputMaybe<Array<Scalars["String"]["input"]>>;
	recordTypeIDs?: InputMaybe<Array<Scalars["ID"]["input"]>>;
};

export enum ResultOrder {
	Asc = "ASC",
	Desc = "DESC",
}

export type GetObjectInfosQueryVariables = Exact<{
	apiNames: Array<Scalars["String"]["input"]> | Scalars["String"]["input"];
}>;

export type GetObjectInfosQuery = {
	uiapi: {
		objectInfos?: Array<{
			ApiName: string;
			label?: string | null;
			labelPlural?: string | null;
			nameFields: Array<string | null>;
			defaultRecordTypeId?: string | null;
			keyPrefix?: string | null;
			layoutable: boolean;
			queryable: boolean;
			searchable: boolean;
			updateable: boolean;
			deletable: boolean;
			createable: boolean;
			custom: boolean;
			mruEnabled: boolean;
			feedEnabled: boolean;
			fields: Array<
				| {
						ApiName: string;
						label?: string | null;
						dataType?: DataType | null;
						relationshipName?: string | null;
						reference: boolean;
						compound: boolean;
						compoundFieldName?: string | null;
						compoundComponentName?: string | null;
						controllingFields: Array<string | null>;
						controllerName?: string | null;
						referenceToInfos: Array<{ ApiName: string; nameFields: Array<string | null> } | null>;
				  }
				| {
						ApiName: string;
						label?: string | null;
						dataType?: DataType | null;
						relationshipName?: string | null;
						reference: boolean;
						compound: boolean;
						compoundFieldName?: string | null;
						compoundComponentName?: string | null;
						controllingFields: Array<string | null>;
						controllerName?: string | null;
						referenceToInfos: Array<{ ApiName: string; nameFields: Array<string | null> } | null>;
				  }
				| null
			>;
			recordTypeInfos: Array<{
				recordTypeId?: string | null;
				name?: string | null;
				master: boolean;
				available: boolean;
				defaultRecordTypeMapping: boolean;
			} | null>;
			themeInfo?: { color?: string | null; iconUrl?: string | null } | null;
			childRelationships: Array<{
				relationshipName?: string | null;
				fieldName?: string | null;
				childObjectApiName: string;
			} | null>;
			dependentFields: Array<{ controllingField: string } | null>;
		} | null> | null;
	};
};

export type GetPicklistValuesQueryVariables = Exact<{
	objectInfoInputs: Array<ObjectInfoInput> | ObjectInfoInput;
}>;

export type GetPicklistValuesQuery = {
	uiapi: {
		objectInfos?: Array<{
			ApiName: string;
			fields: Array<
				| {
						ApiName: string;
						picklistValuesByRecordTypeIDs?: Array<{
							recordTypeID: string;
							defaultValue?: { value?: string | null } | null;
							picklistValues?: Array<{
								label?: string | null;
								value?: string | null;
								validFor?: Array<number | null> | null;
							}> | null;
						} | null> | null;
				  }
				| { ApiName: string }
				| null
			>;
		} | null> | null;
	};
};
