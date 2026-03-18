/**
 * Alternative detail rendering: columns + record → label/value list.
 *
 * Use when you have list columns + record (e.g. from filters-derived columns + searchResults)
 * and do not need the Layout API. The primary detail view (DetailPage) uses DetailForm
 * via UiApiDetailForm (layout + GraphQL record).
 *
 * @param record - Record data to display
 * @param columns - Column definitions (e.g. derived from getObjectListFilters)
 */
import type { Column, SearchResultRecordData } from "../../types/search/searchResults";
import { getNestedFieldValue } from "../../utils/fieldUtils";

interface DetailFieldsProps {
	record: SearchResultRecordData;
	columns: Column[];
}

function hasVisibleValue(value: string | number | boolean | null | undefined): boolean {
	return value !== null && value !== undefined && value !== "";
}

export default function DetailFields({ record, columns }: DetailFieldsProps) {
	const rows = columns.filter(
		(col) =>
			col?.fieldApiName && hasVisibleValue(getNestedFieldValue(record.fields, col.fieldApiName)),
	);

	if (columns.length > 0 && rows.length === 0) {
		return (
			<div role="status" className="text-sm text-muted-foreground py-4">
				No field values to display
			</div>
		);
	}

	return (
		<dl className="space-y-4" role="list">
			{rows.map((column) => {
				const fieldApiName = column.fieldApiName as string;
				const displayValue = getNestedFieldValue(record.fields, fieldApiName);
				return (
					<div key={fieldApiName} className="border-b pb-4 last:border-0" role="listitem">
						<div className="flex flex-col sm:flex-row sm:items-start gap-2">
							<dt className="font-semibold text-sm text-muted-foreground min-w-[150px]">
								{column.label || fieldApiName}:
							</dt>
							<dd className="text-sm text-foreground flex-1">{displayValue}</dd>
						</div>
					</div>
				);
			})}
		</dl>
	);
}
