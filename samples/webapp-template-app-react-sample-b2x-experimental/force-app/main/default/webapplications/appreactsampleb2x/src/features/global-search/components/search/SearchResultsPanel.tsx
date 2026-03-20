/**
 * SearchResultsPanel Component
 *
 * Displays the search results panel with loading, error, and empty states.
 * Renders a list of SearchResultCard components and pagination controls.
 *
 * @param columns - Array of column definitions for displaying result data
 * @param results - Array of search result records to display
 * @param columnsLoading - Whether column metadata is currently loading
 * @param resultsLoading - Whether search results are currently loading
 * @param columnsError - Error message if column fetch failed
 * @param resultsError - Error message if results fetch failed
 * @param currentPageToken - Current pagination token
 * @param pageSize - Number of results per page
 * @param onPageChange - Callback when pagination changes; second arg optional: "next" | "prev" | "first" (cursor-stack pagination)
 * @param onPageSizeChange - Callback when page size changes
 *
 * @example
 * ```tsx
 * <SearchResultsPanel
 *   columns={columns}
 *   results={results}
 *   columnsLoading={false}
 *   resultsLoading={false}
 *   columnsError={null}
 *   resultsError={null}
 *   currentPageToken="0"
 *   pageSize={25}
 *   onPageChange={(token, direction) => handlePageChange(token, direction)}
 *   onPageSizeChange={(size) => setPageSize(size)}
 * />
 * ```
 */
import { useMemo } from "react";
import { Alert, AlertDescription, AlertTitle } from "../../../../components/ui/alert";
import { Skeleton } from "../../../../components/ui/skeleton";
import { AlertCircle } from "lucide-react";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../components/ui/select";
import { Label } from "../../../../components/ui/label";
import SearchResultCard from "./SearchResultCard";
import SearchPagination from "./SearchPagination";
import type { Column, SearchResultRecord } from "../../types/search/searchResults";
import { getSafeKey } from "../../utils/recordUtils";

interface SearchResultsPanelProps {
	/** API name of the object being searched (e.g. for detail page navigation). */
	objectApiName?: string;
	columns: Column[];
	results: SearchResultRecord[];
	columnsLoading: boolean;
	resultsLoading: boolean;
	columnsError: string | null;
	resultsError: string | null;
	currentPageToken: string;
	nextPageToken: string | null;
	previousPageToken: string | null;
	hasNextPage?: boolean;
	hasPreviousPage?: boolean;
	pageSize: number;
	sortBy: string;
	onPageChange: (newPageToken: string, direction?: "next" | "prev" | "first") => void;
	onPageSizeChange: (newPageSize: number) => void;
	onSortByChange: (newSortBy: string) => void;
}

export default function SearchResultsPanel({
	objectApiName,
	columns,
	results,
	columnsLoading,
	resultsLoading,
	columnsError,
	resultsError,
	currentPageToken,
	nextPageToken,
	previousPageToken,
	hasNextPage = false,
	hasPreviousPage = false,
	pageSize,
	sortBy,
	onPageChange,
	onPageSizeChange,
	onSortByChange,
}: SearchResultsPanelProps) {
	const sortableColumns = useMemo(() => columns.filter(({ sortable }) => sortable), [columns]);

	const validResults = useMemo(
		() => results.filter((record) => record && record.record && record.record.id),
		[results],
	);
	if (columnsError || resultsError) {
		return (
			<Alert variant="destructive" role="alert">
				<AlertCircle className="h-4 w-4" aria-hidden="true" />
				<AlertTitle>Error</AlertTitle>
				<AlertDescription>
					{columnsError || resultsError || "Failed to load search results"}
				</AlertDescription>
			</Alert>
		);
	}

	if (resultsLoading || columnsLoading) {
		return (
			<div
				className="space-y-4"
				role="status"
				aria-live="polite"
				aria-label="Loading search results"
			>
				<span className="sr-only">Loading search results</span>
				{[1, 2, 3].map((i) => (
					<div key={i} className="border rounded-lg p-6" aria-hidden="true">
						<Skeleton className="h-6 w-3/4 mb-4" />
						<Skeleton className="h-4 w-full mb-2" />
						<Skeleton className="h-4 w-2/3" />
					</div>
				))}
			</div>
		);
	}

	if (results.length === 0) {
		return (
			<div className="text-center py-12" role="status" aria-live="polite">
				<p className="text-lg mb-2">No results found</p>
				<p className="text-sm">Try adjusting your search query or filters</p>
			</div>
		);
	}

	return (
		<>
			{sortableColumns.length > 0 && (
				<div
					className="mb-6 flex items-center gap-2 justify-end"
					role="group"
					aria-label="Sort options"
				>
					<Label htmlFor="sort-by-select" className="text-sm font-normal whitespace-nowrap">
						Sort by:
					</Label>
					<Select value={sortBy || ""} onValueChange={onSortByChange}>
						<SelectTrigger
							id="sort-by-select"
							className="w-[200px]"
							aria-label="Sort search results by field"
						>
							<SelectValue placeholder="Select field..." />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="relevance">Relevance</SelectItem>
							{sortableColumns.map((column) => (
								<SelectItem key={column.fieldApiName} value={column.fieldApiName}>
									{column.label}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				</div>
			)}

			<div className="space-y-4 mb-6" role="list" aria-label="Search results list">
				{validResults.map((record, index) => {
					const recordId = record.record.id;
					const safeKey = getSafeKey(recordId, index);
					return (
						<div key={safeKey} role="listitem">
							<SearchResultCard
								record={record.record}
								columns={columns}
								objectApiName={objectApiName}
							/>
						</div>
					);
				})}
			</div>

			<SearchPagination
				currentPageToken={currentPageToken}
				nextPageToken={nextPageToken}
				previousPageToken={previousPageToken}
				hasNextPage={hasNextPage}
				hasPreviousPage={hasPreviousPage}
				pageSize={pageSize}
				onPageChange={onPageChange}
				onPageSizeChange={onPageSizeChange}
			/>
		</>
	);
}
