import type { ReactNode } from "react";
import {
	Pagination,
	PaginationContent,
	PaginationItem,
	PaginationPrevious,
	PaginationNext,
} from "../../../components/ui/pagination";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../components/ui/select";
import { Label } from "../../../components/ui/label";
import { Button } from "../../../components/ui/button";

/** Shared props: pagination state is from useObjectSearchParams (synced to URL). */
interface PaginationControlsBase {
	pageSize: number;
	pageSizeOptions: readonly number[];
	onPageSizeChange: (newPageSize: number) => void;
	disabled?: boolean;
}

/** Default mode: Previous, Page N, Next (cursor-based, state in URL). */
interface PaginationControlsDefaultProps extends PaginationControlsBase {
	variant?: "default";
	pageIndex: number;
	hasNextPage: boolean;
	hasPreviousPage: boolean;
	onNextPage: () => void;
	onPreviousPage: () => void;
}

/** Load More mode: optional page size + Load More button (or custom slot). */
interface PaginationControlsLoadMoreProps extends PaginationControlsBase {
	variant: "loadMore";
	hasNextPage: boolean;
	onLoadMore: () => void;
	loadMoreLoading?: boolean;
	/** Custom content for load-more (e.g. custom button). If not set, renders default Load More button. */
	loadMoreSlot?: ReactNode;
}

export type PaginationControlsProps =
	| PaginationControlsDefaultProps
	| PaginationControlsLoadMoreProps;

function isLoadMoreProps(props: PaginationControlsProps): props is PaginationControlsLoadMoreProps {
	return props.variant === "loadMore";
}

export default function PaginationControls(props: PaginationControlsProps) {
	const { pageSize, pageSizeOptions, onPageSizeChange, disabled = false } = props;

	const handlePageSizeChange = (newValue: string) => {
		const newSize = parseInt(newValue, 10);
		if (!isNaN(newSize) && newSize !== pageSize) {
			onPageSizeChange(newSize);
		}
	};

	const pageSizeBlock = (
		<div
			className="flex justify-center sm:justify-start items-center gap-2 shrink-0"
			role="group"
			aria-label="Page size selector"
		>
			<Label htmlFor="page-size-select" className="text-sm font-normal whitespace-nowrap">
				Results per page:
			</Label>
			<Select value={pageSize.toString()} onValueChange={handlePageSizeChange} disabled={disabled}>
				<SelectTrigger
					id="page-size-select"
					className="w-16"
					aria-label="Select number of results per page"
				>
					<SelectValue />
				</SelectTrigger>
				<SelectContent>
					{pageSizeOptions.map((size) => (
						<SelectItem key={size} value={size.toString()}>
							{size}
						</SelectItem>
					))}
				</SelectContent>
			</Select>
		</div>
	);

	if (isLoadMoreProps(props)) {
		const { hasNextPage, onLoadMore, loadMoreLoading = false, loadMoreSlot } = props;
		return (
			<div className="w-full grid grid-cols-1 sm:grid-cols-2 items-center justify-center gap-4 py-2">
				{pageSizeBlock}
				<div className="flex justify-center sm:justify-end">
					{loadMoreSlot !== undefined ? (
						loadMoreSlot
					) : hasNextPage ? (
						<Button
							onClick={onLoadMore}
							disabled={loadMoreLoading}
							aria-label={loadMoreLoading ? "Loading..." : "Load More"}
						>
							{loadMoreLoading ? "Loading..." : "Load More"}
						</Button>
					) : null}
				</div>
			</div>
		);
	}

	const { pageIndex, hasNextPage, hasPreviousPage, onNextPage, onPreviousPage } = props;
	const currentPage = pageIndex + 1;
	const prevDisabled = disabled || !hasPreviousPage;
	const nextDisabled = disabled || !hasNextPage;

	return (
		<div className="w-full grid grid-cols-1 sm:grid-cols-2 items-center justify-center gap-4 py-2">
			{pageSizeBlock}
			<Pagination className="w-full mx-0 sm:justify-end">
				<PaginationContent>
					<PaginationItem>
						<PaginationPrevious
							onClick={prevDisabled ? undefined : onPreviousPage}
							aria-disabled={prevDisabled}
							className={prevDisabled ? "pointer-events-none opacity-50" : "cursor-pointer"}
						/>
					</PaginationItem>
					<PaginationItem>
						<span
							className="min-w-16 text-center text-sm text-muted-foreground px-2"
							aria-current="page"
						>
							Page {currentPage}
						</span>
					</PaginationItem>
					<PaginationItem>
						<PaginationNext
							onClick={nextDisabled ? undefined : onNextPage}
							aria-disabled={nextDisabled}
							className={nextDisabled ? "pointer-events-none opacity-50" : "cursor-pointer"}
						/>
					</PaginationItem>
				</PaginationContent>
			</Pagination>
		</div>
	);
}
