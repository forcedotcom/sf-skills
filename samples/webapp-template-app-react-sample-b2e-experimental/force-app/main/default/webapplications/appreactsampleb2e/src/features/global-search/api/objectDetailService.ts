/**
 * Record detail service: layout (REST), object metadata (GraphQL), single record (GraphQL).
 *
 * getRecordDetail orchestrates layout + objectInfoBatch + getRecordByIdGraphQL for the detail page.
 * Layout is still REST (uiApiClient); record and object info are GraphQL-backed.
 *
 * @module api/objectDetailService
 */

import { uiApiClient } from "@salesforce/webapp-experimental/api";
import type { LayoutResponse } from "../types/recordDetail/recordDetail";
import { LayoutResponseSchema } from "../types/recordDetail/recordDetail";
import { fetchAndValidate, safeEncodePath } from "../utils/apiUtils";
import { objectInfoService } from "./objectInfoService";
import type { ObjectInfoResult } from "../types/objectInfo/objectInfo";
import { getRecordByIdGraphQL, type GraphQLRecordNode } from "./recordListGraphQLService";
import type { Column } from "../types/search/searchResults";
import { calculateFieldsToFetch } from "../utils/recordUtils";

/** Fallback when record type is unknown. Prefer recordTypeId from the record (e.g. from search or record response) when available. */
const DEFAULT_RECORD_TYPE_ID = "012000000000000AAA";

/**
 * Returns field API names to request for a record from the given layout and object metadata.
 * Used to derive GraphQL columns from layout (detail view). Delegates to recordUtils.calculateFieldsToFetch.
 *
 * @param objectMetadata - Object info (fields, relationshipName, etc.).
 * @param layout - Layout response (sections, layoutItems, layoutComponents).
 * @returns Array of field API names (e.g. ["Name", "OwnerId", "Owner", "CreatedDate"]).
 */
export function extractFieldsFromLayout(
	objectMetadata: ObjectInfoResult,
	layout: LayoutResponse,
): string[] {
	const [optionalFields] = calculateFieldsToFetch(objectMetadata, layout, false);
	return optionalFields;
}

export async function getLayout(
	objectApiName: string,
	recordTypeId: string = DEFAULT_RECORD_TYPE_ID,
): Promise<LayoutResponse> {
	const params = new URLSearchParams({
		layoutType: "Full",
		mode: "View",
		recordTypeId,
	});
	return fetchAndValidate(
		() => uiApiClient.get(`/layout/${safeEncodePath(objectApiName)}?${params.toString()}`),
		{
			schema: LayoutResponseSchema,
			errorContext: `layout for ${objectApiName}`,
		},
	);
}

export interface RecordDetailResult {
	layout: LayoutResponse;
	record: GraphQLRecordNode;
	objectMetadata: ObjectInfoResult;
}

/**
 * Converts layout-derived optionalFields (field API names) to Column[] for GraphQL node selection.
 * Uses unqualified names (no entity prefix) so the GraphQL query matches UI API shape.
 * Other Column fields (label, searchable, sortable) are only required by the type; GraphQL selection uses fieldApiName only.
 */
function optionalFieldsToColumns(optionalFields: string[]): Column[] {
	return optionalFields.map((fieldApiName) => ({
		fieldApiName,
		label: "",
		searchable: false,
		sortable: false,
	}));
}

export async function getRecordDetail(
	objectApiName: string,
	recordId: string,
	recordTypeId: string = DEFAULT_RECORD_TYPE_ID,
): Promise<RecordDetailResult> {
	const layout = await getLayout(objectApiName, recordTypeId);
	const objectMetadata = await objectInfoService.getObjectInfoBatch(objectApiName);
	const firstResult = objectMetadata?.results?.[0]?.result;
	if (!firstResult) {
		throw new Error(`Object metadata not found for ${objectApiName}`);
	}
	// Layout-driven optionalFields (fields shown on the detail layout), not list columns
	const [optionalFields] = calculateFieldsToFetch(firstResult, layout, false);
	const columns = optionalFieldsToColumns(optionalFields);
	const record = await getRecordByIdGraphQL(objectApiName, recordId, columns);
	if (!record) {
		throw new Error(`Record not found: ${recordId}`);
	}
	return { layout, record, objectMetadata: firstResult };
}

export const objectDetailService = {
	extractFieldsFromLayout,
	getLayout,
	getRecordDetail,
};
