import {
	Pagination,
	PaginationContent,
	PaginationEllipsis,
	PaginationItem,
	PaginationLink,
	PaginationNext,
	PaginationPrevious,
} from "../../../../components/ui/pagination";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../components/ui/select";
import { Label } from "../../../../components/ui/label";
import type { KeyboardEvent } from "react";

interface PaginationControlsProps {
	pageIndex: number;
	hasNextPage: boolean;
	hasPreviousPage: boolean;
	pageSize: number;
	pageSizeOptions: readonly number[];
	onNextPage: () => void;
	onPreviousPage: () => void;
	onPageSizeChange: (size: number) => void;
	/**
	 * Total number of pages. When provided (with {@link onGoToPage}) and `> 1`,
	 * the control renders numbered page buttons with ellipsis truncation instead
	 * of a plain "Page N" label. Omit for cursor-style sources where the total
	 * page count is unknown.
	 */
	pageCount?: number;
	/** Jump to a 0-based page. Required to render numbered page buttons. */
	onGoToPage?: (pageIndex: number) => void;
	disabled?: boolean;
	idPrefix?: string;
}

/**
 * Builds the list of page tokens to render: 0-based page numbers plus
 * `"ellipsis"` gap markers. Always shows the first and last page, a window
 * around the current page, and collapses the rest. e.g. for current=5,
 * total=12 → [0, ellipsis, 4, 5, 6, ellipsis, 11].
 */
function getPageTokens(currentIndex: number, pageCount: number): Array<number | "ellipsis"> {
	const SIBLINGS = 1; // pages shown on each side of the current page
	const last = pageCount - 1;
	const pages = new Set<number>([0, last]);
	for (let p = currentIndex - SIBLINGS; p <= currentIndex + SIBLINGS; p++) {
		if (p >= 0 && p <= last) pages.add(p);
	}
	const sorted = [...pages].sort((a, b) => a - b);
	const tokens: Array<number | "ellipsis"> = [];
	let prev = -1;
	for (const p of sorted) {
		if (prev !== -1 && p - prev > 1) tokens.push("ellipsis");
		tokens.push(p);
		prev = p;
	}
	return tokens;
}

export function PaginationControls({
	pageIndex,
	hasNextPage,
	hasPreviousPage,
	pageSize,
	pageSizeOptions,
	onNextPage,
	onPreviousPage,
	onPageSizeChange,
	pageCount,
	onGoToPage,
	disabled = false,
	idPrefix = "page-size",
}: PaginationControlsProps) {
	const handlePageSizeChange = (next: string) => {
		const size = parseInt(next, 10);
		if (!isNaN(size) && size !== pageSize) onPageSizeChange(size);
	};
	const prevDisabled = disabled || !hasPreviousPage;
	const nextDisabled = disabled || !hasNextPage;
	const selectId = `${idPrefix}-select`;

	// Numbered page buttons require both a known page count and a seek callback.
	const showNumberedPages = pageCount != null && pageCount > 1 && onGoToPage != null;

	// The underlying pagination control renders an <a> without an href, so it is
	// not keyboard-operable on its own. Activate it on Enter/Space to match the
	// behaviour of a native button (WCAG 2.2 SC 2.1.1 Keyboard).
	const handleActivationKey = (action: () => void) => (event: KeyboardEvent) => {
		if (event.key === "Enter" || event.key === " ") {
			event.preventDefault();
			action();
		}
	};

	return (
		<div className="w-full grid grid-cols-1 sm:grid-cols-2 items-center gap-4 py-2">
			<div className="flex justify-center sm:justify-start items-center gap-2">
				<Label htmlFor={selectId} className="text-sm font-normal whitespace-nowrap">
					Results per page:
				</Label>
				<Select
					value={pageSize.toString()}
					onValueChange={handlePageSizeChange}
					disabled={disabled}
				>
					<SelectTrigger id={selectId} className="w-16">
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
			<Pagination className="w-full mx-0 sm:justify-end">
				<PaginationContent>
					<PaginationItem>
						<PaginationPrevious
							role="button"
							tabIndex={prevDisabled ? -1 : 0}
							onClick={prevDisabled ? undefined : onPreviousPage}
							onKeyDown={prevDisabled ? undefined : handleActivationKey(onPreviousPage)}
							aria-disabled={prevDisabled}
							className={prevDisabled ? "pointer-events-none opacity-50" : "cursor-pointer"}
						/>
					</PaginationItem>

					{showNumberedPages ? (
						getPageTokens(pageIndex, pageCount).map((token, i) =>
							token === "ellipsis" ? (
								<PaginationItem key={`ellipsis-${i}`}>
									<PaginationEllipsis />
								</PaginationItem>
							) : (
								<PaginationItem key={token}>
									<PaginationLink
										role="button"
										tabIndex={disabled ? -1 : 0}
										isActive={token === pageIndex}
										aria-label={`Go to page ${token + 1}`}
										aria-current={token === pageIndex ? "page" : undefined}
										onClick={disabled ? undefined : () => onGoToPage(token)}
										onKeyDown={disabled ? undefined : handleActivationKey(() => onGoToPage(token))}
										aria-disabled={disabled}
										className={disabled ? "pointer-events-none opacity-50" : "cursor-pointer"}
									>
										{token + 1}
									</PaginationLink>
								</PaginationItem>
							),
						)
					) : (
						<PaginationItem>
							<span className="min-w-16 text-center text-sm text-muted-foreground px-2">
								{pageCount != null && pageCount > 0
									? `Page ${pageIndex + 1} of ${pageCount}`
									: `Page ${pageIndex + 1}`}
							</span>
						</PaginationItem>
					)}

					<PaginationItem>
						<PaginationNext
							role="button"
							tabIndex={nextDisabled ? -1 : 0}
							onClick={nextDisabled ? undefined : onNextPage}
							onKeyDown={nextDisabled ? undefined : handleActivationKey(onNextPage)}
							aria-disabled={nextDisabled}
							className={nextDisabled ? "pointer-events-none opacity-50" : "cursor-pointer"}
						/>
					</PaginationItem>
				</PaginationContent>
			</Pagination>
		</div>
	);
}
