/**
 * Property Search page – ZENLEASE-style layout.
 * Map ~2/3 left, scrollable listings ~1/3 right; search/filter bar above.
 */
import { useState, useCallback, useMemo, useEffect } from "react";
import {
	searchProperties,
	type PropertySearchNode,
	type PropertySearchResult,
} from "@/api/properties/propertySearchService";
import {
	extractPrimaryImageUrl,
	extractAmenities,
	extractAddress,
} from "@/api/properties/propertyNodeUtils";
import type { Property__C_Filter, Property__C_OrderBy } from "@/api/graphql-operations-types";
import {
	useObjectSearchParams,
	type PaginationConfig,
} from "@/features/object-search/hooks/useObjectSearchParams";
import { useCachedAsyncData } from "@/features/object-search/hooks/useCachedAsyncData";
import type { FilterFieldConfig } from "@/features/object-search/utils/filterUtils";
import type {
	SortFieldConfig,
	SortState,
} from "@/features/object-search/utils/sortUtils";
import { usePropertyMapMarkers } from "@/hooks/usePropertyMapMarkers";
import PaginationControls from "@/features/object-search/components/PaginationControls";
import PropertyListingCard, {
	PropertyListingCardSkeleton,
} from "@/components/properties/PropertyListingCard";
import PropertySearchFilters, {
	type BedroomFilter,
	type SortBy,
} from "@/components/properties/PropertySearchFilters";
import PropertyMap from "@/components/properties/PropertyMap";
import type { MapMarker, MapBounds } from "@/components/properties/PropertyMap";
import PropertySearchPlaceholder from "@/pages/PropertySearchPlaceholder";
import { Skeleton } from "@/components/ui/skeleton";

/** Fallback map center when there are no geocoded markers yet. Zoom 7 ≈ 100-mile radius view. */
const MAP_CENTER_FALLBACK: [number, number] = [37.7897484, -122.3998086];
const MAP_ZOOM_DEFAULT = 10;
const MAP_ZOOM_WITH_MARKERS = 12;

/** Delay before applying search text change to the committed filter. */
const SEARCH_FILTER_DEBOUNCE_MS = 400;

const FILTER_CONFIGS: FilterFieldConfig[] = [
	{
		field: "search",
		label: "Search",
		type: "search",
		searchFields: ["Name", "Address__c"],
		placeholder: "Area or search",
	},
	{ field: "Monthly_Rent__c", label: "Price", type: "numeric" },
	{ field: "Bedrooms__c", label: "Bedrooms", type: "numeric" },
];

const SORT_CONFIGS: SortFieldConfig[] = [
	{ field: "Monthly_Rent__c", label: "Monthly Rent" },
	{ field: "Bedrooms__c", label: "Bedrooms" },
];

const PAGINATION_CONFIG: PaginationConfig = {
	defaultPageSize: 20,
	validPageSizes: [10, 20, 50],
};

/* ── Adapter helpers: translate between popover pill UI types and object-search state ── */

const SORT_TO_STATE: Record<NonNullable<SortBy>, SortState> = {
	price_asc: { field: "Monthly_Rent__c", direction: "ASC" },
	price_desc: { field: "Monthly_Rent__c", direction: "DESC" },
	beds_asc: { field: "Bedrooms__c", direction: "ASC" },
	beds_desc: { field: "Bedrooms__c", direction: "DESC" },
};

function sortStateToSortBy(s: SortState | null): SortBy {
	if (!s) return null;
	for (const [key, val] of Object.entries(SORT_TO_STATE)) {
		if (val.field === s.field && val.direction === s.direction) return key as SortBy;
	}
	return null;
}

function bedroomBucketToRange(value: BedroomFilter): { min?: string; max?: string } | null {
	if (value === "le2") return { max: "2" };
	if (value === "3") return { min: "3", max: "3" };
	if (value === "ge4") return { min: "4" };
	return null;
}

function rangeToBedroomBucket(min?: string, max?: string): BedroomFilter {
	if (!min && max === "2") return "le2";
	if (min === "3" && max === "3") return "3";
	if (min === "4" && !max) return "ge4";
	return null;
}

