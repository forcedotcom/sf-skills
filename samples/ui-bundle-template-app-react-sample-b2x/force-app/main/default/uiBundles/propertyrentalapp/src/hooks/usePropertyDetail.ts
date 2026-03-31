/**
 * Fetches Property__c by id with all related data (images, costs, features, listings)
 * in a single GraphQL query.
 */
import { useState, useCallback } from "react";
import {
	fetchPropertyDetailById,
	fetchListingById,
	type PropertyDetailNode,
} from "@/api/properties/propertyDetailGraphQL";
import {
	useCachedAsyncData,
	clearCacheEntry,
} from "@/features/object-search/hooks/useCachedAsyncData";

export interface PropertyDetailState {
	property: PropertyDetailNode | null;
	loading: boolean;
	error: string | null;
}

const CACHE_KEY_PREFIX = "property-detail";

async function fetchDetail(id: string): Promise<PropertyDetailNode | null> {
	// First try directly as a Property__c ID (common path).
	const detail = await fetchPropertyDetailById(id);
	if (detail) return detail;

	// Fall back: treat as a Property_Listing__c ID and resolve to its Property__c.
	const listing = await fetchListingById(id);
	const propertyId = listing?.Property__c?.value ?? null;
	if (!propertyId) return null;
	return fetchPropertyDetailById(propertyId);
}

export function usePropertyDetail(
	id: string | undefined,
): PropertyDetailState & { refetch: () => void } {
	const [generation, setGeneration] = useState(0);
	const trimmedId = id?.trim() ?? "";
	const cacheKey = `${CACHE_KEY_PREFIX}:${trimmedId}:${generation}`;

	const { data, loading, error } = useCachedAsyncData(
		() => {
			if (!trimmedId) return Promise.resolve(null);
			return fetchDetail(trimmedId);
		},
		[trimmedId, generation],
		{ key: cacheKey },
	);

	const refetch = useCallback(() => {
		clearCacheEntry(cacheKey);
		setGeneration((g) => g + 1);
	}, [cacheKey]);

	return {
		property: data ?? null,
		loading,
		error,
		refetch,
	};
}
