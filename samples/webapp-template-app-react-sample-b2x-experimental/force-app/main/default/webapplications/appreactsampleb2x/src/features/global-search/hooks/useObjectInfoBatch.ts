/**
 * useObjectInfoBatch
 *
 * Fetches object metadata (label, labelPlural, fields, etc.) for the given object API names.
 * Uses the shared cache in objectInfoService so List, Home, and Detail views reuse one request.
 */

import { useState, useEffect, useRef } from "react";
import { objectInfoService } from "../api/objectInfoService";
import type { ObjectInfoResult } from "../types/objectInfo/objectInfo";

export interface UseObjectInfoBatchResult {
	/** Object metadata in the same order as the requested objectApiNames. */
	objectInfos: ObjectInfoResult[];
	loading: boolean;
	error: string | null;
}

/**
 * Fetches batch object info for the given object API names. Results are cached;
 * multiple callers (List, Home, Detail) share the same request.
 *
 * @param objectApiNames - Array of object API names (e.g. OBJECT_API_NAMES)
 * @returns objectInfos (same order as input), loading, error
 */
export function useObjectInfoBatch(objectApiNames: string[]): UseObjectInfoBatchResult {
	const [state, setState] = useState<UseObjectInfoBatchResult>({
		objectInfos: [],
		loading: objectApiNames.length > 0,
		error: null,
	});
	const isCancelled = useRef(false);
	// Derive a stable primitive from the array so the effect dependency doesn't
	// change on every render. A new array reference (even with identical contents)
	// would otherwise trigger the effect on every render, causing an infinite loop.
	const namesKey = objectApiNames.filter(Boolean).join(",");

	useEffect(() => {
		isCancelled.current = false;
		// Re-derive the array inside the effect from the stable key rather than
		// closing over objectApiNames directly, which would require it in the dep
		// array and reintroduce the infinite loop.
		const names = namesKey ? namesKey.split(",") : [];
		if (names.length === 0) {
			queueMicrotask(() => setState({ objectInfos: [], loading: false, error: null }));
			return;
		}
		queueMicrotask(() => setState((s) => ({ ...s, loading: true, error: null })));
		objectInfoService
			.getObjectInfoBatch(namesKey)
			.then((res) => {
				if (isCancelled.current) return;
				const objectInfos = names
					.map((apiName) => res.results?.find((r) => r.result?.ApiName === apiName)?.result)
					.filter((r) => r != null) as ObjectInfoResult[];
				setState({ objectInfos, loading: false, error: null });
			})
			.catch((err) => {
				if (isCancelled.current) return;
				setState({
					objectInfos: [],
					loading: false,
					error: err instanceof Error ? err.message : (err as string),
				});
			});
		return () => {
			isCancelled.current = true;
		};
	}, [namesKey]);

	return state;
}