export default function PropertySearch() {
	/* ── Object-search infrastructure ── */
	const { filters, sort, query, pagination } = useObjectSearchParams<
		Property__C_Filter,
		Property__C_OrderBy
	>(FILTER_CONFIGS, SORT_CONFIGS, PAGINATION_CONFIG);

	/* ── Data fetching ── */
	const searchKey = `rentalProperties:${JSON.stringify({
		where: query.where,
		orderBy: query.orderBy,
		first: pagination.pageSize,
		after: pagination.afterCursor,
	})}`;

	const {
		data: searchResult,
		loading: resultsLoading,
		error: resultsError,
	} = useCachedAsyncData<PropertySearchResult>(
		() =>
			searchProperties({
				where: query.where,
				orderBy: query.orderBy,
				first: pagination.pageSize,
				after: pagination.afterCursor,
			}),
		[query.where, query.orderBy, pagination.pageSize, pagination.afterCursor],
		{ key: searchKey },
	);

	/* ── Derive results + maps ── */
	const results = useMemo(
		() =>
			(searchResult?.edges ?? []).reduce<PropertySearchNode[]>((acc, edge) => {
				if (edge?.node) acc.push(edge.node);
				return acc;
			}, []),
		[searchResult?.edges],
	);

	const primaryImagesMap = useMemo(() => {
		const map: Record<string, string> = {};
		for (const node of results) {
			const url = extractPrimaryImageUrl(node);
			if (url) map[node.Id] = url;
		}
		return map;
	}, [results]);

	const propertyAddressMap = useMemo(() => {
		const map: Record<string, string> = {};
		for (const node of results) {
			const addr = extractAddress(node);
			if (addr) map[node.Id] = String(addr);
		}
		return map;
	}, [results]);

	const amenitiesMap = useMemo(() => {
		const map: Record<string, string> = {};
		for (const node of results) {
			const amenities = extractAmenities(node);
			if (amenities) map[node.Id] = amenities;
		}
		return map;
	}, [results]);

	/* ── Map markers + bounds ── */
	const { markers: mapMarkers } = usePropertyMapMarkers(results);
	const apiUnavailable = Boolean(resultsError);
	const [mapBounds, setMapBounds] = useState<MapBounds | null>(null);

	const visibleResults = useMemo(() => {
		if (!mapBounds || mapMarkers.length === 0) return results;
		const visiblePropertyIds = new Set(
			mapMarkers
				.filter(
					(m) =>
						m.propertyId &&
						m.lat >= mapBounds.south &&
						m.lat <= mapBounds.north &&
						m.lng >= mapBounds.west &&
						m.lng <= mapBounds.east,
				)
				.map((m) => m.propertyId as string),
		);
		return results.filter((r) => visiblePropertyIds.has(r.Id));
	}, [results, mapMarkers, mapBounds]);

	/* ── Staged filter state for popover edits (committed on Save) ── */
	const committedSearchValue = filters.active.find((f) => f.field === "search")?.value ?? "";
	const [searchQuery, setSearchQuery] = useState(committedSearchValue);

	// Debounce search text → filters.set
	useEffect(() => {
		const t = setTimeout(() => {
			if (searchQuery.trim()) {
				filters.set("search", {
					field: "search",
					label: "Search",
					type: "search",
					value: searchQuery,
				});
			} else {
				filters.remove("search");
			}
		}, SEARCH_FILTER_DEBOUNCE_MS);
		return () => clearTimeout(t);
	}, [searchQuery]);

	// Sync local searchQuery when the committed value changes externally (e.g. URL nav)
	useEffect(() => {
		setSearchQuery(committedSearchValue);
	}, [committedSearchValue]);

	const committedPriceFilter = filters.active.find((f) => f.field === "Monthly_Rent__c");
	const [stagedPriceMin, setStagedPriceMin] = useState(committedPriceFilter?.min ?? "");
	const [stagedPriceMax, setStagedPriceMax] = useState(committedPriceFilter?.max ?? "");
	useEffect(() => {
		setStagedPriceMin(committedPriceFilter?.min ?? "");
		setStagedPriceMax(committedPriceFilter?.max ?? "");
	}, [committedPriceFilter?.min, committedPriceFilter?.max]);

	const committedBedroomFilter = filters.active.find((f) => f.field === "Bedrooms__c");
	const committedBedrooms = rangeToBedroomBucket(
		committedBedroomFilter?.min,
		committedBedroomFilter?.max,
	);
	const [stagedBedrooms, setStagedBedrooms] = useState<BedroomFilter>(committedBedrooms);
	useEffect(() => {
		setStagedBedrooms(committedBedrooms);
	}, [committedBedrooms]);

	const committedSortBy = sortStateToSortBy(sort.current);
	const [stagedSortBy, setStagedSortBy] = useState<SortBy>(committedSortBy ?? "price_asc");
	useEffect(() => {
		setStagedSortBy(committedSortBy ?? "price_asc");
	}, [committedSortBy]);

	// Set default sort on mount if none set
	useEffect(() => {
		if (!sort.current) {
			sort.set(SORT_TO_STATE.price_asc);
		}
	}, [sort]);

	/* ── Save handlers: commit staged state to infrastructure ── */
	const handlePriceSave = useCallback(
		(min: string, max: string) => {
			if (min.trim() || max.trim()) {
				filters.set("Monthly_Rent__c", {
					field: "Monthly_Rent__c",
					label: "Price",
					type: "numeric",
					min: min.trim() || undefined,
					max: max.trim() || undefined,
				});
			} else {
				filters.remove("Monthly_Rent__c");
			}
		},
		[filters],
	);

	const handleBedsSave = useCallback(
		(value: BedroomFilter) => {
			const range = bedroomBucketToRange(value);
			if (range) {
				filters.set("Bedrooms__c", {
					field: "Bedrooms__c",
					label: "Bedrooms",
					type: "numeric",
					...range,
				});
			} else {
				filters.remove("Bedrooms__c");
			}
		},
		[filters],
	);

	const handleSortSave = useCallback(
		(value: SortBy) => {
			if (value && SORT_TO_STATE[value]) {
				sort.set(SORT_TO_STATE[value]);
			} else {
				sort.set(null);
			}
		},
		[sort],
	);

	const handleSearchSubmit = useCallback(() => {
		// Immediately commit the current search text (bypass debounce)
		if (searchQuery.trim()) {
			filters.set("search", {
				field: "search",
				label: "Search",
				type: "search",
				value: searchQuery,
			});
		} else {
			filters.remove("search");
		}
	}, [searchQuery, filters]);

	/* ── Pagination ── */
	const pageInfo = searchResult?.pageInfo;
	const hasNextPage = pageInfo?.hasNextPage ?? false;
	const hasPreviousPage = pagination.pageIndex > 0;

	/* ── Map popup ── */
	const popupContent = useCallback(
		(marker: MapMarker) => {
			if (!marker.propertyId) return marker.label ?? "Property";
			const node = results.find((r) => r.Id === marker.propertyId);
			if (!node) return marker.label ?? "Property";
			const imageUrl = primaryImagesMap[node.Id] ?? null;
			const address = propertyAddressMap[node.Id] ?? null;
			const amenities = amenitiesMap[node.Id] ?? null;
			return (
				<div className="w-[280px] min-w-0">
					<PropertyListingCard
						node={node}
						imageUrl={imageUrl}
						address={address}
						amenities={amenities || undefined}
						loading={resultsLoading}
					/>
				</div>
			);
		},
		[results, primaryImagesMap, propertyAddressMap, amenitiesMap, resultsLoading],
	);

	return (
		<div className="flex h-[calc(100vh-4rem)] min-h-[500px] flex-col">
			<PropertySearchFilters
				searchQuery={searchQuery}
				onSearchQueryChange={setSearchQuery}
				priceMin={stagedPriceMin}
				onPriceMinChange={setStagedPriceMin}
				priceMax={stagedPriceMax}
				onPriceMaxChange={setStagedPriceMax}
				onPriceSave={handlePriceSave}
				bedrooms={stagedBedrooms}
				onBedroomsChange={setStagedBedrooms}
				onBedsSave={handleBedsSave}
				sortBy={stagedSortBy}
				onSortChange={setStagedSortBy}
				onSortSave={handleSortSave}
				appliedSortBy={committedSortBy}
				onSubmit={handleSearchSubmit}
			/>

			{/* Main: map 2/3, list 1/3 */}
			<div className="flex min-h-0 flex-1 flex-col lg:flex-row">
				{/* Map – 2/3 on desktop */}
				<div className="isolate h-64 shrink-0 lg:h-full lg:min-h-0 lg:w-2/3" aria-label="Map">
					<PropertyMap
						center={MAP_CENTER_FALLBACK}
						zoom={mapMarkers.length > 0 ? MAP_ZOOM_WITH_MARKERS : MAP_ZOOM_DEFAULT}
						markers={mapMarkers}
						popupContent={popupContent}
						onBoundsChange={setMapBounds}
						className="h-full w-full"
					/>
				</div>

				{/* Listings – scrollable, 1/3 */}
				<aside className="flex w-full flex-col border-t border-border lg:w-1/3 lg:border-l lg:border-t-0">
					<div className="shrink-0 border-b border-border px-4 py-3">
						<h2 className="text-base font-semibold text-foreground">
							Property Listings
							{searchQuery.trim() ? ` matching "${searchQuery.trim()}"` : ""}
						</h2>
						<div className="flex flex-wrap items-center gap-2">
							<div className="text-sm text-muted-foreground">
								{apiUnavailable ? (
									"Placeholder (API unavailable)"
								) : resultsLoading ? (
									<Skeleton className="inline-block h-4 w-24 align-middle" />
								) : mapBounds != null && mapMarkers.length > 0 ? (
									`${visibleResults.length} of ${results.length} in map view`
								) : (
									`${results.length} result(s)`
								)}
							</div>
							{mapBounds != null && results.length > 0 && !resultsLoading && (
								<button
									type="button"
									onClick={() => setMapBounds(null)}
									className="text-sm font-medium text-primary hover:underline"
								>
									Show all
								</button>
							)}
						</div>
					</div>
					<div className="flex-1 overflow-y-auto p-4">
						{apiUnavailable ? (
							<PropertySearchPlaceholder message="Search is temporarily unavailable." />
						) : resultsLoading ? (
							<div className="space-y-4">
								{[1, 2, 3].map((i) => (
									<PropertyListingCardSkeleton key={i} />
								))}
							</div>
						) : results.length === 0 ? (
							<div className="py-12 text-center">
								<p className="mb-2 font-medium">No results found</p>
								<p className="text-sm text-muted-foreground">Try adjusting search or filters</p>
							</div>
						) : visibleResults.length === 0 && mapBounds != null ? (
							<div className="py-12 text-center">
								<p className="mb-2 font-medium">No listings in this map area</p>
								<p className="text-sm text-muted-foreground">
									Pan or zoom to see results, or clear the map filter
								</p>
								<button
									type="button"
									onClick={() => setMapBounds(null)}
									className="mt-3 text-sm font-medium text-primary hover:underline"
								>
									Show all {results.length} result(s)
								</button>
							</div>
						) : (
							<>
								<ul className="space-y-4" role="list" aria-label="Search results">
									{visibleResults.map((node, index) => {
										const imageUrl = primaryImagesMap[node.Id] ?? null;
										const address = propertyAddressMap[node.Id] ?? null;
										const amenities = amenitiesMap[node.Id] ?? null;
										return (
											<li key={node.Id ?? index}>
												<PropertyListingCard
													node={node}
													imageUrl={imageUrl}
													address={address}
													amenities={amenities || undefined}
													loading={resultsLoading}
												/>
											</li>
										);
									})}
								</ul>
								<div className="mt-4">
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
										disabled={resultsLoading || apiUnavailable}
									/>
								</div>
							</>
						)}
					</div>
				</aside>
			</div>
		</div>
	);
}
