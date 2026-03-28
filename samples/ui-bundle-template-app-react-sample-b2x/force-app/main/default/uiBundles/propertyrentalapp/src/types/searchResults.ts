import { z } from "zod";

/**
 * Type definitions for search results and column structures.
 * * ARCHITECTURE NOTE:
 * We define recursive interfaces MANUALLY first.
 * If we rely on z.infer<typeof LazySchema> where the schema is z.ZodTypeAny,
 * TypeScript defaults the type to 'any', destroying type safety.
 */
export type ComplexFieldValue = {
	apiName?: string;
	childRelationships?: Record<string, unknown>;
	eTag?: string;
	fields?: Record<string, FieldValue>; // Recursive reference
	id?: string;
	lastModifiedById?: string | null;
	lastModifiedDate?: string | null;
	recordTypeId?: string | null;
	recordTypeInfo?: unknown;
	systemModstamp?: string | null;
	weakEtag?: number;
};
export type FieldValue = {
	displayValue: string | null;
	value: string | number | boolean | null | ComplexFieldValue; // Recursive union
};

// Zod Schema for Inline Edit Attributes
export const InlineEditAttributesSchema = z.record(
	z.string(),
	z.object({
		editable: z.boolean(),
		required: z.boolean(),
	}),
);

/**
 * Inline edit attributes for a field
 */
export type InlineEditAttributes = z.infer<typeof InlineEditAttributesSchema>;

// Zod Schema for Column
export const ColumnSchema = z.object({
	fieldApiName: z.string(),
	inlineEditAttributes: InlineEditAttributesSchema.optional(),
	label: z.string(),
	lookupId: z.string().nullish(),
	searchable: z.boolean(),
	sortable: z.boolean(),
});

/**
 * Column definition for list/result UI. Can be derived from Filter[] via targetFieldPath and label
 * (e.g. filters.map(f => ({ fieldApiName: f.targetFieldPath, label: f.label, searchable: true, sortable: true }))).
 */
export type Column = z.infer<typeof ColumnSchema>;

// Export schema for validation
export const ColumnArraySchema = z.array(ColumnSchema);

// Zod Schema for Complex Field Value (recursive structure)
// Using z.lazy() to handle circular reference with FieldValueSchema
// Note: This schema is exported for advanced use cases but should be used carefully
// due to potential performance implications with deeply nested structures
export const ComplexFieldValueSchema: z.ZodType<ComplexFieldValue> = z.lazy(() =>
	z.object({
		apiName: z.string().optional(),
		childRelationships: z.record(z.string(), z.unknown()).optional(),
		eTag: z.string().optional(),
		fields: z.record(z.string(), FieldValueSchema).optional(),
		id: z.string().optional(),
		lastModifiedById: z.string().nullish(),
		lastModifiedDate: z.string().nullish(),
		recordTypeId: z.string().nullish(),
		recordTypeInfo: z.unknown().optional(),
		systemModstamp: z.string().nullish(),
		weakEtag: z.number().optional(),
	}),
);

// Zod Schema for Field Value (using z.lazy() to handle circular reference)
// Note: This schema is exported for validating individual field values on-demand
// Use FieldValueValidationSchema alias for clarity
// Using z.union([z.string(), z.null()]) instead of .nullish() to match FieldValue type definition
export const FieldValueSchema: z.ZodType<FieldValue> = z.lazy(() =>
	z.object({
		displayValue: z.union([z.string(), z.null()]),
		value: z.union([
			z.string(),
			z.number(),
			z.boolean(),
			z.null(),
			ComplexFieldValueSchema as z.ZodType<ComplexFieldValue>,
		]),
	}),
);

