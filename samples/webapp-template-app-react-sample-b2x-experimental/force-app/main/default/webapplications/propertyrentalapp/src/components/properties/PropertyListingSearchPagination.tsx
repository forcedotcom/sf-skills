/**
 * Pagination controls for Property_Listing__c consumer search (token-based).
 * Replaces feature-react-global-search SearchPagination without pulling in that feature.
 */
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import {
	PAGE_SIZE_OPTIONS,
	getValidPageSize,
	isValidPageSize,
} from "@/utils/propertyListingPaginationUtils";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PropertyListingSearchPaginationProps {
	currentPageToken: string;
	nextPageToken: string | null;
	previousPageToken: string | null;
	hasNextPage?: boolean;
	hasPreviousPage?: boolean;
	pageSize: number;
	onPageChange: (newPageToken: string, direction?: "next" | "prev" | "first") => void;
	onPageSizeChange: (newPageSize: number) => void;
}

export default function PropertyListingSearchPagination({
	currentPageToken,
	nextPageToken,
	previousPageToken,
	hasNextPage = false,
	hasPreviousPage = false,
	pageSize,
	onPageChange,
	onPageSizeChange,
}: PropertyListingSearchPaginationProps) {
	const validPageSize = getValidPageSize(pageSize);

	const currentPageTokenNum = parseInt(currentPageToken, 10) || 0;
	const currentPage = currentPageTokenNum + 1;

	const canGoPrevious = Boolean(hasPreviousPage);
	const canGoNext = Boolean(hasNextPage && nextPageToken != null);

	const handlePrevious = () => {
		if (canGoPrevious) {
			onPageChange(previousPageToken ?? "", "prev");
		}
	};

	const handleNext = () => {
		if (canGoNext && nextPageToken != null) {
			onPageChange(nextPageToken, "next");
		}
	};

	const handlePageSizeChange = (newPageSize: string) => {
		const newSize = parseInt(newPageSize, 10);
		if (!isNaN(newSize) && isValidPageSize(newSize) && newSize !== validPageSize) {
			onPageSizeChange(newSize);
			onPageChange("0", "first");
		}
	};

	return (
		<nav
			className="flex w-full flex-row flex-wrap items-center justify-between gap-4 py-2"
			aria-label="Search results pagination"
		>
			<div
				className="flex shrink-0 items-center gap-2"
				role="group"
				aria-label="Page size selector"
			>
				<Label htmlFor="page-size-select" className="whitespace-nowrap text-sm font-normal">
					Results per page:
				</Label>
				<Select value={validPageSize.toString()} onValueChange={handlePageSizeChange}>
					<SelectTrigger id="page-size-select" className="w-[70px]" aria-label="Results per page">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{PAGE_SIZE_OPTIONS.map((option) => (
							<SelectItem key={option.value} value={option.value}>
								{option.label}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
			</div>

			<div className="flex shrink-0 items-center gap-1" role="group" aria-label="Page navigation">
				<Button
					type="button"
					variant="outline"
					size="sm"
					disabled={!canGoPrevious}
					onClick={handlePrevious}
					aria-label={
						canGoPrevious
							? `Go to previous page (Page ${currentPage - 1})`
							: "Previous page (disabled)"
					}
				>
					<ChevronLeft className="size-4" aria-hidden />
					Previous
				</Button>
				<span
					className="min-w-[4rem] px-2 text-center text-sm text-muted-foreground"
					aria-current="page"
					aria-label={`Page ${currentPage}, current page`}
				>
					Page {currentPage}
				</span>
				<Button
					type="button"
					variant="outline"
					size="sm"
					disabled={!canGoNext}
					onClick={handleNext}
					aria-label={
						canGoNext ? `Go to next page (Page ${currentPage + 1})` : "Next page (disabled)"
					}
				>
					Next
					<ChevronRight className="size-4" aria-hidden />
				</Button>
			</div>
		</nav>
	);
}
