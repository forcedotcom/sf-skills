/**
 * ResultCardFields Component
 *
 * Displays secondary fields (up to 3) for a search result card.
 * Excludes the primary field and handles nested field values.
 *
 * @param record - The search result record data
 * @param columns - Array of column definitions
 * @param excludeFieldApiName - Field API name to exclude (usually the primary field)
 *
 * @remarks
 * - Displays up to 3 secondary fields
 * - Handles nested field paths (e.g., "Owner.Alias")
 * - Skips fields with null/undefined/empty values
 * - Responsive layout (vertical on mobile, horizontal on desktop)
 *
 * @example
 * ```tsx
 * <ResultCardFields
 *   record={searchResult}
 *   columns={columns}
 *   excludeFieldApiName="Name"
 * />
 * ```
 */
import type { Column, SearchResultRecordData } from "../../types/search/searchResults";
import { getNestedFieldValue } from "../../utils/fieldUtils";

interface ResultCardFieldsProps {
	record: SearchResultRecordData;
	columns: Column[];
	excludeFieldApiName?: string;
}

export default function ResultCardFields({
	record,
	columns,
	excludeFieldApiName,
}: ResultCardFieldsProps) {
	const secondaryFields = columns.filter(
		(col) => col && col.fieldApiName && col.fieldApiName !== excludeFieldApiName,
	);

	return (
		<dl className="space-y-2" aria-label="Additional record information">
			{secondaryFields.map((column) => {
				if (!column || !column.fieldApiName) {
					return null;
				}

				const displayValue = getNestedFieldValue(record.fields, column.fieldApiName);

				if (displayValue === null || displayValue === undefined || displayValue === "") {
					return null;
				}

				return (
					<div
						key={column.fieldApiName}
						className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2"
					>
						<dt className="text-sm font-medium text-muted-foreground min-w-[100px]">
							{column.label || column.fieldApiName}:
						</dt>
						<dd className="text-sm text-foreground">{displayValue}</dd>
					</div>
				);
			})}
		</dl>
	);
}
