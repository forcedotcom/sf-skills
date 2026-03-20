/**
 * Transforms UI API record + object info into detail form shape: Reference fields get
 * relationshipField, compound fields get constituents, metadata gets editable flag.
 * Aligns with LWC detailForm _calculateFormData and uiApiDataTransformHelper.
 */

import type { FieldValue } from "../types/search/searchResults";

/** Field metadata from object info API (subset used by form transform). */
export interface ObjectInfoFieldMetadata {
	compound?: boolean;
	compoundFieldName?: string;
	compoundComponentName?: string;
	dataType?: string;
	relationshipName?: string;
	updateable?: boolean;
	calculated?: boolean;
	polymorphicForeignKey?: boolean;
	apiName?: string;
	label?: string;
	[name: string]: unknown;
}

/** Minimal UI API object info (metadata) for form data transform. */
export interface ObjectInfoMetadata {
	apiName?: string;
	fields?: Record<string, ObjectInfoFieldMetadata>;
	[name: string]: unknown;
}

/** Transformed field value: base FieldValue + relationshipField (Reference) and constituents (compound). */
export interface TransformedFieldValue extends FieldValue {
	relationshipField?: FieldValue;
	constituents?: Record<string, TransformedFieldValue & { metadata?: ObjectInfoFieldMetadata }>;
}

export type TransformedDataFields = Record<string, TransformedFieldValue>;

/** Form values keyed by record context id (e.g. record.id). */
export type FormValues = Record<string, TransformedDataFields>;

/** Form metadata keyed by metadata context (e.g. object apiName). */
export type FormMetadata = Record<string, ObjectInfoMetadata>;

/** Contexts: recordId -> objectApiName. */
export type FormContexts = Record<string, string>;

/** Result of calculateFormData (single record). */
export interface FormData {
	formValues: FormValues;
	formMetadata: FormMetadata;
	formContexts: FormContexts;
}

/** Fields never editable per UI API (platform convention). */
const NON_EDITABLE_FIELDS = ["OwnerId", "RecordTypeId"];

/** Created By / Last Modified By: synthetic compound from Id + Date (modstampMetadataTransform). */
const SYSTEM_FIELDS = [
	{
		fieldName: "CreatedBy",
		idFieldName: "CreatedById",
		dateFieldName: "CreatedDate",
		apiName: "CreatedBy",
		compound: true,
		dataType: "String",
		label: "Created By",
	},
	{
		fieldName: "LastModifiedBy",
		idFieldName: "LastModifiedById",
		dateFieldName: "LastModifiedDate",
		apiName: "LastModifiedBy",
		compound: true,
		dataType: "String",
		label: "Last Modified By",
	},
];

function modstampMetadataTransform(metadata: ObjectInfoMetadata): ObjectInfoMetadata {
	const fields = { ...metadata.fields };
	if (!fields) return metadata;

	SYSTEM_FIELDS.forEach((systemField) => {
		const field = systemField.fieldName;
		const idField = systemField.idFieldName;
		const dateField = systemField.dateFieldName;
		if (idField in fields && dateField in fields && metadata.fields) {
			fields[field] = { ...metadata.fields[idField], ...systemField };
			fields[idField] = {
				...(metadata.fields[idField] ?? {}),
				compoundComponentName: "Id",
				compoundFieldName: field,
			};
			fields[dateField] = {
				...(metadata.fields[dateField] ?? {}),
				compoundComponentName: "Date",
				compoundFieldName: field,
			};
		}
	});
	return { ...metadata, fields };
}

export function metaDataTransform(metadata: ObjectInfoMetadata): ObjectInfoMetadata {
	const newMetadata = modstampMetadataTransform(metadata);
	const fields: Record<string, ObjectInfoFieldMetadata> = {};
	const metaFields = newMetadata.fields ?? {};
	Object.keys(metaFields).forEach((fieldName) => {
		const fieldRep = metaFields[fieldName];
		const isCalculated = Boolean(fieldRep.calculated);
		const isUpdateable = Boolean(fieldRep.updateable);
		const isPolymorphicLookup = Boolean(fieldRep.polymorphicForeignKey);
		fields[fieldName] = {
			...fieldRep,
			editable:
				!isCalculated &&
				isUpdateable &&
				!isPolymorphicLookup &&
				!NON_EDITABLE_FIELDS.includes(fieldName),
		} as ObjectInfoFieldMetadata;
	});
	return { ...newMetadata, fields };
}

