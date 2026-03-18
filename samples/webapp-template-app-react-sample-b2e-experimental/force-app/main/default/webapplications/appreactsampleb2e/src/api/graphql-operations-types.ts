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
	Currency: { input: number | string; output: number };
	Date: { input: string; output: string };
	DateTime: { input: string; output: string };
	Double: { input: number | string; output: number };
	Email: { input: string; output: string };
	EncryptedString: { input: string; output: string };
	/** Can be set to an ID or a Reference to the result of another mutation operation. */
	IdOrRef: { input: string; output: string };
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
	TextArea: { input: string; output: string };
	Time: { input: string; output: string };
	Url: { input: string; output: string };
};

export type Application__CUpdateInput = {
	Application__c: Application__CUpdateRepresentation;
	Id: Scalars["IdOrRef"]["input"];
};

export type Application__CUpdateRepresentation = {
	Employment__c?: InputMaybe<Scalars["LongTextArea"]["input"]>;
	OwnerId?: InputMaybe<Scalars["IdOrRef"]["input"]>;
	Property__c?: InputMaybe<Scalars["IdOrRef"]["input"]>;
	References__c?: InputMaybe<Scalars["LongTextArea"]["input"]>;
	Start_Date__c?: InputMaybe<Scalars["Date"]["input"]>;
	Status__c?: InputMaybe<Scalars["Picklist"]["input"]>;
	User__c?: InputMaybe<Scalars["IdOrRef"]["input"]>;
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

export enum LayoutComponentType {
	Canvas = "CANVAS",
	CustomLink = "CUSTOM_LINK",
	EmptySpace = "EMPTY_SPACE",
	Field = "FIELD",
	ReportChart = "REPORT_CHART",
	VisualforcePage = "VISUALFORCE_PAGE",
}

export enum LayoutMode {
	Create = "CREATE",
	Edit = "EDIT",
	View = "VIEW",
}

export enum LayoutType {
	Compact = "COMPACT",
	Full = "FULL",
}

export type Maintenance_Request__CUpdateInput = {
	Id: Scalars["IdOrRef"]["input"];
	Maintenance_Request__c: Maintenance_Request__CUpdateRepresentation;
};

export type Maintenance_Request__CUpdateRepresentation = {
	Actual_Cost__c?: InputMaybe<Scalars["Currency"]["input"]>;
	Assigned_Worker__c?: InputMaybe<Scalars["IdOrRef"]["input"]>;
	Completed__c?: InputMaybe<Scalars["DateTime"]["input"]>;
	Description__c?: InputMaybe<Scalars["LongTextArea"]["input"]>;
	Est_Cost__c?: InputMaybe<Scalars["Currency"]["input"]>;
	OwnerId?: InputMaybe<Scalars["IdOrRef"]["input"]>;
	Priority__c?: InputMaybe<Scalars["Picklist"]["input"]>;
	Property__c?: InputMaybe<Scalars["IdOrRef"]["input"]>;
	Scheduled__c?: InputMaybe<Scalars["DateTime"]["input"]>;
	Status__c?: InputMaybe<Scalars["Picklist"]["input"]>;
	Tenant_Home__c?: InputMaybe<Scalars["Boolean"]["input"]>;
	Type__c?: InputMaybe<Scalars["Picklist"]["input"]>;
	User__c?: InputMaybe<Scalars["IdOrRef"]["input"]>;
};

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

export enum TabOrder {
	LeftRight = "LEFT_RIGHT",
	TopDown = "TOP_DOWN",
}

export enum UiBehavior {
	Edit = "EDIT",
	Readonly = "READONLY",
	Required = "REQUIRED",
}

export type GetApplicationsQueryVariables = Exact<{ [key: string]: never }>;

export type GetApplicationsQuery = {
	uiapi: {
		query: {
			Application__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null } | null;
						User__r?: {
							FirstName?: { value?: string | null } | null;
							LastName?: { value?: string | null } | null;
						} | null;
						Property__r?: {
							Name?: { value?: string | null } | null;
							Address__c?: { value?: string | null } | null;
						} | null;
						Start_Date__c?: { value?: string | null } | null;
						Status__c?: { value?: string | null } | null;
						Employment__c?: { value?: string | null } | null;
						References__c?: { value?: string | null } | null;
					} | null;
				} | null> | null;
			} | null;
		};
	};
};

export type UpdateApplicationStatusMutationVariables = Exact<{
	input: Application__CUpdateInput;
}>;

export type UpdateApplicationStatusMutation = {
	uiapi: {
		Application__cUpdate?: {
			success?: boolean | null;
			Record?: { Id: string; Status__c?: { value?: string | null } | null } | null;
		} | null;
	};
};

export type GetDashboardMetricsQueryVariables = Exact<{ [key: string]: never }>;

export type GetDashboardMetricsQuery = {
	uiapi: {
		query: {
			allProperties?: {
				edges?: Array<{
					node?: { Id: string; Status__c?: { value?: string | null } | null } | null;
				} | null> | null;
			} | null;
			maintenanceRequests?: {
				edges?: Array<{
					node?: { Id: string; Type__c?: { value?: string | null } | null } | null;
				} | null> | null;
			} | null;
		};
	};
};

