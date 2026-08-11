/**
 * Caches and serves distinct picklist values fetched via the GraphQL
 * aggregate API. The cache key is `${objectName}.${fieldName}`; entries
 * persist for the lifetime of the page so repeated mounts of the same
 * picklist filter share the same response.
 *
 * Pass `null` to short-circuit the fetch (e.g. when inline options are
 * available on the filter config).
 */

import { useEffect, useState } from "react";
import { fetchDistinctValues, type PicklistOption } from "../api/distinctValuesService";

const cache = new Map<string, PicklistOption[]>();
const inflight = new Map<string, Promise<PicklistOption[]>>();

interface DistinctValuesQuery {
	objectName: string;
	fieldName: string;
}

export function useDistinctValues(query: DistinctValuesQuery | null): PicklistOption[] | null {
	const cacheKey = query ? `${query.objectName}.${query.fieldName}` : null;
	const [options, setOptions] = useState<PicklistOption[] | null>(() =>
		cacheKey ? (cache.get(cacheKey) ?? null) : null,
	);

	useEffect(() => {
		if (!query || !cacheKey) return;
		const cached = cache.get(cacheKey);
		if (cached) {
			setOptions(cached);
			return;
		}
		let cancelled = false;
		const existing = inflight.get(cacheKey);
		const promise =
			existing ??
			fetchDistinctValues(query.objectName, query.fieldName).then((result) => {
				cache.set(cacheKey, result);
				inflight.delete(cacheKey);
				return result;
			});
		if (!existing) inflight.set(cacheKey, promise);
		promise
			.then((result) => {
				if (!cancelled) setOptions(result);
			})
			.catch((err: unknown) => {
				inflight.delete(cacheKey);
				console.error(`Failed to fetch distinct values for ${cacheKey}:`, err);
			});
		return () => {
			cancelled = true;
		};
	}, [cacheKey, query]);

	return options;
}
