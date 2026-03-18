import { useState, useRef, useEffect, type Dispatch, type SetStateAction } from "react";

/**
 * Accumulates list pages when the GraphQL hook returns one page at a time.
 * When loading goes from true to false: if afterCursor is null, replaces the list;
 * otherwise appends (load more). Caller must reset accumulated when search/filters/sort change.
 */
export function useAccumulatedListPages<T>(
	edges: Array<{ node?: unknown }>,
	loading: boolean,
	afterCursor: string | null,
	mapNode: (node: unknown) => T,
): [T[], Dispatch<SetStateAction<T[]>>] {
	const [accumulated, setAccumulated] = useState<T[]>([]);
	const prevLoadingRef = useRef(loading);

	useEffect(() => {
		const isFirstPage = afterCursor === null;
		const justFinishedLoading = prevLoadingRef.current && !loading;
		if (justFinishedLoading) {
			const list = edges.map((e) => mapNode(e.node));
			if (isFirstPage) setAccumulated(list);
			else setAccumulated((prev) => [...prev, ...list]);
		}
		prevLoadingRef.current = loading;
	}, [loading, edges, afterCursor, mapNode]);

	return [accumulated, setAccumulated];
}
