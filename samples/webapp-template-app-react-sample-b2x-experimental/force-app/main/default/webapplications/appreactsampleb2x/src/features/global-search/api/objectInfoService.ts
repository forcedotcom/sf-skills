import { uiApiClient } from "@salesforce/webapp-experimental/api";
import type { Filter } from "../types/filters/filters";
import { FilterArraySchema } from "../types/filters/filters";
import type { PicklistValue } from "../types/filters/picklist";
import type { ObjectInfoBatchResponse } from "../types/objectInfo/objectInfo";
import { fetchAndValidate, safeEncodePath } from "../utils/apiUtils";
import { queryForObjectInfos, queryForPicklistValues } from "./objectInfoGraphQLService";
import {
	graphQLObjectInfosToBatchResponse,
	extractPicklistValuesFromGraphQLObjectInfo,
} from "../utils/graphQLObjectInfoAdapter";

/**
 * Object info and search service.
 *
 * - getObjectInfoBatch / getPicklistValues: GraphQL (objectInfoGraphQLService).
 * - getObjectListFilters: REST (search-info).
 * Hooks use this service; components do not call it directly.
 *
 * @module api/objectInfoService
 */

/** Cache key: sorted, comma-joined object API names. */
function getObjectInfoBatchCacheKey(objectApiNames: string): string {
	const names = objectApiNames
		.split(",")
		.map((s) => s.trim())
		.filter(Boolean);
	return [...names].sort().join(",");
}

const objectInfoBatchCache = new Map<string, ObjectInfoBatchResponse>();
const objectInfoBatchInFlight = new Map<string, Promise<ObjectInfoBatchResponse>>();

export async function getObjectInfoBatch(objectApiNames: string): Promise<ObjectInfoBatchResponse> {
	const names = objectApiNames
		.split(",")
		.map((s) => s.trim())
		.filter(Boolean);
	if (names.length === 0) {
		return { results: [] };
	}
	const key = getObjectInfoBatchCacheKey(objectApiNames);
	const cached = objectInfoBatchCache.get(key);
	if (cached) return Promise.resolve(cached);
	const inFlight = objectInfoBatchInFlight.get(key);
	if (inFlight) return inFlight;
	const promise = (async () => {
		try {
			const response = await queryForObjectInfos(names);
			const nodes = response?.uiapi?.objectInfos ?? [];
			const result = graphQLObjectInfosToBatchResponse(nodes, names);
			objectInfoBatchCache.set(key, result);
			return result;
		} finally {
			objectInfoBatchInFlight.delete(key);
		}
	})();
	objectInfoBatchInFlight.set(key, promise);
	return promise;
}

export async function getObjectListFilters(objectApiName: string): Promise<Filter[]> {
	return fetchAndValidate(
		() => uiApiClient.get(`/search-info/${safeEncodePath(objectApiName)}/filters`),
		{
			schema: FilterArraySchema,
			errorContext: `filters for ${objectApiName}`,
			extractData: (data: unknown) => {
				if (!data) return [];
				return Array.isArray(data) ? data : (data as { filters?: unknown }).filters || [];
			},
		},
	);
}

export async function getPicklistValues(
	objectApiName: string,
	fieldName: string,
	recordTypeId: string = "012000000000000AAA",
): Promise<PicklistValue[]> {
	const response = await queryForPicklistValues([
		{ apiName: objectApiName, fieldNames: [fieldName] },
	]);
	const nodes = response?.uiapi?.objectInfos ?? [];
	const node = nodes[0];
	if (!node) return [];
	return extractPicklistValuesFromGraphQLObjectInfo(node, fieldName, recordTypeId);
}

export const objectInfoService = {
	getObjectInfoBatch,
	getObjectListFilters,
	getPicklistValues,
};
