/**
 * Alternative detail rendering: layout sections → rows → items → label/value grid.
 *
 * Use when you have raw Layout API response + record and do not need the full
 * layoutTransformUtils + formDataTransformUtils pipeline. The primary detail view
 * (DetailPage) uses DetailForm via UiApiDetailForm; use this component for other
 * entry points that already have layout + record in hand.
 */
import type { LayoutResponse } from "../../types/recordDetail/recordDetail";
import type { SearchResultRecordData } from "../../types/search/searchResults";
import { getNestedFieldValue } from "../../utils/fieldUtils";

interface DetailLayoutSectionsProps {
	layout: LayoutResponse;
	record: SearchResultRecordData;
}

interface FieldEntry {
	key: string;
	label: string;
	value: string | number | boolean | null;
}

function getSectionFieldEntries(
	section: LayoutResponse["sections"][number],
	record: SearchResultRecordData,
): FieldEntry[] {
	const entries: FieldEntry[] = [];
	section.layoutRows.forEach((row, rowIdx) => {
		row.layoutItems.forEach((item, itemIdx) => {
			item.layoutComponents.forEach((comp, compIdx) => {
				if (comp.componentType !== "Field" || !comp.apiName) return;
				const value = getNestedFieldValue(record.fields, comp.apiName);
				const label = comp.label ?? item.label;
				entries.push({
					key: `${section.id}-${rowIdx}-${itemIdx}-${comp.apiName ?? compIdx}`,
					label: label || comp.apiName,
					value: value ?? null,
				});
			});
		});
	});
	return entries;
}

export default function DetailLayoutSections({ layout, record }: DetailLayoutSectionsProps) {
	return (
		<div className="space-y-8" role="region" aria-label="Record details">
			{layout.sections.map((section) => {
				const entries = getSectionFieldEntries(section, record);
				if (entries.length === 0) return null;

				return (
					<section
						key={section.id}
						className="space-y-4"
						aria-labelledby={section.useHeading ? `section-${section.id}` : undefined}
					>
						{section.useHeading && section.heading ? (
							<h3
								id={`section-${section.id}`}
								className="text-base font-semibold text-foreground border-b pb-2"
							>
								{section.heading}
							</h3>
						) : null}
						<dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
							{entries.map(({ key, label, value }) => (
								<div key={key} className="flex flex-col gap-1">
									<dt className="text-sm font-medium text-muted-foreground">{label}</dt>
									<dd className="text-sm text-foreground">{value || "—"}</dd>
								</div>
							))}
						</dl>
					</section>
				);
			})}
		</div>
	);
}
