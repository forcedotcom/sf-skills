/**
 * Fetches Address__c for each property id from search results.
 * Returns propertyId -> address for display on listing cards.
 */
import { useState, useEffect } from "react";
import { fetchPropertyAddresses } from "@/api/propertyDetailGraphQL";
import { getPropertyIdFromRecord } from "@/hooks/usePropertyPrimaryImages";
import type { SearchResultRecord } from "@/features/global-search/types/search/searchResults.js";

export function usePropertyAddresses(
	results: SearchResultRecord[],
): Record<string, string> & { loading: boolean } {
	const [map, setMap] = useState<Record<string, string>>({});
	const [fetchedKey, setFetchedKey] = useState("");

	const propertyIds = results
		.map((r) => r?.record && getPropertyIdFromRecord(r.record))
		.filter((id): id is string => Boolean(id));
	const idsKey = [...new Set(propertyIds)].join(",");
	const loading = idsKey !== "" && idsKey !== fetchedKey;

	useEffect(() => {
		if (idsKey === "") {
			setMap({});
			setFetchedKey("");
			return;
		}
		let cancelled = false;
		fetchPropertyAddresses(idsKey.split(","))
			.then((next) => {
				if (!cancelled) setMap(next);
			})
			.catch(() => {
				if (!cancelled) setMap({});
			})
			.finally(() => {
				if (!cancelled) setFetchedKey(idsKey);
			});
		return () => {
			cancelled = true;
		};
	}, [idsKey]);

	return Object.assign(map, { loading });
}
