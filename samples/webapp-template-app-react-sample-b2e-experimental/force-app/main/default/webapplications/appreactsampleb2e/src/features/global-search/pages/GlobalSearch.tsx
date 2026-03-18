/**
 * GlobalSearch Page Component
 *
 * Main page component for displaying global search results.
 * Uses GraphQL API (useRecordListGraphQL) for list data; results are adapted to the
 * same record shape as before so SearchResultCard and filters/sort/pagination work unchanged.
 *
 * @remarks
 * - Supports single object search (no tabs)
 * - Displays filters panel on the left and results on the right
 * - Pagination uses a cursor stack: we only query forward (first + after) and store endCursor per page;
 *   Previous re-queries using the stored cursor for the previous page so both Next and Previous work.
 */
import { useMemo, useState, useCallback, useEffect, useRef } from "react";
import { useParams } from "react-router";
import { OBJECT_API_NAMES, DEFAULT_PAGE_SIZE } from "../constants";
import { useObjectListMetadata } from "../hooks/useObjectSearchData";
import { useObjectInfoBatch } from "../hooks/useObjectInfoBatch";
import { useRecordListGraphQL } from "../hooks/useRecordListGraphQL";
import FiltersPanel from "../components/filters/FiltersPanel";
import SearchHeader from "../components/search/SearchHeader";
import SearchResultsPanel from "../components/search/SearchResultsPanel";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";
import type { FilterCriteria } from "../types/filters/filters";
import type { SearchResultRecord } from "../types/search/searchResults";
import { graphQLNodeToSearchResultRecordData } from "../utils/graphQLRecordAdapter";

const EMPTY_HIGHLIGHT = { fields: {}, snippet: null };
const EMPTY_SEARCH_INFO = { isPromoted: false, isSpellCorrected: false };

