import { useState, useMemo, useEffect, useRef } from "react";

export interface PageInfo {
	hasNextPage?: boolean;
	endCursor?: string;
}

/** GraphQL-style list result; edges may have optional or null node. */
export interface CursorBasedData<T> {
	edges?: Array<{ node?: T | null } | null>;
	pageInfo?: PageInfo;
}

export interface UseCursorBasedAccumulationOptions<T> {
	/** GraphQL-style result with edges and pageInfo. */
	data: CursorBasedData<T> | undefined;
	loading: boolean;
	/** True when we are on the first page (no cursor set). */
	isFirstPage: boolean;
	/** Callback to request the next page with the given cursor. */
	goToNextPage: (cursor: string) => void;
	/** When these values change, accumulated items are cleared (e.g. query/filters changed). */
	resetDeps: unknown[];
}

export interface UseCursorBasedAccumulationReturn<T> {
	/** All items accumulated so far (first page + loaded more pages). */
	accumulatedItems: T[];
	/** True when a "load more" request is in flight. */
	loadMoreLoading: boolean;
	/** Whether there is a next page. */
	hasNextPage: boolean;
	/** End cursor for the current page (for loading next). */
	endCursor: string | undefined;
	/** Call to load the next page. No-op if no cursor or already loading. */
	onLoadMore: () => void;
}

/**
 * Manages cursor-based "Load More" pagination: accumulates nodes from the first
 * page and each subsequent page, resets when query/filters change, and exposes
 * a single onLoadMore action. Use with LoadMoreButton for a consistent UX across
 * search pages.
 */
export function useCursorBasedAccumulation<T>({
	data,
	loading,
	isFirstPage,
	goToNextPage,
	resetDeps,
}: UseCursorBasedAccumulationOptions<T>): UseCursorBasedAccumulationReturn<T> {
	const [accumulatedItems, setAccumulatedItems] = useState<T[]>([]);

	const currentPageNodes = useMemo(
		() =>
			(data?.edges ?? []).reduce<T[]>((acc, edge) => {
				if (edge?.node != null) acc.push(edge.node);
				return acc;
			}, []),
		[data?.edges],
	);

	// Reset accumulated when query/filters change.
	useEffect(() => {
		setAccumulatedItems([]);
	}, resetDeps);

	const prevLoadingRef = useRef(loading);
	useEffect(() => {
		const justFinishedLoading = prevLoadingRef.current && !loading;
		prevLoadingRef.current = loading;

		if (currentPageNodes.length === 0 && !loading) {
			setAccumulatedItems([]);
			return;
		}
		if (isFirstPage) {
			if (!loading) setAccumulatedItems(currentPageNodes);
		} else {
			if (justFinishedLoading) {
				setAccumulatedItems((prev) => [...prev, ...currentPageNodes]);
			}
		}
	}, [currentPageNodes, isFirstPage, loading]);

	const hasNextPage = data?.pageInfo?.hasNextPage ?? false;
	const endCursor = data?.pageInfo?.endCursor;
	const loadMoreLoading = loading && !isFirstPage;

	const onLoadMore = () => {
		if (loadMoreLoading || !endCursor) return;
		goToNextPage(endCursor);
	};

	return {
		accumulatedItems,
		loadMoreLoading,
		hasNextPage,
		endCursor,
		onLoadMore,
	};
}
