/**
 * Property Search page – ZENLEASE-style layout.
 * Map ~2/3 left, scrollable listings ~1/3 right; search/filter bar above.
 */
import { useState, useCallback, useMemo, useEffect } from "react";
import { useSearchParams } from "react-router";
import { DEFAULT_PAGE_SIZE } from "@/features/global-search/constants";
import { usePropertyListingSearch } from "@/hooks/usePropertyListingSearch";
import {
	usePropertyPrimaryImages,
	getPropertyIdFromRecord,
} from "@/hooks/usePropertyPrimaryImages";
import { usePropertyAddresses } from "@/hooks/usePropertyAddresses";
import { usePropertyListingAmenities } from "@/hooks/usePropertyListingAmenities";
import { usePropertyMapMarkers } from "@/hooks/usePropertyMapMarkers";
import SearchPagination from "@/features/global-search/components/search/SearchPagination";
import PropertyListingCard, { PropertyListingCardSkeleton } from "@/components/PropertyListingCard";
import PropertySearchFilters, {
	type BedroomFilter,
	type SortBy,
} from "@/components/PropertySearchFilters";
import PropertyMap from "@/components/PropertyMap";
import type { MapMarker, MapBounds } from "@/components/PropertyMap";
import PropertySearchPlaceholder from "@/pages/PropertySearchPlaceholder";
import { Skeleton } from "@/components/ui/skeleton";
import type { SearchResultRecord } from "@/features/global-search/types/search/searchResults.js";

/** Fallback map center when there are no geocoded markers yet. Zoom 7 ≈ 100-mile radius view. */
const MAP_CENTER_FALLBACK: [number, number] = [37.7897484, -122.3998086];
const MAP_ZOOM_DEFAULT = 10;
const MAP_ZOOM_WITH_MARKERS = 12;

/** Delay before applying any filter change to the search (avoids refetch on every keystroke/slider tick). */
const SEARCH_FILTER_DEBOUNCE_MS = 400;

