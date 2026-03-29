import { useMemo, useState } from "react";
import { Link } from "react-router";
import { AlertCircle, ChevronDown, SearchX } from "lucide-react";
import {
	searchAccounts,
	fetchDistinctIndustries,
	fetchDistinctTypes,
} from "../api/accountSearchService";
import { useCachedAsyncData } from "../../hooks/useCachedAsyncData";
import { fieldValue } from "../../utils/fieldUtils";
import { useObjectSearchParams } from "../../hooks/useObjectSearchParams";
import { Alert, AlertTitle, AlertDescription } from "../../../../components/ui/alert";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "../../../../components/ui/collapsible";
import { Skeleton } from "../../../../components/ui/skeleton";
import { FilterProvider, FilterResetButton } from "../../components/FilterContext";
import { SearchFilter } from "../../components/filters/SearchFilter";
import { TextFilter } from "../../components/filters/TextFilter";
import { SelectFilter } from "../../components/filters/SelectFilter";
import { MultiSelectFilter } from "../../components/filters/MultiSelectFilter";
import { NumericRangeFilter } from "../../components/filters/NumericRangeFilter";
import { DateFilter } from "../../components/filters/DateFilter";
import { DateRangeFilter } from "../../components/filters/DateRangeFilter";
import { ActiveFilters } from "../../components/ActiveFilters";
import { SortControl } from "../../components/SortControl";
import type { FilterFieldConfig } from "../../utils/filterUtils";
import type { SortFieldConfig } from "../../utils/sortUtils";
import type { Account_Filter, Account_OrderBy } from "../../../../api/graphql-operations-types";
import type { AccountSearchResult } from "../api/accountSearchService";
import { ObjectBreadcrumb } from "../../components/ObjectBreadcrumb";
import PaginationControls from "../../components/PaginationControls";
import type { PaginationConfig } from "../../hooks/useObjectSearchParams";

const PAGINATION_CONFIG: PaginationConfig = {
	defaultPageSize: 6,
	validPageSizes: [6, 12, 24, 48],
};

type AccountNode = NonNullable<
	NonNullable<NonNullable<AccountSearchResult["edges"]>[number]>["node"]
>;

const FILTER_CONFIGS: FilterFieldConfig[] = [
	{
		field: "search",
		label: "Search",
		type: "search",
		searchFields: ["Name", "Phone", "Industry"],
		placeholder: "Search by name, phone, or industry...",
	},
	{ field: "Name", label: "Account Name", type: "text", placeholder: "Search by name..." },
	{ field: "Industry", label: "Industry", type: "picklist" },
	{ field: "Type", label: "Type", type: "multipicklist" },
	{ field: "AnnualRevenue", label: "Annual Revenue", type: "numeric" },
	{ field: "CreatedDate", label: "Created Date", type: "datetime" },
	{ field: "LastModifiedDate", label: "Last Modified Date", type: "datetimerange" },
];

const ACCOUNT_SORT_CONFIGS: SortFieldConfig<keyof Account_OrderBy>[] = [
	{ field: "Name", label: "Name" },
	{ field: "AnnualRevenue", label: "Annual Revenue" },
	{ field: "Industry", label: "Industry" },
	{ field: "CreatedDate", label: "Created Date" },
];

// -- Component --------------------------------------------------------------

