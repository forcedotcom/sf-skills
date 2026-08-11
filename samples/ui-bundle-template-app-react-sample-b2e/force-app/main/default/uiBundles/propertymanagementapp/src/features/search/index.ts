/**
 * Public API for the search feature.
 *
 * Most apps only need:
 *   ```tsx
 *   import { Search, config } from ".../features/search";
 *   <Search config={config} />
 *   ```
 *
 * For more control, drop down to primitives:
 *   - {@link useSearch} hook + {@link SearchBar} + {@link SearchResults}
 *   - {@link DefaultResultRow} / {@link DefaultFilterPanel} for opt-in defaults
 *   - filter components (TextFilter, SelectFilter, ...) for custom sidebars
 */

// Drop-in wrapper (most common entry point)
export { Search } from "./components/Search";

// Primitives
export { useSearch } from "./hooks/useSearch";
export { useAsyncData } from "./hooks/useAsyncData";
export { useDistinctValues } from "./hooks/useDistinctValues";

export { SearchBar } from "./components/controls/SearchBar";
export { SearchResults } from "./components/SearchResults";
export { MergedSearchResults } from "./components/MergedSearchResults";
export type { MergedSearchResultsProps } from "./components/MergedSearchResults";
export { SourceSection } from "./components/SourceSection";
export { SortControl } from "./components/controls/SortControl";
export { PaginationControls } from "./components/controls/PaginationControls";
export { ScopeSelector } from "./components/controls/ScopeSelector";
export { ActiveFilters } from "./components/filters/ActiveFilters";
export { DefaultResultRow } from "./components/results/DefaultResultRow";
export { DefaultFilterPanel } from "./components/filters/DefaultFilterPanel";
export {
	FilterProvider,
	FilterResetButton,
	useFilterField,
	useFilterPanel,
} from "./components/filters/FilterContext";

export { TextFilter } from "./components/filters/inputs/TextFilter";
export { SelectFilter } from "./components/filters/inputs/SelectFilter";
export { MultiSelectFilter } from "./components/filters/inputs/MultiSelectFilter";
export { NumericRangeFilter } from "./components/filters/inputs/NumericRangeFilter";
export { BooleanFilter } from "./components/filters/inputs/BooleanFilter";
export { DateRangeFilter } from "./components/filters/inputs/DateRangeFilter";
export { FilterFieldWrapper } from "./components/filters/inputs/FilterFieldWrapper";

export { fieldValue } from "./utils/fieldUtils";
export {
	buildFilter,
	buildGlobalQueryClause,
	readSourceParams,
	writeSourceParams,
	GLOBAL_QUERY_KEY,
} from "./utils/filterUtils";
export type {
	ActiveFilterValue,
	DateFilterMode,
	FilterFieldConfig,
	FilterFieldType,
} from "./utils/filterUtils";
export { buildOrderBy } from "./utils/sortUtils";
export type { SortFieldConfig, SortState } from "./utils/sortUtils";

export { buildSearchQuery } from "./queryBuilder";
export type { SourceRequest, SearchQueryPayload } from "./queryBuilder";

export { runSearch } from "./api/searchService";
export { fetchDistinctValues } from "./api/distinctValuesService";
export type { PicklistOption } from "./api/distinctValuesService";

export { config } from "./loadConfig";

export { ALL_SCOPE } from "./types";
export type {
	DisplayField,
	SObjectSourceConfig,
	SearchConfig,
	SearchPaginationConfig,
	SourceController,
	SourceResult,
	SourcePageInfo,
	SearchHandle,
	SearchScope,
	RenderResultFn,
	GlobalPagination,
	MergedResultItem,
} from "./types";
