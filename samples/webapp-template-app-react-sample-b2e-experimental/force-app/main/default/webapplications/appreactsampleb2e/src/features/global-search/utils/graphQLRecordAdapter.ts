/**
 * Adapts GraphQL UI API node shape to SearchResultRecordData so existing list UI
 * (SearchResultCard, ResultCardFields, getNestedFieldValue) works unchanged.
 *
 * GraphQL node: { Id, Name: { value }, Owner: { Alias: { value } }, ... }
 * SearchResultRecordData: { id, fields: Record<string, FieldValue>, apiName, ... }
 * FieldValue: { displayValue, value }
 */

import type { FieldValue, SearchResultRecordData } from "../types/search/searchResults";

function isValueLeaf(obj: unknown): obj is { value: string | number | boolean | null } {
	return (
		typeof obj === "object" &&
		obj !== null &&
		"value" in obj &&
		(Object.keys(obj).length === 1 || (Object.keys(obj).length === 2 && "displayValue" in obj))
	);
}

function graphQLValueToFieldValue(val: unknown): FieldValue {
	if (val === null || val === undefined) {
		return { displayValue: null, value: null };
	}
	if (isValueLeaf(val)) {
		const v = val.value;
		const display =
			typeof v === "string" || typeof v === "number" || typeof v === "boolean" ? v : null;
		return { displayValue: display as string | null, value: v };
	}
	if (typeof val === "object" && val !== null && !Array.isArray(val)) {
		const nested = graphQLNodeToFields(val as Record<string, unknown>);
		const firstFv = nested && Object.values(nested)[0];
		const display =
			firstFv && typeof (firstFv as FieldValue).value !== "object"
				? ((firstFv as FieldValue).value as string | null)
				: null;
		return { displayValue: display, value: { fields: nested ?? {} } };
	}
	return { displayValue: null, value: val };
}

function graphQLNodeToFields(node: Record<string, unknown>): Record<string, FieldValue> {
	const fields: Record<string, FieldValue> = {};
	for (const [key, val] of Object.entries(node)) {
		if (key === "Id" || val === undefined) continue;
		fields[key] = graphQLValueToFieldValue(val);
	}
	return fields;
}

/**
 * Converts a GraphQL connection node (from getRecordsGraphQL) to SearchResultRecordData
 * so it can be passed to SearchResultCard and other components that expect the keyword-search record shape.
 */
export function graphQLNodeToSearchResultRecordData(
	node: Record<string, unknown> | undefined,
	objectApiName: string,
): SearchResultRecordData {
	if (!node || typeof node !== "object") {
		return {
			id: "",
			apiName: objectApiName,
			childRelationships: {},
			eTag: "",
			fields: {},
			lastModifiedById: null,
			lastModifiedDate: null,
			recordTypeId: null,
			recordTypeInfo: null,
			systemModstamp: null,
			weakEtag: 0,
		};
	}
	const id = (node.Id as string) ?? "";
	const fields = graphQLNodeToFields(node);
	return {
		id,
		apiName: objectApiName,
		childRelationships: {},
		eTag: "",
		fields,
		lastModifiedById: null,
		lastModifiedDate: null,
		recordTypeId: null,
		recordTypeInfo: null,
		systemModstamp: null,
		weakEtag: 0,
	};
}
