/**
 * Search and filter bar for property search: area search, price range, number of bedrooms.
 */
import { Popover } from "radix-ui";
import { Search, ChevronDown } from "lucide-react";

const SEARCH_INPUT_CLASS =
	"h-10 rounded-full border-2 border-primary/50 bg-background px-4 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20";

const FILTER_PILL_CLASS =
	"inline-flex h-10 items-center gap-1.5 rounded-full border-2 border-primary/50 bg-background px-4 text-sm font-medium text-foreground outline-none transition-colors hover:border-primary/70 focus:ring-2 focus:ring-primary/20";

const SAVE_BUTTON_CLASS =
	"mt-3 w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/20";

const DEFAULT_PRICE_MIN = 0;
const DEFAULT_PRICE_MAX = 100_000;

/** Bedroom filter buckets: ≤2, exactly 3, or ≥4 */
export type BedroomFilter = "le2" | "3" | "ge4" | null;

const BEDROOM_OPTIONS: { value: BedroomFilter; label: string }[] = [
	{ value: "le2", label: "≤2" },
	{ value: "3", label: "3" },
	{ value: "ge4", label: "≥4" },
];

/** Sort by price or number of bedrooms, ascending or descending */
export type SortBy = "price_asc" | "price_desc" | "beds_asc" | "beds_desc" | null;

const SORT_OPTIONS: { value: NonNullable<SortBy>; label: string }[] = [
	{ value: "price_asc", label: "Price (low to high)" },
	{ value: "price_desc", label: "Price (high to low)" },
	{ value: "beds_asc", label: "Number of bedrooms (low to high)" },
	{ value: "beds_desc", label: "Number of bedrooms (high to low)" },
];

export interface PropertySearchFiltersProps {
	searchQuery: string;
	onSearchQueryChange: (value: string) => void;
	priceMin: string;
	onPriceMinChange: (value: string) => void;
	priceMax: string;
	onPriceMaxChange: (value: string) => void;
	/** Called when user clicks Save in the Price popover; use this to commit filters and run search. */
	onPriceSave?: (min: string, max: string) => void;
	bedrooms: BedroomFilter;
	onBedroomsChange: (value: BedroomFilter) => void;
	/** Called when user clicks Save in the Beds popover; use this to commit filters and run search. */
	onBedsSave?: (value: BedroomFilter) => void;
	sortBy: SortBy;
	onSortChange: (value: SortBy) => void;
	/** Called when user clicks Save in the Sort popover; use this to apply sort. */
	onSortSave?: (value: SortBy) => void;
	/** When set, pill shows this as the applied sort (e.g. after Save); otherwise pill shows sortBy. */
	appliedSortBy?: SortBy | null;
	onSubmit?: () => void;
}