export default function AccountSearch() {
	const [filtersOpen, setFiltersOpen] = useState(true);
	const { data: industryOptions } = useCachedAsyncData(fetchDistinctIndustries, [], {
		key: "distinctIndustries",
		ttl: 300_000,
	});
	const { data: typeOptions } = useCachedAsyncData(fetchDistinctTypes, [], {
		key: "distinctTypes",
		ttl: 300_000,
	});

	const { filters, sort, query, pagination, resetAll } = useObjectSearchParams<
		Account_Filter,
		Account_OrderBy
	>(FILTER_CONFIGS, ACCOUNT_SORT_CONFIGS, PAGINATION_CONFIG);

	const searchKey = `accounts:${JSON.stringify({ where: query.where, orderBy: query.orderBy, first: pagination.pageSize, after: pagination.afterCursor })}`;
	const { data, loading, error } = useCachedAsyncData(
		() =>
			searchAccounts({
				where: query.where,
				orderBy: query.orderBy,
				first: pagination.pageSize,
				after: pagination.afterCursor,
			}),
		[query.where, query.orderBy, pagination.pageSize, pagination.afterCursor],
		{ key: searchKey },
	);

	const pageInfo = data?.pageInfo;
	const totalCount = data?.totalCount;
	const hasNextPage = pageInfo?.hasNextPage ?? false;
	const hasPreviousPage = pagination.pageIndex > 0;

	const validAccountNodes = useMemo(
		() =>
			(data?.edges ?? []).reduce<AccountNode[]>((acc, edge) => {
				if (edge?.node) acc.push(edge.node);
				return acc;
			}, []),
		[data?.edges],
	);

	return (
		<div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
			<ObjectBreadcrumb listPath="/accounts" listLabel="Accounts" />

			<h1 className="text-2xl font-bold mb-4">Search Accounts</h1>

			<div className="flex flex-col lg:flex-row gap-6">
				{/* Sidebar — Filter Panel */}
				<aside className="w-full lg:w-80 shrink-0">
					<FilterProvider
						filters={filters.active}
						onFilterChange={filters.set}
						onFilterRemove={filters.remove}
						onReset={resetAll}
					>
						<Card>
							<Collapsible open={filtersOpen} onOpenChange={setFiltersOpen}>
								<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
									<CardTitle className="text-base font-semibold">
										<h2>Filters</h2>
									</CardTitle>
									<div className="flex items-center gap-1">
										<FilterResetButton variant="destructive" size="sm" />
										<CollapsibleTrigger asChild>
											<Button variant="ghost" size="icon">
												<ChevronDown
													className={`h-4 w-4 transition-transform ${filtersOpen ? "" : "-rotate-90"}`}
												/>
												<span className="sr-only">Toggle filters</span>
											</Button>
										</CollapsibleTrigger>
									</div>
								</CardHeader>
								<CollapsibleContent>
									<CardContent className="space-y-1 pt-0">
										<SearchFilter
											field="search"
											label="Search"
											placeholder="Search by name, phone, or industry..."
										/>
										<TextFilter field="Name" label="Account Name" placeholder="Search by name..." />
										<SelectFilter
											field="Industry"
											label="Industry"
											options={industryOptions ?? []}
										/>
										<MultiSelectFilter field="Type" label="Type" options={typeOptions ?? []} />
										<NumericRangeFilter
											field="AnnualRevenue"
											label="Annual Revenue"
											min={0}
											max={1_000_000_000_000}
										/>
										<DateFilter field="CreatedDate" label="Created Date" filterType="datetime" />
										<DateRangeFilter
											field="LastModifiedDate"
											label="Last Modified Date"
											filterType="datetimerange"
										/>
									</CardContent>
								</CollapsibleContent>
							</Collapsible>
						</Card>
					</FilterProvider>
				</aside>

				{/* Main area — Sort + Results */}
				<div className="flex-1 min-w-0">
					{/* Sort control + active filters */}
					<div className="flex flex-wrap items-center gap-2 mb-4">
						<SortControl
							configs={ACCOUNT_SORT_CONFIGS}
							sort={sort.current}
							onSortChange={sort.set}
						/>
						<ActiveFilters filters={filters.active} onRemove={filters.remove} />
					</div>

					<div className="min-h-112">
						{/* Loading state */}
						{loading && (
							<>
								<Skeleton className="h-5 w-30 mb-3" />
								<div className="divide-y">
									{Array.from({ length: pagination.pageSize }, (_, i) => (
										<div key={i} className="flex items-center justify-between py-3">
											<div className="space-y-2">
												<Skeleton className="h-5 w-40" />
												<Skeleton className="h-4 w-28" />
											</div>
											<div className="space-y-2 flex flex-col items-end">
												<Skeleton className="h-4 w-24" />
												<Skeleton className="h-4 w-20" />
											</div>
										</div>
									))}
								</div>
							</>
						)}

						{/* Error state */}
						{error && (
							<>
								<p className="text-sm text-muted-foreground mb-3">0 accounts found</p>
								<Alert variant="destructive" role="alert">
									<AlertCircle />
									<AlertTitle>Failed to load accounts</AlertTitle>
									<AlertDescription>
										Something went wrong while loading accounts. Please try again later.
									</AlertDescription>
								</Alert>
							</>
						)}

						{/* Results list */}
						{!loading && !error && validAccountNodes.length > 0 && (
							<>
								<p className="text-sm text-muted-foreground mb-3">
									{totalCount != null && (hasNextPage || hasPreviousPage)
										? `${totalCount} account${totalCount !== 1 ? "s" : ""} found`
										: `Showing ${validAccountNodes.length} account${validAccountNodes.length !== 1 ? "s" : ""}`}
								</p>
								<AccountResultsList nodes={validAccountNodes} />
							</>
						)}

						{/* No results state */}
						{!loading && !error && validAccountNodes.length === 0 && (
							<div className="flex flex-col items-center justify-center py-16 text-center">
								<SearchX className="size-12 text-muted-foreground mb-4" />
								<h2 className="text-lg font-semibold mb-1">No accounts found</h2>
								<p className="text-sm text-muted-foreground">
									Try adjusting your filters or search criteria.
								</p>
							</div>
						)}
					</div>

					{/* Pagination — always visible, disabled while loading or on error */}
					<PaginationControls
						pageIndex={pagination.pageIndex}
						hasNextPage={hasNextPage}
						hasPreviousPage={hasPreviousPage}
						pageSize={pagination.pageSize}
						pageSizeOptions={PAGINATION_CONFIG.validPageSizes}
						onNextPage={() => {
							if (pageInfo?.endCursor) pagination.goToNextPage(pageInfo.endCursor);
						}}
						onPreviousPage={pagination.goToPreviousPage}
						onPageSizeChange={pagination.setPageSize}
						disabled={loading || !!error}
					/>
				</div>
			</div>
		</div>
	);
}

// -- Result Components ------------------------------------------------------

function AccountResultsList({ nodes }: { nodes: AccountNode[] }) {
	return (
		<ul className="divide-y">
			{nodes.map((node) => (
				<AccountResultItem key={node.Id} node={node} />
			))}
		</ul>
	);
}

function AccountResultItem({ node }: { node: AccountNode }) {
	return (
		<li>
			<Link
				to={`/accounts/${node.Id}`}
				className="flex items-center justify-between py-3 px-3 -mx-3 rounded-md transition-colors hover:bg-accent"
			>
				<div>
					<span className="font-medium">{fieldValue(node.Name) ?? "\u2014"}</span>
					<p className="text-sm text-muted-foreground">
						{[fieldValue(node.Industry), fieldValue(node.Type)].filter(Boolean).join(" \u00B7 ") ||
							"\u2014"}
					</p>
				</div>
				<div className="text-right text-sm">
					<p>{fieldValue(node.Phone) ?? ""}</p>
					<p className="text-muted-foreground">{fieldValue(node.Owner?.Name) ?? ""}</p>
				</div>
			</Link>
		</li>
	);
}
