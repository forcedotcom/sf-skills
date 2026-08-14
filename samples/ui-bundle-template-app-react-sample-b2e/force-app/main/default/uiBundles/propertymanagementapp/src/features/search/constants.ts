/**
 * Minimum trimmed keyword length before a search fires. Both the SObject and
 * CMS search backends reject terms shorter than this (returning errors that the
 * UI would otherwise render as "Search failed for this source." on every
 * source), so the query is gated client-side until the user types at least this
 * many characters. Shared so every `<Search>` consumer inherits the same floor.
 */
export const MIN_QUERY_LENGTH = 3;
