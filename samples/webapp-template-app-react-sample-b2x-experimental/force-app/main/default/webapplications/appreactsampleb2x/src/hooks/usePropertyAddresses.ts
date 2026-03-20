/**
 * Fetches Address__c for each property id from search results.
 * Returns propertyId -> address for display on listing cards.
 */
import { useState, useEffect } from "react";
import { fetchPropertyAddresses } from "@/api/propertyDetailGraphQL";
import { getPropertyIdFromRecord } from "@/hooks/usePropertyPrimaryImages";
import type { SearchResultRecord } from "@/features/global-search/types/search/searchResults.js";

export function usePropertyAddresses(results: SearchResultRecord[]): Record<string, string> {
	const [map, setMap] = useState<Record<string, string>>({});

	const propertyIds = results
		.map((r) => r?.record && getPropertyIdFromRecord(r.record))
		.filter((id): id is string => Boolean(id));

	useEffect(() => {
		if (propertyIds.length === 0) {
			setMap({});
			return;
		}
		let cancelled = false;
		fetchPropertyAddresses([...new Set(propertyIds)])
			.then((next) => {
				if (!cancelled) setMap(next);
			})
			.catch(() => {
				if (!cancelled) setMap({});
			});
		return () => {
			cancelled = true;
		};
	}, [propertyIds.join(",")]);

	return map;
}
