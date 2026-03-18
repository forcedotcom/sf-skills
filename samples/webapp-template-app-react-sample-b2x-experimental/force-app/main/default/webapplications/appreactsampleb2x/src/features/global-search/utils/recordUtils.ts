/**
 * Record utilities: layout-derived fields for GraphQL fetch, safe keys, ID validation.
 *
 * calculateFieldsToFetch: from layout + object metadata → field names and relation map;
 * used by objectDetailService and list to build columns. findIdFieldForRelationship ensures
 * Id + relationship name are both requested for reference display.
 *
 * @module utils/recordUtils
 */

import type { ObjectInfoResult } from "../types/objectInfo/objectInfo";
import type {
	LayoutResponse,
	LayoutRow,
	LayoutSection,
	LayoutItem,
	LayoutComponent,
} from "../types/recordDetail/recordDetail";

/**
 * Find the Id field (reference foreign key) whose relationshipName matches the given name,
 * so we can request both Id and relationship in the record query for display.
 */
function findIdFieldForRelationship(
	metadata: ObjectInfoResult,
	relationshipName: string,
): string | null {
	if (!metadata.fields || !relationshipName) return null;
	for (const [apiName, field] of Object.entries(metadata.fields)) {
		const isReference = field.dataType != null && field.dataType.toLowerCase() === "reference";
		if (field.relationshipName === relationshipName && (isReference || apiName.endsWith("Id"))) {
			return apiName;
		}
	}
	return null;
}

const getFetchableFieldsFromLayoutItem = function (
	metadata: ObjectInfoResult,
	layoutItem: LayoutItem,
	relationFieldMap: Record<string, string>,
) {
	const fields: Record<string, string> = {};
	layoutItem.layoutComponents.forEach((comp: LayoutComponent) => {
		// check if this is a field to add
		if (!comp.apiName || comp.componentType !== "Field") {
			return;
		}

		// add field: fieldType
		const fieldMetadata = metadata.fields[comp.apiName];
		fields[comp.apiName] = fieldMetadata?.dataType ?? "";

		// add relatedField if one exists (Id field -> add relationship name so we request Owner.Name)
		if (comp.apiName in metadata.fields) {
			const relationshipName = fieldMetadata?.relationshipName;
			if (relationshipName) {
				fields[relationshipName] = fieldMetadata.dataType ?? "";

				relationFieldMap[comp.apiName] = relationshipName;
			}
		} else {
			// layout component is relationship name (e.g. Owner); ensure we also request the Id
			// so buildSelectionTree sees both OwnerId and Owner and requests Owner { Name { value } }
			const idField = findIdFieldForRelationship(metadata, comp.apiName);
			if (idField) {
				const idMeta = metadata.fields[idField];
				fields[idField] = idMeta?.dataType ?? "";
				relationFieldMap[idField] = comp.apiName;
			}
		}
	});
	return fields;
};

const getFetchableFieldsFromLayoutRow = function (
	metadata: ObjectInfoResult,
	layoutRow: LayoutRow,
	relationFieldMap: Record<string, string>,
) {
	let fieldsFromRow: Record<string, string> = {};
	layoutRow.layoutItems.forEach((item: LayoutItem) => {
		Object.assign(
			fieldsFromRow,
			getFetchableFieldsFromLayoutItem(metadata, item, relationFieldMap),
		);
	});
	return fieldsFromRow;
};

const getFetchableFieldsFromSection = function (
	metadata: ObjectInfoResult,
	section: LayoutSection,
	relationFieldMap: Record<string, string>,
) {
	let fieldsFromSection: Record<string, string> = {};
	section.layoutRows.forEach((row: LayoutRow) => {
		Object.assign(
			fieldsFromSection,
			getFetchableFieldsFromLayoutRow(metadata, row, relationFieldMap),
		);
	});
	return fieldsFromSection;
};

const getFetchableFieldsFromLayout = function (
	metadata: ObjectInfoResult,
	layout: LayoutResponse,
	relationFieldMap: Record<string, string>,
) {
	let fieldsFromLayout: Record<string, string> = {};
	layout.sections.forEach((section) => {
		Object.assign(
			fieldsFromLayout,
			getFetchableFieldsFromSection(metadata, section, relationFieldMap),
		);
	});
	return fieldsFromLayout;
};

/**
 * Returns field API names to request for records from layout + object metadata.
 * Includes both Id and relationship name for reference fields so GraphQL can fetch display value.
 *
 * @param metadata - Object info (fields with dataType, relationshipName).
 * @param layout - Layout response (sections, layoutItems, layoutComponents).
 * @param shouldPrefixedWithEntityName - If true, prefix names with object (e.g. Account.Name).
 * @returns [fieldNames, fieldTypes, relationFieldMap] for buildSelectionTree / optionalFields.
 */
export const calculateFieldsToFetch = function (
	metadata: ObjectInfoResult,
	layout: LayoutResponse,
	shouldPrefixedWithEntityName: boolean,
): [string[], string[], Record<string, string>] {
	const relationFieldMap: Record<string, string> = {};
	// populating fields to query for layout
	const fields = getFetchableFieldsFromLayout(metadata, layout, relationFieldMap);
	let fieldsToFetch = Object.keys(fields);
	if (shouldPrefixedWithEntityName) {
		fieldsToFetch = fieldsToFetch.map((field) => `${metadata.ApiName}.${field}`);
	}
	// populate field types for o11y logging
	const fieldTypes = Object.values(fields).filter((fieldType) => fieldType !== "");
	return [fieldsToFetch, fieldTypes, relationFieldMap];
};
/** Type guard: true if id is a non-empty string matching 15- or 18-char Salesforce ID format. */
export function isValidSalesforceId(id: string | null | undefined): id is string {
	if (!id || typeof id !== "string") return false;
	return /^[a-zA-Z0-9]{15}$|^[a-zA-Z0-9]{18}$/.test(id);
}

/** Safe React key from record id or fallback to prefix-index. */
export function getSafeKey(
	recordId: string | null | undefined,
	index: number,
	prefix: string = "result",
): string {
	return isValidSalesforceId(recordId) ? recordId : `${prefix}-${index}`;
}