export default function PropertySearchFilters({
	searchQuery,
	onSearchQueryChange,
	priceMin,
	onPriceMinChange,
	priceMax,
	onPriceMaxChange,
	onPriceSave,
	bedrooms,
	onBedroomsChange,
	onBedsSave,
	sortBy,
	onSortChange,
	onSortSave,
	appliedSortBy,
	onSubmit,
}: PropertySearchFiltersProps) {
	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter") onSubmit?.();
	};

	const rangeMin = DEFAULT_PRICE_MIN;
	const rangeMax = DEFAULT_PRICE_MAX;

	const minNum = priceMin.trim() ? Number(priceMin.replace(/[^0-9.]/g, "")) : NaN;
	const maxNum = priceMax.trim() ? Number(priceMax.replace(/[^0-9.]/g, "")) : NaN;
	const hasMin = Number.isFinite(minNum) && minNum > 0;
	const hasMax = Number.isFinite(maxNum) && maxNum > 0;
	const formatPrice = (n: number) =>
		new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "USD",
			maximumFractionDigits: 0,
		}).format(n);
	const priceValueLabel =
		hasMin && hasMax
			? `${formatPrice(minNum)} – ${formatPrice(maxNum)}`
			: hasMin
				? `${formatPrice(minNum)}+`
				: hasMax
					? `– ${formatPrice(maxNum)}`
					: null;
	const priceLabel = priceValueLabel != null ? `Price: ${priceValueLabel}` : "Price";

	const bedsLabel = bedrooms
		? `Number of bedrooms: ${BEDROOM_OPTIONS.find((o) => o.value === bedrooms)?.label ?? ""}`
		: "Number of bedrooms";

	const sortForPill = appliedSortBy ?? sortBy;
	const sortOptionLabel = sortForPill
		? (SORT_OPTIONS.find((o) => o.value === sortForPill)?.label ?? null)
		: null;
	const sortLabel = sortOptionLabel != null ? `Sort By: ${sortOptionLabel}` : "Sort By";

	return (
		<div className="flex w-full shrink-0 flex-col items-stretch gap-3 border-b border-border px-4 py-4 lg:flex-row lg:items-center">
			<div className="relative min-w-0 w-full lg:w-1/2 lg:shrink-0">
				<Search
					className="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-muted-foreground"
					aria-hidden
				/>
				<input
					type="text"
					value={searchQuery}
					onChange={(e) => onSearchQueryChange(e.target.value)}
					onKeyDown={handleKeyDown}
					placeholder="Area or search"
					className={`${SEARCH_INPUT_CLASS} w-full pl-10`}
					aria-label="Search property listings"
				/>
			</div>
			<div className="flex flex-wrap items-center gap-3 lg:flex-1 lg:min-w-0 lg:flex-nowrap">
				<div className="min-w-0 lg:flex-1">
					<Popover.Root>
						<Popover.Trigger asChild>
							<button
								type="button"
								className={`${FILTER_PILL_CLASS} w-full justify-center`}
								aria-label={priceValueLabel == null ? "Price filter" : priceLabel}
							>
								{priceLabel}
								<ChevronDown className="size-4 shrink-0 text-muted-foreground" aria-hidden />
							</button>
						</Popover.Trigger>
						<Popover.Portal>
							<Popover.Content
								sideOffset={8}
								align="start"
								className="z-[1100] w-[min(20rem,90vw)] rounded-xl border border-border bg-background p-4 shadow-lg outline-none"
							>
								<div className="space-y-3">
									<p className="text-sm font-medium text-foreground">Price range</p>
									<div className="flex items-center gap-2">
										<div className="flex flex-1 items-center rounded-full border-2 border-primary/50 bg-background focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
											<span className="pl-4 text-sm text-muted-foreground">$</span>
											<input
												type="number"
												min={rangeMin}
												max={rangeMax}
												step={1000}
												value={priceMin}
												onChange={(e) => onPriceMinChange(e.target.value)}
												onKeyDown={handleKeyDown}
												className="h-10 flex-1 border-0 bg-transparent px-2 py-0 text-sm outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
												aria-label="Minimum price"
											/>
										</div>
										<span className="text-muted-foreground">–</span>
										<div className="flex flex-1 items-center rounded-full border-2 border-primary/50 bg-background focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
											<span className="pl-4 text-sm text-muted-foreground">$</span>
											<input
												type="number"
												min={rangeMin}
												max={rangeMax}
												step={1000}
												value={priceMax}
												onChange={(e) => onPriceMaxChange(e.target.value)}
												onKeyDown={handleKeyDown}
												className="h-10 flex-1 border-0 bg-transparent px-2 py-0 text-sm outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
												aria-label="Maximum price"
											/>
										</div>
									</div>
									<Popover.Close asChild>
										<button
											type="button"
											className={SAVE_BUTTON_CLASS}
											onClick={() => onPriceSave?.(priceMin, priceMax)}
										>
											Save
										</button>
									</Popover.Close>
								</div>
							</Popover.Content>
						</Popover.Portal>
					</Popover.Root>
				</div>

				<div className="min-w-0 lg:flex-1">
					<Popover.Root>
						<Popover.Trigger asChild>
							<button
								type="button"
								className={`${FILTER_PILL_CLASS} w-full justify-center`}
								aria-label={bedrooms ? bedsLabel : "Number of bedrooms filter"}
							>
								{bedsLabel}
								<ChevronDown className="size-4 shrink-0 text-muted-foreground" aria-hidden />
							</button>
						</Popover.Trigger>
						<Popover.Portal>
							<Popover.Content
								sideOffset={8}
								align="start"
								className="z-[1100] w-[min(20rem,90vw)] rounded-xl border border-border bg-background p-4 shadow-lg outline-none"
							>
								<div className="space-y-3">
									<p className="text-sm font-medium text-foreground">Number of bedrooms</p>
									<div
										className="flex overflow-hidden rounded-full border-2 border-primary/40"
										role="group"
										aria-label="Number of bedrooms"
									>
										{BEDROOM_OPTIONS.map(({ value, label }) => (
											<button
												key={value}
												type="button"
												onClick={() => onBedroomsChange(bedrooms === value ? null : value)}
												className={`min-w-[4rem] flex-1 border-r border-primary/40 px-4 py-2 text-sm font-medium transition-colors last:border-r-0 ${
													bedrooms === value
														? "bg-primary text-primary-foreground"
														: "bg-background text-primary hover:bg-primary/10"
												}`}
												aria-pressed={bedrooms === value}
												aria-label={
													value === "le2"
														? "2 or fewer bedrooms"
														: value === "3"
															? "3 bedrooms"
															: "4 or more bedrooms"
												}
											>
												{label}
											</button>
										))}
									</div>
									<Popover.Close asChild>
										<button
											type="button"
											className={SAVE_BUTTON_CLASS}
											onClick={() => onBedsSave?.(bedrooms)}
										>
											Save
										</button>
									</Popover.Close>
								</div>
							</Popover.Content>
						</Popover.Portal>
					</Popover.Root>
				</div>

				<div className="min-w-0 lg:flex-1">
					<Popover.Root>
						<Popover.Trigger asChild>
							<button
								type="button"
								className={`${FILTER_PILL_CLASS} w-full justify-center`}
								aria-label={sortBy ? sortLabel : "Sort By"}
							>
								{sortLabel}
								<ChevronDown className="size-4 shrink-0 text-muted-foreground" aria-hidden />
							</button>
						</Popover.Trigger>
						<Popover.Portal>
							<Popover.Content
								sideOffset={8}
								align="start"
								className="z-[1100] w-[min(20rem,90vw)] rounded-xl border border-border bg-background p-4 shadow-lg outline-none"
							>
								<div className="space-y-3">
									<p className="text-sm font-medium text-foreground">Sort by</p>
									<div className="flex flex-col gap-1">
										{SORT_OPTIONS.map(({ value, label }) => (
											<button
												key={value}
												type="button"
												onClick={() => onSortChange(value)}
												className={`rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors ${
													sortBy === value
														? "bg-primary text-primary-foreground"
														: "bg-background text-foreground hover:bg-muted"
												}`}
												aria-pressed={sortBy === value}
											>
												{label}
											</button>
										))}
									</div>
									<Popover.Close asChild>
										<button
											type="button"
											className={SAVE_BUTTON_CLASS}
											onClick={() => onSortSave?.(sortBy)}
										>
											Save
										</button>
									</Popover.Close>
								</div>
							</Popover.Content>
						</Popover.Portal>
					</Popover.Root>
				</div>
			</div>
		</div>
	);
}