// Zod Schema for Search Result Record Data (lightweight validation)
// Using z.unknown() for fields to avoid expensive recursive validation of every field value
// This prevents UI freezing when validating large result sets (e.g., 100 records × 50 fields = 5,000 validations)
// Individual fields can be validated later when needed using FieldValueSchema
// Note: z.unknown() is safer than z.any() as it requires explicit type checking before use
export const SearchResultRecordDataSchema = z.object({
	apiName: z.string(),
	childRelationships: z.record(z.string(), z.unknown()),
	eTag: z.string(),
	fields: z.record(z.string(), z.unknown()), // Lightweight: avoids recursive validation, uses unknown for type safety
	id: z.string(),
	lastModifiedById: z.string().nullish(),
	lastModifiedDate: z.string().nullish(),
	recordTypeId: z.string().nullish(),
	recordTypeInfo: z.unknown().nullish(),
	systemModstamp: z.string().nullish(),
	weakEtag: z.number(),
});

// Full validation schema for individual field values (use when validating specific fields)
// This can be used to validate a single field value when needed
export const FieldValueValidationSchema = FieldValueSchema;

// Zod Schema for Highlight Info
export const HighlightInfoSchema = z.object({
	fields: z.record(z.string(), z.unknown()),
	snippet: z.string().nullish(),
});

// Zod Schema for Search Info
export const SearchInfoSchema = z.object({
	isPromoted: z.boolean(),
	isSpellCorrected: z.boolean(),
});

// Zod Schema for Search Result Record
export const SearchResultRecordSchema = z.object({
	highlightInfo: HighlightInfoSchema,
	record: SearchResultRecordDataSchema,
	searchInfo: SearchInfoSchema,
});

/**
 * Record structure within search results
 * Note: The fields property is typed as Record<string, FieldValue> for type safety,
 * but validation uses z.unknown() for performance (avoids recursive validation of all fields)
 */
export type SearchResultRecordData = Omit<
	z.infer<typeof SearchResultRecordDataSchema>,
	"fields"
> & {
	fields: Record<string, FieldValue>;
};

/**
 * Highlight information for search results
 */
export type HighlightInfo = z.infer<typeof HighlightInfoSchema>;

/**
 * Search information for results
 */
export type SearchInfo = z.infer<typeof SearchInfoSchema>;

/**
 * Single record in search results (complete structure from API)
 * Note: The record.fields property is typed as Record<string, FieldValue> for type safety,
 * but validation uses z.unknown() for performance (avoids recursive validation of all fields)
 */
export type SearchResultRecord = Omit<z.infer<typeof SearchResultRecordSchema>, "record"> & {
	record: SearchResultRecordData;
};

// Export schemas for validation
export const SearchResultRecordArraySchema = z.array(SearchResultRecordSchema);

// Zod Schema for Order By
export const OrderBySchema = z.object({
	fieldApiName: z.string(),
	isAscending: z.boolean(),
	label: z.string(),
});

/**
 * Order by configuration
 */
export type OrderBy = z.infer<typeof OrderBySchema>;

// Zod Schema for Keyword Search Result
export const KeywordSearchResultSchema = z.object({
	currentPageToken: z.string(),
	error: z.string().nullish(),
	nextPageToken: z.string().nullish(),
	objectApiName: z.string(),
	orderBy: z.array(OrderBySchema),
	pageSize: z.number(),
	previousPageToken: z.string().nullish(),
	records: z.array(SearchResultRecordSchema),
	relatedObjectApiNames: z.array(z.string()),
});

/**
 * Keyword search result structure
 */
export type KeywordSearchResult = z.infer<typeof KeywordSearchResultSchema>;

// Zod Schema for Search Results Response
export const SearchResultsResponseSchema = z.object({
	configurationName: z.string().nullish(),
	keywordSearchResult: KeywordSearchResultSchema,
	objectApiName: z.string(),
	query: z.string(),
	queryId: z.string(),
});

/**
 * Search results response structure
 */
export type SearchResultsResponse = z.infer<typeof SearchResultsResponseSchema>;

// Zod Schema for Column Info Response
export const ColumnInfoResponseSchema = z.record(z.string(), z.unknown()).and(
	z.object({
		columns: ColumnArraySchema.optional(),
		fields: ColumnArraySchema.optional(),
	}),
);

/**
 * Column info response structure
 */
export type ColumnInfoResponse = z.infer<typeof ColumnInfoResponseSchema>;