export default function GlobalSearch() {
	const { query } = useParams<{ query: string }>();

	const objectApiName = OBJECT_API_NAMES[0];

	const [searchPageSize, setSearchPageSize] = useState(DEFAULT_PAGE_SIZE);
	const [afterCursor, setAfterCursor] = useState<string | null>(null);
	const [pageIndex, setPageIndex] = useState(0);
	/** Cursor stack: cursorStack[i] is the `after` value that returns page i. cursorStack[0] = null (first page). */
	const [cursorStack, setCursorStack] = useState<(string | null)[]>([null]);
	const [appliedFilters, setAppliedFilters] = useState<FilterCriteria[]>([]);
	const [sortBy, setSortBy] = useState("Name");

	const decodedQuery = useMemo(() => {
		if (!query) return "";
		try {
			return decodeURIComponent(query);
		} catch (e) {
			return query;
		}
	}, [query]);

	const isBrowseAll = decodedQuery === "browse__all";
	const searchQuery = isBrowseAll ? "" : decodedQuery.trim();

	// Reset pagination when the URL search query changes so we don't use an old cursor with a new result set
	useEffect(() => {
		setAfterCursor(null);
		setPageIndex(0);
		setCursorStack([null]);
	}, [query]);

	const listMeta = useObjectListMetadata(objectApiName);
	const { objectInfos } = useObjectInfoBatch([...OBJECT_API_NAMES]);
	const labelPlural = (objectInfos[0]?.labelPlural as string | undefined) ?? "records";
	const {
		edges,
		pageInfo,
		loading: resultsLoading,
		error: resultsError,
	} = useRecordListGraphQL({
		objectApiName,
		first: searchPageSize,
		after: afterCursor,
		filters: appliedFilters,
		sortBy: sortBy === "relevance" ? "Name" : sortBy,
		searchQuery: searchQuery || undefined,
		columns: listMeta.columns,
		columnsLoading: listMeta.loading,
		columnsError: listMeta.error,
	});

	// Store endCursor for the next page so we can re-query when user clicks Next; also enables Previous via stack.
	// Only update when not loading so a stale response cannot write a cursor into the wrong stack index (e.g. after rapid Next clicks).
	useEffect(() => {
		if (resultsLoading) return;
		const cursor = pageInfo?.endCursor ?? null;
		if (cursor == null) return;
		setCursorStack((prev) => {
			const next = [...prev];
			next[pageIndex + 1] = cursor;
			return next;
		});
	}, [resultsLoading, pageInfo?.endCursor, pageIndex]);

	const results: SearchResultRecord[] = useMemo(
		() =>
			(edges ?? []).map((edge) => ({
				record: graphQLNodeToSearchResultRecordData(
					edge?.node as Record<string, unknown>,
					objectApiName,
				),
				highlightInfo: EMPTY_HIGHLIGHT,
				searchInfo: EMPTY_SEARCH_INFO,
			})),
		[edges, objectApiName],
	);

	const nextPageToken = pageInfo?.endCursor ?? null;
	/** Entry cursor for the previous page; used when user clicks Previous to re-query with after=cursorStack[pageIndex-1]. */
	const previousPageToken = pageIndex > 0 ? (cursorStack[pageIndex - 1] ?? null) : null;
	const hasNextPage = pageInfo?.hasNextPage === true;
	const hasPreviousPage = pageIndex > 0;
	const currentPageToken = pageIndex.toString();

	const cursorStackRef = useRef(cursorStack);
	const pageIndexRef = useRef(pageIndex);
	cursorStackRef.current = cursorStack;
	pageIndexRef.current = pageIndex;

	const canRenderFilters =
		!listMeta.loading && listMeta.filters !== undefined && listMeta.picklistValues !== undefined;

	const handleApplyFilters = useCallback((filterCriteria: FilterCriteria[]) => {
		setAppliedFilters(filterCriteria);
		setAfterCursor(null);
		setPageIndex(0);
		setCursorStack([null]);
	}, []);

	const handlePageChange = useCallback(
		(newPageToken: string, direction?: "next" | "prev" | "first") => {
			if (direction === "first" || newPageToken === "0") {
				setAfterCursor(null);
				setPageIndex(0);
			} else if (direction === "prev") {
				const idx = pageIndexRef.current;
				const stack = cursorStackRef.current;
				const prevCursor = idx > 0 ? (stack[idx - 1] ?? null) : null;
				setAfterCursor(prevCursor);
				setPageIndex((prev) => Math.max(0, prev - 1));
			} else {
				setAfterCursor(newPageToken);
				setPageIndex((prev) => prev + 1);
			}
			window.scrollTo({ top: 0, behavior: "smooth" });
		},
		[],
	);

	const handlePageSizeChange = useCallback((newPageSize: number) => {
		setSearchPageSize(newPageSize);
		setAfterCursor(null);
		setPageIndex(0);
		setCursorStack([null]);
		window.scrollTo({ top: 0, behavior: "smooth" });
	}, []);

	const handleSortByChange = useCallback((newSortBy: string) => {
		setSortBy(newSortBy);
		setAfterCursor(null);
		setPageIndex(0);
		setCursorStack([null]);
		window.scrollTo({ top: 0, behavior: "smooth" });
	}, []);

	return (
		<main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
			<SearchHeader query={decodedQuery} isBrowseAll={isBrowseAll} labelPlural={labelPlural} />

			<div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
				<aside className="lg:col-span-1" aria-label="Filters panel">
					{canRenderFilters ? (
						<FiltersPanel
							filters={listMeta.filters}
							picklistValues={listMeta.picklistValues}
							loading={listMeta.loading}
							objectApiName={objectApiName}
							onApplyFilters={handleApplyFilters}
						/>
					) : (
						<Card className="w-full" role="region" aria-label="Filters panel">
							<CardHeader>
								<CardTitle>Filters</CardTitle>
							</CardHeader>
							<CardContent
								className="space-y-4"
								role="status"
								aria-live="polite"
								aria-label="Loading filters"
							>
								<span className="sr-only">Loading filters</span>
								{[1, 2, 3].map((i) => (
									<div key={i} className="space-y-2" aria-hidden="true">
										<Skeleton className="h-4 w-24" />
										<Skeleton className="h-9 w-full" />
									</div>
								))}
							</CardContent>
						</Card>
					)}
				</aside>

				<section className="lg:col-span-3" aria-label="Search results">
					<SearchResultsPanel
						objectApiName={objectApiName}
						columns={listMeta.columns}
						results={results}
						columnsLoading={listMeta.loading}
						resultsLoading={resultsLoading}
						columnsError={listMeta.error}
						resultsError={resultsError}
						currentPageToken={currentPageToken}
						nextPageToken={nextPageToken}
						previousPageToken={previousPageToken}
						hasNextPage={hasNextPage}
						hasPreviousPage={hasPreviousPage}
						pageSize={searchPageSize}
						sortBy={sortBy}
						onPageChange={handlePageChange}
						onPageSizeChange={handlePageSizeChange}
						onSortByChange={handleSortByChange}
					/>
				</section>
			</div>
		</main>
	);
}
