/**
 * Public API for the Global Search feature package.
 *
 * Design goals:
 * - Export **API services, hooks, types, schemas, and utilities** that customers can import from node_modules.
 * - Do **not** export UI components or feature constants (customers build their own UI).
 *
 * Source implementation lives under `src/features/global-search/**`.
 */

// ---------------------------------------------------------------------------
// API layer
// ---------------------------------------------------------------------------

export { objectInfoService } from "./features/global-search/api/objectInfoService";
export {
	objectDetailService,
	extractFieldsFromLayout,
} from "./features/global-search/api/objectDetailService";
export type { RecordDetailResult } from "./features/global-search/api/objectDetailService";

export {
	getRecordsGraphQL,
	getRecordByIdGraphQL,
	buildGetRecordsQuery,
	buildWhereFromCriteria,
	buildOrderByFromSort,
} from "./features/global-search/api/recordListGraphQLService";
export type {
	RecordListGraphQLResult,
	RecordListGraphQLVariables,
	RecordListGraphQLOptions,
	GraphQLRecordNode,
} from "./features/global-search/api/recordListGraphQLService";

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export { useObjectInfoBatch } from "./features/global-search/hooks/useObjectInfoBatch";
export {
	useObjectListMetadata,
	useObjectColumns,
	useObjectFilters,
} from "./features/global-search/hooks/useObjectSearchData";
export { useRecordListGraphQL } from "./features/global-search/hooks/useRecordListGraphQL";
export { useRecordDetailLayout } from "./features/global-search/hooks/useRecordDetailLayout";

export type { ObjectListMetadata } from "./features/global-search/hooks/useObjectSearchData";

export type {
	UseRecordListGraphQLOptions,
	UseRecordListGraphQLReturn,
} from "./features/global-search/hooks/useRecordListGraphQL";

export type {
	UseRecordDetailLayoutParams,
	UseRecordDetailLayoutReturn,
} from "./features/global-search/hooks/useRecordDetailLayout";

// ---------------------------------------------------------------------------
// Types + Zod schemas (runtime validation)
// ---------------------------------------------------------------------------

export {
	ColumnArraySchema,
	SearchResultRecordArraySchema,
	KeywordSearchResultSchema,
	SearchResultsResponseSchema,
} from "./features/global-search/types/search/searchResults";
export type {
	Column,
	SearchResultRecord,
	KeywordSearchResult,
	SearchResultsResponse,
} from "./features/global-search/types/search/searchResults";

export {
	FilterArraySchema,
	FilterCriteriaArraySchema,
	FILTER_OPERATORS,
} from "./features/global-search/types/filters/filters";
export type {
	Filter,
	FilterCriteria,
	FilterOperator,
	FiltersResponse,
} from "./features/global-search/types/filters/filters";

export type { PicklistValue } from "./features/global-search/types/filters/picklist";

export type {
	ObjectInfoBatchResponse,
	ObjectInfoResult,
} from "./features/global-search/types/objectInfo/objectInfo";

export { LayoutResponseSchema } from "./features/global-search/types/recordDetail/recordDetail";
export type { LayoutResponse } from "./features/global-search/types/recordDetail/recordDetail";

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

export { fetchAndValidate, safeEncodePath } from "./features/global-search/utils/apiUtils";
export { debounce } from "./features/global-search/utils/debounce";
export { createFiltersKey } from "./features/global-search/utils/cacheUtils";
export {
	calculateFieldsToFetch,
	getSafeKey,
	isValidSalesforceId,
} from "./features/global-search/utils/recordUtils";
export { parseFilterValue } from "./features/global-search/utils/filterUtils";
export { sanitizeFilterValue } from "./features/global-search/utils/sanitizationUtils";
export {
	getGraphQLNodeValue,
	getDisplayValueForDetailFieldFromNode,
	getDisplayValueForLayoutItemFromNode,
	getGraphQLRecordDisplayName,
} from "./features/global-search/utils/graphQLNodeFieldUtils";
export { graphQLNodeToSearchResultRecordData } from "./features/global-search/utils/graphQLRecordAdapter";
