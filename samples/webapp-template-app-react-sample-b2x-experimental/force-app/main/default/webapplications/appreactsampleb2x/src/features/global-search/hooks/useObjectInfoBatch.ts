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

	useEffect(() => {
		isCancelled.current = false;
		const names = objectApiNames.filter(Boolean);
		if (names.length === 0) {
			setState({ objectInfos: [], loading: false, error: null });
			return;
		}
		setState((s) => ({ ...s, loading: true, error: null }));
		objectInfoService
			.getObjectInfoBatch(names.join(","))
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
	}, [objectApiNames.join(",")]);

	return state;
}
