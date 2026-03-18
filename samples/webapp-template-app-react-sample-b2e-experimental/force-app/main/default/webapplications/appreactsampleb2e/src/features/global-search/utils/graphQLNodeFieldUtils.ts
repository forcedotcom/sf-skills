/**
 * GraphQL record node → display values for detail view.
 *
 * getGraphQLNodeValue: primitive by field path. getDisplayValueForDetailFieldFromNode: single field,
 * uses metadata to show relationship name instead of Id. getDisplayValueForLayoutItemFromNode:
 * single or compound (address, modstamp). getGraphQLRecordDisplayName: record title from nameFields.
 *
 * @module utils/graphQLNodeFieldUtils
 */

import type { FieldValue } from "../types/search/searchResults";
import type { GraphQLRecordNode } from "../api/recordListGraphQLService";
import type { ObjectInfoMetadata } from "./formDataTransformUtils";
import { getDisplayValueForLayoutItem, type LayoutItemDisplayResult } from "./fieldUtils";

/** Metadata from getObjectInfoBatch (object metadata) used to resolve reference fields by relationshipName. */
export type ObjectMetadataForDisplay = ObjectInfoMetadata | null | undefined;

/**
 * Gets a primitive value from a GraphQL node by field path.
 * - "Id" -> node.Id (scalar)
 * - "Name" -> node.Name?.value
 * - "Owner.Alias" -> node.Owner?.Alias?.value
 */
export function getGraphQLNodeValue(
	node: GraphQLRecordNode | null | undefined,
	fieldPath: string,
): string | number | boolean | null {
	if (!node || !fieldPath) return null;
	const parts = fieldPath.split(".");
	let current: unknown = node;
	for (let i = 0; i < parts.length; i++) {
		if (current == null || typeof current !== "object") return null;
		current = (current as Record<string, unknown>)[parts[i]];
	}
	if (current == null) return null;
	if (typeof current === "object" && current !== null && "value" in current) {
		const v = (current as { value: unknown }).value;
		if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
			return v;
		}
		if (v === null) return null;
		return v as string;
	}
	if (typeof current === "string" || typeof current === "number" || typeof current === "boolean") {
		return current as string | number | boolean;
	}
	// Relationship/lookup objects: try DisplayValue (scalar or object), Name.value, then Id
	if (typeof current === "object" && current !== null) {
		const obj = current as Record<string, unknown>;
		const displayVal = obj.DisplayValue ?? obj.displayValue;
		if (displayVal != null) {
			if (
				typeof displayVal === "string" ||
				typeof displayVal === "number" ||
				typeof displayVal === "boolean"
			) {
				return displayVal;
			}
			if (typeof displayVal === "object" && "value" in displayVal) {
				const v = (displayVal as { value: unknown }).value;
				if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") return v;
				if (v === null) return null;
				return v as string;
			}
		}
		const nameObj = obj.Name ?? obj.name;
		if (nameObj != null && typeof nameObj === "object" && "value" in nameObj) {
			const v = (nameObj as { value: unknown }).value;
			if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") return v;
			if (v === null) return null;
			return v as string;
		}
		const idVal = obj.Id ?? obj.id;
		if (
			idVal != null &&
			(typeof idVal === "string" || typeof idVal === "number" || typeof idVal === "boolean")
		) {
			return idVal;
		}
	}
	return null;
}

/** Builds a minimal Record<string, FieldValue> from node for the given api names (for reuse with fieldUtils formatters). */
function nodeToConstituentFields(
	node: GraphQLRecordNode,
	componentApiNames: string[],
	metadata?: ObjectMetadataForDisplay,
): Record<string, FieldValue> {
	const fields: Record<string, FieldValue> = {};
	for (const apiName of componentApiNames) {
		const v = getDisplayValueForDetailFieldFromNode(node, apiName, metadata);
		const displayValue = v as string | null;
		fields[apiName] = { displayValue, value: v };
	}
	return fields;
}

/**
 * Resolves display value for a layout item from a GraphQL node (single or multiple components).
 * Reuses address/modstamp formatting from fieldUtils by building minimal constituent fields from the node.
 * Pass metadata from getObjectInfoBatch so reference fields show the relationship's name instead of Id.
 */
export function getDisplayValueForLayoutItemFromNode(
	node: GraphQLRecordNode | null | undefined,
	componentApiNames: string[],
	metadata?: ObjectMetadataForDisplay,
): LayoutItemDisplayResult {
	if (!node || componentApiNames.length === 0) {
		return { value: null };
	}
	if (componentApiNames.length === 1) {
		const apiName = componentApiNames[0];
		const value = getDisplayValueForDetailFieldFromNode(node, apiName, metadata);
		const dataType = metadata?.fields?.[apiName]?.dataType;
		return { value, dataType };
	}
	const constituents = nodeToConstituentFields(node, componentApiNames, metadata);
	const result = getDisplayValueForLayoutItem(constituents, componentApiNames);
	return { value: result.value, dataType: result.dataType };
}

/**
 * Resolves display value for a single detail field from a GraphQL node.
 * When metadata from getObjectInfoBatch is provided and the field is a Reference (dataType === "Reference")
 * with a relationshipName, shows the related record's display value (e.g. Owner.Name) instead of the Id.
 */
/** Treat dataType as Reference regardless of casing (e.g. REFERENCE from GraphQL). */
function isReferenceDataType(dataType: string | undefined): boolean {
	return dataType != null && dataType.toLowerCase() === "reference";
}

export function getDisplayValueForDetailFieldFromNode(
	node: GraphQLRecordNode | null | undefined,
	apiName: string,
	metadata?: ObjectMetadataForDisplay,
): string | number | boolean | null {
	if (!node || !apiName) return null;
	const fieldMeta = metadata?.fields?.[apiName];
	if (
		fieldMeta &&
		isReferenceDataType(fieldMeta.dataType) &&
		fieldMeta.relationshipName != null &&
		fieldMeta.relationshipName !== ""
	) {
		const displayValue = getGraphQLNodeValue(node, fieldMeta.relationshipName);
		if (displayValue !== null && displayValue !== undefined && displayValue !== "") {
			return displayValue;
		}
	}
	return getGraphQLNodeValue(node, apiName);
}

/** Fallback field names for record display name when nameFields are not available. */
const DISPLAY_FIELD_CANDIDATES = [
	"Name",
	"CaseNumber",
	"Subject",
	"Title",
	"DeveloperName",
	"ContractNumber",
] as const;

/** Minimal metadata for record display name. */
export type GraphQLRecordDisplayNameMetadata = { nameFields?: string[] } | null;

/**
 * Resolves a display name for a record from a GraphQL node.
 * Tries metadata.nameFields first, then DISPLAY_FIELD_CANDIDATES, then node.Id.
 */
export function getGraphQLRecordDisplayName(
	node: GraphQLRecordNode | null | undefined,
	metadata?: GraphQLRecordDisplayNameMetadata,
): string {
	if (!node) return "";
	const id = (node.Id as string) ?? "";
	const candidates = [...(metadata?.nameFields ?? []), ...DISPLAY_FIELD_CANDIDATES];
	for (const fieldPath of candidates) {
		const v = getGraphQLNodeValue(node, fieldPath);
		if (v !== null && v !== undefined && v !== "") {
			return v as string;
		}
	}
	return id;
}
