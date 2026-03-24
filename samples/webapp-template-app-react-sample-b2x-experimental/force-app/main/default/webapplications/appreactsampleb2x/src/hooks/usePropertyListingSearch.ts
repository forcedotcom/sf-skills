/**
 * Property Listing search via GraphQL. Optional text, price range, and bedrooms filters.
 */
import { useState, useEffect, useRef, useCallback } from "react";
import {
	queryPropertyListingsGraphQL,
	type PropertyListingFilters,
} from "@/api/propertyListingGraphQL";
import type { SearchResultRecord } from "@/features/global-search/types/search/searchResults.js";

export function usePropertyListingSearch(
	searchQuery: string,
	pageSize: number,
	pageToken: string,
	filters?: PropertyListingFilters,
) {
	const [results, setResults] = useState<SearchResultRecord[]>([]);
	const [nextPageToken, setNextPageToken] = useState<string | null>(null);
	const [previousPageToken, setPreviousPageToken] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const abortControllerRef = useRef<AbortController | null>(null);
	const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	const fetchResults = useCallback(async () => {
		const ac = new AbortController();
		abortControllerRef.current = ac;
		setLoading(true);
		setError(null);
		try {
			const afterCursor = pageToken === "0" || pageToken === "" ? null : pageToken;
			const result = await queryPropertyListingsGraphQL(
				searchQuery,
				pageSize,
				afterCursor,
				ac.signal,
				filters,
			);
			if (ac.signal.aborted) return;
			setResults(result.records);
			setNextPageToken(result.nextPageToken);
			setPreviousPageToken(result.previousPageToken);
		} catch (err) {
			if (ac.signal.aborted || (err instanceof Error && err.name === "AbortError")) return;
			setError(err instanceof Error ? err.message : "Unable to load property listings");
			setResults([]);
			setNextPageToken(null);
			setPreviousPageToken(null);
		} finally {
			if (!ac.signal.aborted) setLoading(false);
		}
	}, [searchQuery, pageSize, pageToken, filters]);

	useEffect(() => {
		if (debounceRef.current) {
			clearTimeout(debounceRef.current);
			debounceRef.current = null;
		}
		if (abortControllerRef.current) {
			abortControllerRef.current.abort();
		}

		// When on first page, debounce to avoid firing on every keystroke
		if (pageToken === "0" || pageToken === "") {
			debounceRef.current = setTimeout(() => fetchResults(), 300);
		} else {
			fetchResults();
		}
		return () => {
			if (debounceRef.current) clearTimeout(debounceRef.current);
			abortControllerRef.current?.abort();
		};
	}, [searchQuery, pageSize, pageToken, fetchResults]);

	return {
		results,
		nextPageToken,
		previousPageToken,
		currentPageToken: pageToken === "" ? "0" : pageToken,
		resultsLoading: loading,
		resultsError: error,
	};
}
