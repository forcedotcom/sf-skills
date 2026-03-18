/**
 * SearchResultCard Component
 *
 * Displays a single search result as a card with primary and secondary fields.
 * Clicking the card navigates to the detail page for that record.
 *
 * @param record - The search result record data to display
 * @param columns - Array of column definitions for field display
 * @param objectApiName - API name of the object (path param in detail URL: /object/:objectApiName/:recordId)
 *
 * @remarks
 * - Automatically identifies the primary field (usually "Name")
 * - Displays up to 3 secondary fields
 * - Supports keyboard navigation (Enter/Space to navigate)
 * - Handles nested field values (e.g., "Owner.Alias")
 *
 * @example
 * ```tsx
 * <SearchResultCard
 *   record={searchResult}
 *   columns={columns}
 *   objectApiName="Account"
 * />
 * ```
 */
import { useNavigate } from "react-router";
import { useMemo, useCallback } from "react";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../../../components/ui/card";
import type { Column, SearchResultRecordData } from "../../types/search/searchResults";
import { getNestedFieldValue } from "../../utils/fieldUtils";
import ResultCardFields from "./ResultCardFields";
import { OBJECT_API_NAMES } from "../../constants";

interface SearchResultCardProps {
	record: SearchResultRecordData;
	columns: Column[];
	objectApiName?: string;
}

export default function SearchResultCard({
	record,
	columns,
	objectApiName,
}: SearchResultCardProps) {
	const navigate = useNavigate();

	if (!record || !record.id) {
		return null;
	}

	if (!columns || !Array.isArray(columns) || columns.length === 0) {
		return null;
	}

	if (!record.fields || typeof record.fields !== "object") {
		return null;
	}

	const detailPath = useMemo(
		() => `/object/${objectApiName?.trim() || OBJECT_API_NAMES[0]}/${record.id}`,
		[record.id, objectApiName],
	);

	const handleClick = useCallback(() => {
		if (record.id) navigate(detailPath);
	}, [record.id, detailPath, navigate]);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				handleClick();
			}
		},
		[handleClick],
	);

	const primaryField = useMemo(() => {
		return (
			columns.find(
				(col) =>
					col &&
					col.fieldApiName &&
					(col.fieldApiName.toLowerCase() === "name" ||
						col.fieldApiName.toLowerCase().includes("name")),
			) ||
			columns[0] ||
			null
		);
	}, [columns]);

	const primaryValue = useMemo(() => {
		return primaryField && primaryField.fieldApiName
			? getNestedFieldValue(record.fields, primaryField.fieldApiName) || "Untitled"
			: "Untitled";
	}, [primaryField, record.fields]);

	const secondaryColumns = useMemo(() => {
		return columns.filter(
			(col) => col && col.fieldApiName && col.fieldApiName !== primaryField?.fieldApiName,
		);
	}, [columns, primaryField]);

	return (
		<Card
			className="cursor-pointer hover:shadow-md transition-shadow focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2"
			onClick={handleClick}
			onKeyDown={handleKeyDown}
			role="button"
			tabIndex={0}
			aria-label={`View details for ${primaryValue}`}
			aria-describedby={`result-${record.id}-description`}
		>
			<CardHeader>
				<CardTitle className="text-lg" id={`result-${record.id}-title`}>
					{primaryValue}
				</CardTitle>
			</CardHeader>
			<CardContent>
				<div id={`result-${record.id}-description`} className="sr-only">
					Search result: {primaryValue}
				</div>
				<ResultCardFields
					record={record}
					columns={secondaryColumns}
					excludeFieldApiName={primaryField?.fieldApiName}
				/>
			</CardContent>
		</Card>
	);
}
