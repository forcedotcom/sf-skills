/**
 * Fetches amenities (feature descriptions) for each property in search results.
 * Returns a map of propertyId -> "Amenity 1 | Amenity 2 | ..." for use in listing cards.
 */
import { useState, useEffect } from "react";
import { fetchFeaturesByPropertyId } from "@/api/propertyDetailGraphQL";
import { getPropertyIdFromRecord } from "@/hooks/usePropertyPrimaryImages";
import type { SearchResultRecord } from "@/features/global-search/types/search/searchResults.js";

const AMENITIES_SEPARATOR = " | ";

export function usePropertyListingAmenities(
	results: SearchResultRecord[],
): Record<string, string> & { loading: boolean } {
	const [map, setMap] = useState<Record<string, string>>({});
	const [loading, setLoading] = useState(false);

	const propertyIds = results
		.map((r) => r?.record && getPropertyIdFromRecord(r.record))
		.filter((id): id is string => Boolean(id));
	const uniqueIds = [...new Set(propertyIds)];

	useEffect(() => {
		if (uniqueIds.length === 0) {
			setMap({});
			return;
		}
		let cancelled = false;
		setLoading(true);
		Promise.all(uniqueIds.map((id) => fetchFeaturesByPropertyId(id)))
			.then((featuresPerProperty) => {
				if (cancelled) return;
				const next: Record<string, string> = {};
				uniqueIds.forEach((id, i) => {
					const features = featuresPerProperty[i] ?? [];
					const descriptions = features
						.map((f) => f.description)
						.filter((d): d is string => d != null && d.trim() !== "");
					next[id] = descriptions.join(AMENITIES_SEPARATOR);
				});
				setMap(next);
			})
			.catch(() => {
				if (!cancelled) setMap({});
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});
		return () => {
			cancelled = true;
		};
	}, [uniqueIds.join(",")]);

	return Object.assign(map, { loading });
}