export default function PropertySearch() {
	const [searchParams] = useSearchParams();
	const initialSearch = searchParams.get("search") ?? "";
	const [searchQuery, setSearchQuery] = useState(initialSearch);
	const [searchPageSize, setSearchPageSize] = useState(DEFAULT_PAGE_SIZE);
	const [searchPageToken, setSearchPageToken] = useState("0");
	const [priceMin, setPriceMin] = useState<string>("");
	const [priceMax, setPriceMax] = useState<string>("");
	const [bedrooms, setBedrooms] = useState<BedroomFilter>(null);
	const [committedSearchQuery, setCommittedSearchQuery] = useState(initialSearch);
	const [committedPriceMin, setCommittedPriceMin] = useState<string>("");
	const [committedPriceMax, setCommittedPriceMax] = useState<string>("");
	const [committedBedrooms, setCommittedBedrooms] = useState<BedroomFilter>(null);
	const [stagedSortBy, setStagedSortBy] = useState<SortBy>(null);
	const [committedSortBy, setCommittedSortBy] = useState<SortBy>("price_asc");

	// Sync from URL when navigating with ?search=... (e.g. from Home "Find Home")
	useEffect(() => {
		const q = searchParams.get("search") ?? "";
		setSearchQuery(q);
		setCommittedSearchQuery(q);
		setSearchPageToken("0");
	}, [searchParams]);

	// Debounce search query only; price and bedrooms commit only when user clicks Save in the popover.
	useEffect(() => {
		const t = setTimeout(() => {
			setCommittedSearchQuery(searchQuery);
		}, SEARCH_FILTER_DEBOUNCE_MS);
		return () => clearTimeout(t);
	}, [searchQuery]);

	const handlePriceSave = useCallback((min: string, max: string) => {
		setCommittedPriceMin(min);
		setCommittedPriceMax(max);
		setSearchPageToken("0");
	}, []);

	const handleBedsSave = useCallback((value: BedroomFilter) => {
		setCommittedBedrooms(value);
		setSearchPageToken("0");
	}, []);

	const handleSortSave = useCallback((value: SortBy) => {
		setCommittedSortBy(value);
		setSearchPageToken("0");
	}, []);

	const filters = useMemo(() => {
		const out: {
			priceMin?: number;
			priceMax?: number;
			bedroomsMin?: number;
			bedroomsMax?: number;
			sortBy?: SortBy;
		} = {};
		const min = committedPriceMin.trim() ? Number(committedPriceMin.replace(/[^0-9.]/g, "")) : NaN;
		const max = committedPriceMax.trim() ? Number(committedPriceMax.replace(/[^0-9.]/g, "")) : NaN;
		if (Number.isFinite(min) && min >= 0) out.priceMin = min;
		if (Number.isFinite(max) && max >= 0) out.priceMax = max;
		if (committedBedrooms === "le2") {
			out.bedroomsMax = 2;
		} else if (committedBedrooms === "3") {
			out.bedroomsMin = 3;
			out.bedroomsMax = 3;
		} else if (committedBedrooms === "ge4") {
			out.bedroomsMin = 4;
		}
		if (committedSortBy != null) out.sortBy = committedSortBy;
		return out;
	}, [committedPriceMin, committedPriceMax, committedBedrooms, committedSortBy]);

	const {
		results,
		nextPageToken,
		previousPageToken,
		currentPageToken,
		resultsLoading,
		resultsError,
	} = usePropertyListingSearch(committedSearchQuery, searchPageSize, searchPageToken, filters);

	const primaryImagesMap = usePropertyPrimaryImages(results);
	const propertyAddressMap = usePropertyAddresses(results);
	const amenitiesMap = usePropertyListingAmenities(results);
	const { markers: mapMarkers } = usePropertyMapMarkers(results);
	const apiUnavailable = Boolean(resultsError);

	const [mapBounds, setMapBounds] = useState<MapBounds | null>(null);

	const validResults = useMemo(() => results.filter((r) => r?.record?.id), [results]);

	function getSortPrice(r: SearchResultRecord): number {
		const raw = r?.record?.fields?.["Listing_Price__c"];
		if (raw == null || typeof raw !== "object") return NaN;
		const v = (raw as { value?: unknown }).value;
		return typeof v === "number" ? v : Number(v);
	}
	function getSortBeds(r: SearchResultRecord): number {
		const raw = r?.record?.fields?.["Property__r.Bedrooms__c"];
		if (raw == null || typeof raw !== "object") return NaN;
		const v = (raw as { value?: unknown }).value;
		return typeof v === "number" ? v : Number(v);
	}

	// Order applied only after user clicks Save (committedSortBy); server may also apply orderBy.
	const sortedResults = useMemo(() => {
		if (!committedSortBy) return validResults;
		const list = [...validResults];
		if (committedSortBy === "price_asc" || committedSortBy === "price_desc") {
			const dir = committedSortBy === "price_asc" ? 1 : -1;
			list.sort((a, b) => {
				const pa = getSortPrice(a);
				const pb = getSortPrice(b);
				if (Number.isNaN(pa) && Number.isNaN(pb)) return 0;
				if (Number.isNaN(pa)) return 1;
				if (Number.isNaN(pb)) return -1;
				return dir * (pa - pb);
			});
		} else {
			const dir = committedSortBy === "beds_asc" ? 1 : -1;
			list.sort((a, b) => {
				const ba = getSortBeds(a);
				const bb = getSortBeds(b);
				if (Number.isNaN(ba) && Number.isNaN(bb)) return 0;
				if (Number.isNaN(ba)) return 1;
				if (Number.isNaN(bb)) return -1;
				return dir * (ba - bb);
			});
		}
		return list;
	}, [validResults, committedSortBy]);

	// When user pans/zooms, filter list to properties whose pin is visible on the map
	const visibleResults = useMemo(() => {
		if (!mapBounds || mapMarkers.length === 0) return sortedResults;
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
		return sortedResults.filter((r) => {
			const id = getPropertyIdFromRecord(r.record);
			return id != null && visiblePropertyIds.has(id);
		});
	}, [sortedResults, mapMarkers, mapBounds]);

	const handlePageChange = useCallback((newPageToken: string) => {
		setSearchPageToken(newPageToken);
	}, []);

	const handlePageSizeChange = useCallback((newPageSize: number) => {
		setSearchPageSize(newPageSize);
		setSearchPageToken("0");
	}, []);

	const handleSearchSubmit = useCallback(() => {
		setSearchPageToken("0");
	}, []);

	const popupContent = useCallback(
		(marker: MapMarker) => {
			if (!marker.propertyId) return marker.label ?? "Property";
			const result = results.find(
				(r) => r?.record && getPropertyIdFromRecord(r.record) === marker.propertyId,
			);
			if (!result?.record) return marker.label ?? "Property";
			const propertyId = getPropertyIdFromRecord(result.record);
			const imageUrl = propertyId ? (primaryImagesMap[propertyId] ?? null) : null;
			const address = propertyId ? (propertyAddressMap[propertyId] ?? null) : null;
			const amenities = propertyId ? (amenitiesMap[propertyId] ?? null) : null;
			return (
				<div className="w-[280px] min-w-0">
					<PropertyListingCard
						record={result.record}
						imageUrl={imageUrl}
						address={address}
						amenities={amenities || undefined}
						loading={primaryImagesMap.loading || propertyAddressMap.loading || amenitiesMap.loading}
					/>
				</div>
			);
		},
		[results, primaryImagesMap, propertyAddressMap, amenitiesMap],
	);

	return (
		<div className="flex h-[calc(100vh-4rem)] min-h-[500px] flex-col">
			<PropertySearchFilters
				searchQuery={searchQuery}
				onSearchQueryChange={setSearchQuery}
				priceMin={priceMin}
				onPriceMinChange={setPriceMin}
				priceMax={priceMax}
				onPriceMaxChange={setPriceMax}
				onPriceSave={handlePriceSave}
				bedrooms={bedrooms}
				onBedroomsChange={setBedrooms}
				onBedsSave={handleBedsSave}
				sortBy={stagedSortBy ?? committedSortBy}
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
							<p className="text-sm text-muted-foreground">
								{apiUnavailable ? (
									"Placeholder (API unavailable)"
								) : resultsLoading ? (
									<Skeleton className="inline-block h-4 w-24 align-middle" />
								) : mapBounds != null && mapMarkers.length > 0 ? (
									`${visibleResults.length} of ${sortedResults.length} in map view`
								) : (
									`${sortedResults.length} result(s)`
								)}
							</p>
							{mapBounds != null && sortedResults.length > 0 && !resultsLoading && (
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
							<PropertySearchPlaceholder
								message={resultsError ?? "Search is temporarily unavailable."}
							/>
						) : resultsLoading ? (
							<div className="space-y-4">
								{[1, 2, 3].map((i) => (
									<PropertyListingCardSkeleton key={i} />
								))}
							</div>
						) : sortedResults.length === 0 ? (
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
									Show all {sortedResults.length} result(s)
								</button>
							</div>
						) : (
							<>
								<ul className="space-y-4" role="list" aria-label="Search results">
									{visibleResults.map((record, index) => {
										const propertyId = getPropertyIdFromRecord(record.record);
										const imageUrl = propertyId ? (primaryImagesMap[propertyId] ?? null) : null;
										const address = propertyId ? (propertyAddressMap[propertyId] ?? null) : null;
										const amenities = propertyId ? (amenitiesMap[propertyId] ?? null) : null;
										return (
											<li key={record.record.id ?? index}>
												<PropertyListingCard
													record={record.record}
													imageUrl={imageUrl}
													address={address}
													amenities={amenities || undefined}
													loading={
														primaryImagesMap.loading ||
														propertyAddressMap.loading ||
														amenitiesMap.loading
													}
												/>
											</li>
										);
									})}
								</ul>
								<div className="mt-4">
									<SearchPagination
										currentPageToken={currentPageToken}
										nextPageToken={nextPageToken}
										previousPageToken={previousPageToken}
										pageSize={searchPageSize}
										onPageChange={handlePageChange}
										onPageSizeChange={handlePageSizeChange}
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
