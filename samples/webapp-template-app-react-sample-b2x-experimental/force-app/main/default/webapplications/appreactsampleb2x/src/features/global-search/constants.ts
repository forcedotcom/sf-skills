/**
 * Application-wide Constants
 *
 * Defines constants used throughout the global search feature.
 */

/**
 * Object API names to search across in the global search feature.
 * Currently supports single object search.
 *
 * @remarks
 * - Array of Salesforce object API names
 * - First element is used as the primary search object
 * - Can be extended to support multiple objects in the future
 *
 * @example
 * ```tsx
 * const objectApiName = OBJECT_API_NAMES[0]; // 'Account'
 * ```
 */
export const OBJECT_API_NAMES = ["Account"] as const;

/** Fallback title when record display name cannot be resolved (e.g. before load or no name field). */
export const DEFAULT_DETAIL_PAGE_TITLE = "Untitled";

/**
 * Default page size for search results pagination.
 * This should match one of the values in PAGE_SIZE_OPTIONS from paginationUtils.
 *
 * @remarks
 * - Default value is 20 (second option in PAGE_SIZE_OPTIONS)
 * - Can be changed by user via pagination controls
 *
 * @example
 * ```tsx
 * const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
 * ```
 */
export const DEFAULT_PAGE_SIZE = 20;
