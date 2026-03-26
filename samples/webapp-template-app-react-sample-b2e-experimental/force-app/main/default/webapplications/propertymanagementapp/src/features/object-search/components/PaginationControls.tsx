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

interface PaginationControlsProps {
	pageIndex: number;
	hasNextPage: boolean;
	hasPreviousPage: boolean;
	pageSize: number;
	pageSizeOptions: readonly number[];
	onNextPage: () => void;
	onPreviousPage: () => void;
	onPageSizeChange: (newPageSize: number) => void;
	disabled?: boolean;
}

export default function PaginationControls({
	pageIndex,
	hasNextPage,
	hasPreviousPage,
	pageSize,
	pageSizeOptions,
	onNextPage,
	onPreviousPage,
	onPageSizeChange,
	disabled = false,
}: PaginationControlsProps) {
	const handlePageSizeChange = (newValue: string) => {
		const newSize = parseInt(newValue, 10);
		if (!isNaN(newSize) && newSize !== pageSize) {
			onPageSizeChange(newSize);
		}
	};
	const currentPage = pageIndex + 1;
	const prevDisabled = disabled || !hasPreviousPage;
	const nextDisabled = disabled || !hasNextPage;

	return (
		<div className="w-full grid grid-cols-1 sm:grid-cols-2 items-center justify-center gap-4 py-2">
			<div
				className="flex justify-center sm:justify-start items-center gap-2 shrink-0 row-2 sm:row-1"
				role="group"
				aria-label="Page size selector"
			>
				<Label htmlFor="page-size-select" className="text-sm font-normal whitespace-nowrap">
					Results per page:
				</Label>
				<Select
					value={pageSize.toString()}
					onValueChange={handlePageSizeChange}
					disabled={disabled}
				>
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