export type GetOpenApplicationsQueryVariables = Exact<{
	first?: InputMaybe<Scalars["Int"]["input"]>;
}>;

export type GetOpenApplicationsQuery = {
	uiapi: {
		query: {
			Application__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null } | null;
						User__r?: { Name?: { value?: string | null } | null } | null;
						Property__r?: { Address__c?: { value?: string | null } | null } | null;
						Status__c?: { value?: string | null } | null;
						CreatedDate?: { value?: string | null } | null;
					} | null;
				} | null> | null;
			} | null;
		};
	};
};

export type GetUserInfoQueryVariables = Exact<{ [key: string]: never }>;

export type GetUserInfoQuery = {
	uiapi: {
		query: {
			User?: {
				edges?: Array<{
					node?: { Id: string; Name?: { value?: string | null } | null } | null;
				} | null> | null;
			} | null;
		};
	};
};

export type GetMaintenanceRequestsQueryVariables = Exact<{
	first?: InputMaybe<Scalars["Int"]["input"]>;
}>;

export type GetMaintenanceRequestsQuery = {
	uiapi: {
		query: {
			Maintenance_Request__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null } | null;
						Property__r?: { Address__c?: { value?: string | null } | null } | null;
						User__r?: { Name?: { value?: string | null } | null } | null;
						Type__c?: { value?: string | null } | null;
						Priority__c?: { value?: string | null } | null;
						Status__c?: { value?: string | null } | null;
						Description__c?: { value?: string | null } | null;
						Scheduled__c?: { value?: string | null } | null;
					} | null;
				} | null> | null;
			} | null;
		};
	};
};

export type GetAllMaintenanceRequestsQueryVariables = Exact<{
	first?: InputMaybe<Scalars["Int"]["input"]>;
	after?: InputMaybe<Scalars["String"]["input"]>;
}>;

export type GetAllMaintenanceRequestsQuery = {
	uiapi: {
		query: {
			Maintenance_Request__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null } | null;
						Description__c?: { value?: string | null } | null;
						Type__c?: { value?: string | null } | null;
						Priority__c?: { value?: string | null } | null;
						Status__c?: { value?: string | null } | null;
						Scheduled__c?: { value?: string | null } | null;
						Property__r?: {
							Address__c?: { value?: string | null } | null;
							Name?: { value?: string | null } | null;
						} | null;
						User__r?: { Name?: { value?: string | null } | null } | null;
						Assigned_Worker__r?: {
							Name?: { value?: string | null } | null;
							Employment_Type__c?: { value?: string | null } | null;
						} | null;
						ContentDocumentLinks?: {
							edges?: Array<{
								node?: {
									ContentDocument?: {
										LatestPublishedVersionId?: { value?: string | null } | null;
									} | null;
								} | null;
							} | null> | null;
						} | null;
					} | null;
				} | null> | null;
				pageInfo: { hasNextPage: boolean; endCursor?: string | null };
			} | null;
		};
	};
};

export type UpdateMaintenanceStatusMutationVariables = Exact<{
	input: Maintenance_Request__CUpdateInput;
}>;

export type UpdateMaintenanceStatusMutation = {
	uiapi: {
		Maintenance_Request__cUpdate?: {
			success?: boolean | null;
			Record?: { Id: string; Status__c?: { value?: string | null } | null } | null;
		} | null;
	};
};

export type GetPropertiesQueryVariables = Exact<{
	first?: InputMaybe<Scalars["Int"]["input"]>;
	after?: InputMaybe<Scalars["String"]["input"]>;
}>;

export type GetPropertiesQuery = {
	uiapi: {
		query: {
			Property__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null } | null;
						Address__c?: { value?: string | null } | null;
						Description__c?: { value?: string | null } | null;
						Type__c?: { value?: string | null } | null;
						Status__c?: { value?: string | null } | null;
						Monthly_Rent__c?: { value?: number | null } | null;
						Bedrooms__c?: { value?: number | null } | null;
						Bathrooms__c?: { value?: number | null } | null;
						Sq_Ft__c?: { value?: number | null } | null;
						Year_Built__c?: { value?: number | null } | null;
						Hero_Image__c?: { value?: string | null } | null;
						Deposit__c?: { value?: number | null } | null;
						Parking__c?: { value?: number | null } | null;
						Pet_Friendly__c?: { value?: boolean | null } | null;
						Available_Date__c?: { value?: string | null } | null;
						Lease_Term__c?: { value?: number | null } | null;
						Features__c?: { value?: string | null } | null;
						Utilities__c?: { value?: string | null } | null;
						Tour_URL__c?: { value?: string | null } | null;
						CreatedDate?: { value?: string | null } | null;
					} | null;
				} | null> | null;
				pageInfo: { hasNextPage: boolean; endCursor?: string | null };
			} | null;
		};
	};
};

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
