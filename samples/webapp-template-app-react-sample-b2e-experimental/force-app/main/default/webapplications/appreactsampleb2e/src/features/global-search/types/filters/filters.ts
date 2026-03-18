import { z } from "zod";

/**
 * Type definitions for filter structures
 * All types are derived from Zod schemas using z.infer for type safety
 */

/**
 * Allowed filter operators for Salesforce search queries
 */
export const FILTER_OPERATORS = [
	"eq", // Equals
	"ne", // Not equals
	"like", // Pattern matching (contains)
	"in", // In list (multiple values)
	"gt", // Greater than
	"gte", // Greater than or equal
	"lt", // Less than
	"lte", // Less than or equal
] as const;

/**
 * Filter operator type
 */
export type FilterOperator = (typeof FILTER_OPERATORS)[number];

/**
 * Salesforce field path validation regex
 * Validates field paths like:
 * - Simple fields: "Name", "FieldName__c"
 * - Relationship fields: "Account__r.Name", "Owner__r.FieldName__c"
 * - Nested relationships: "Account__r.Owner__r.Name"
 *
 * Pattern explanation:
 * - ^[A-Za-z][A-Za-z0-9_]* - Starts with letter, followed by letters/numbers/underscores
 * - (__[cr])? - Optional relationship suffix (__r or __c)
 * - (\.[A-Za-z][A-Za-z0-9_]*(__[cr])?)* - Optional relationship traversal (dot notation)
 */
const SALESFORCE_FIELD_PATH_REGEX =
	/^[A-Za-z][A-Za-z0-9_]*(__[cr])?(\.[A-Za-z][A-Za-z0-9_]*(__[cr])?)*$/;

/**
 * Validates Salesforce field path format
 * @param fieldPath - The field path to validate
 * @returns true if valid, false otherwise
 */
function isValidSalesforceFieldPath(fieldPath: string): boolean {
	if (!fieldPath || fieldPath.trim().length === 0) {
		return false;
	}
	return SALESFORCE_FIELD_PATH_REGEX.test(fieldPath);
}

// Zod Schema for Filter Attributes
const FilterAttributesSchema = z.object({
	affordance: z.string().optional(),
	placeholder: z.string().optional(),
});

/**
 * Filter attributes containing input-specific properties
 */
export type FilterAttributes = z.infer<typeof FilterAttributesSchema>;

// Zod Schema for Filter
const FilterSchema = z.object({
	affordance: z.string(),
	attributes: FilterAttributesSchema.optional(),
	defaultValues: z.array(z.string()).optional(),
	helpMessage: z.string().nullable().optional(),
	label: z.string(),
	targetFieldPath: z.string().refine((value) => isValidSalesforceFieldPath(value), {
		message:
			"Invalid Salesforce field path format. Field paths must start with a letter and can contain letters, numbers, underscores, and relationship notation (__r or __c). Use dot notation for relationships (e.g., 'Account__r.Name').",
	}),
	type: z.string(),
});

/**
 * Single filter definition from getObjectListFilters API
 */
export type Filter = z.infer<typeof FilterSchema>;

// Export schema for validation
export const FilterArraySchema = z.array(FilterSchema);

// Zod Schema for Filter Criteria with operator and field path validation
const FilterCriteriaSchema = z.object({
	objectApiName: z.string().min(1, "Object API name is required"),
	fieldPath: z
		.string()
		.min(1, "Field path is required")
		.refine((value) => isValidSalesforceFieldPath(value), {
			message:
				"Invalid Salesforce field path format. Field paths must start with a letter and can contain letters, numbers, underscores, and relationship notation (__r or __c). Use dot notation for relationships (e.g., 'Account__r.Name').",
		}),
	operator: z.enum(FILTER_OPERATORS, {
		message: `Operator must be one of: ${FILTER_OPERATORS.join(", ")}`,
	}),
	values: z.array(z.union([z.string(), z.number()])).min(1, "At least one value is required"),
});

/**
 * Filter criteria structure for filtering search results
 */
export type FilterCriteria = z.infer<typeof FilterCriteriaSchema>;

// Export schema for validation
export const FilterCriteriaArraySchema = z.array(FilterCriteriaSchema);

// Zod Schema for Filters Response
const FiltersResponseSchema = z.record(z.string(), z.unknown()).and(
	z.object({
		filters: FilterArraySchema.optional(),
	}),
);

/**
 * Filters response structure
 */
export type FiltersResponse = z.infer<typeof FiltersResponseSchema>;