export function getConstituentMap(
	dataFields: Record<string, FieldValue>,
	fieldMetadata: Record<string, ObjectInfoFieldMetadata>,
): Record<string, Record<string, TransformedFieldValue & { metadata?: ObjectInfoFieldMetadata }>> {
	const constituentMap: Record<
		string,
		Record<string, TransformedFieldValue & { metadata?: ObjectInfoFieldMetadata }>
	> = {};
	Object.keys(fieldMetadata).forEach((fieldApiName) => {
		const { compoundFieldName } = fieldMetadata[fieldApiName];
		if (compoundFieldName && dataFields[fieldApiName]) {
			const constituentFields =
				constituentMap[compoundFieldName] ??
				({} as Record<string, TransformedFieldValue & { metadata?: ObjectInfoFieldMetadata }>);
			const raw = dataFields[fieldApiName] as TransformedFieldValue;
			constituentFields[fieldApiName] = {
				...raw,
				metadata: fieldMetadata[fieldApiName],
			};
			constituentMap[compoundFieldName] = constituentFields;

			const compoundMeta = fieldMetadata[compoundFieldName];
			if (
				compoundMeta?.dataType === "Address" &&
				(fieldApiName.endsWith("StateCode") || fieldApiName.endsWith("CountryCode"))
			) {
				const nonPicklistName = fieldApiName.replace("Code", "");
				if (fieldMetadata[nonPicklistName] && dataFields[nonPicklistName]) {
					constituentFields[nonPicklistName] = {
						...(dataFields[nonPicklistName] as TransformedFieldValue),
						metadata: fieldMetadata[nonPicklistName],
					};
				}
			}
		}
	});
	if (constituentMap.Name) {
		const constituentApiNames = Object.keys(constituentMap.Name);
		if (constituentApiNames.length === 1 && constituentApiNames[0] === "Name") {
			delete constituentMap.Name;
		}
	}
	return constituentMap;
}

export function objectInfoFieldsTransform(
	dataFields: Record<string, FieldValue>,
	metadata: ObjectInfoMetadata,
): TransformedDataFields {
	const fieldMetadata = metadata.fields ?? {};
	const transformedDataFields: TransformedDataFields = { ...dataFields };

	Object.keys(fieldMetadata).forEach((field) => {
		const meta = fieldMetadata[field];
		if (meta.dataType === "Reference" && meta.relationshipName != null) {
			const existing = dataFields[field];
			const relField = dataFields[meta.relationshipName];
			transformedDataFields[field] = {
				...(existing ?? {}),
				relationshipField: {
					...(relField ?? {}),
					value: null,
				},
			};
		}
	});

	Object.keys(fieldMetadata).forEach((field) => {
		const meta = fieldMetadata[field];
		const { compound, dataType } = meta;
		const existing = dataFields[field];
		if (dataType === "Reference") return;
		if (compound) {
			transformedDataFields[field] = { ...(existing ?? {}) };
		} else if (existing) {
			transformedDataFields[field] = existing as TransformedFieldValue;
		}
	});

	const constituentMap = getConstituentMap(transformedDataFields, fieldMetadata);
	Object.keys(constituentMap).forEach((field) => {
		if (transformedDataFields[field]) {
			transformedDataFields[field] = {
				...transformedDataFields[field],
				constituents: constituentMap[field],
			};
		}
	});
	return transformedDataFields;
}

export function multiRecordMetadataTransform(
	metadata: Record<string, ObjectInfoMetadata>,
): FormMetadata {
	const result: FormMetadata = {};
	Object.keys(metadata).forEach((metadataContext) => {
		result[metadataContext] = metaDataTransform(metadata[metadataContext]);
	});
	return result;
}

export function multiRecordValuesTransform(
	values: Record<string, Record<string, FieldValue>>,
	metadata: FormMetadata,
	contexts: FormContexts,
): FormValues {
	const result: FormValues = {};
	Object.keys(values).forEach((recordContext) => {
		const metadataContext = contexts[recordContext];
		if (metadataContext && metadata[metadataContext]) {
			result[recordContext] = objectInfoFieldsTransform(
				values[recordContext],
				metadata[metadataContext],
			);
		}
	});
	return result;
}

export function calculateFormData(
	record: { id: string; apiName: string; fields: Record<string, FieldValue> },
	metadata: ObjectInfoMetadata | null | undefined,
): FormData {
	const formValues: FormValues = {};
	const formMetadata: FormMetadata = {};
	const formContexts: FormContexts = { [record.id]: record.apiName };

	if (!metadata?.fields) {
		return { formValues, formMetadata, formContexts };
	}

	formMetadata[record.apiName] = metaDataTransform(metadata);
	formValues[record.id] = objectInfoFieldsTransform(record.fields, formMetadata[record.apiName]);
	return { formValues, formMetadata, formContexts };
}
