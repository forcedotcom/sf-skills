/**
 * Fetches primary image URL for each property id from search results.
 * Returns a map of propertyId -> imageUrl for use in listing cards.
 */
import { useState, useEffect } from "react";
import { fetchPrimaryImagesByPropertyIds } from "@/api/propertyDetailGraphQL";
import type { SearchResultRecord } from "@/features/global-search/types/search/searchResults.js";

export function getPropertyIdFromRecord(record: {
	fields?: Record<string, { value?: unknown }>;
}): string | null {
	const f = record.fields?.Property__c;
	if (!f || typeof f !== "object") return null;
	const v = (f as { value?: unknown }).value;
	return typeof v === "string" ? v : null;
}

export function usePropertyPrimaryImages(
	results: SearchResultRecord[],
): Record<string, string> & { loading: boolean } {
	const [map, setMap] = useState<Record<string, string>>({});
	const [fetchedKey, setFetchedKey] = useState("");

	const propertyIds = results
		.map((r) => r?.record && getPropertyIdFromRecord(r.record))
		.filter((id): id is string => Boolean(id));
	const idsKey = propertyIds.join(",");
	const loading = idsKey !== "" && idsKey !== fetchedKey;

	useEffect(() => {
		if (propertyIds.length === 0) {
			setMap({});
			setFetchedKey("");
			return;
		}
		let cancelled = false;
		fetchPrimaryImagesByPropertyIds(propertyIds)
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
