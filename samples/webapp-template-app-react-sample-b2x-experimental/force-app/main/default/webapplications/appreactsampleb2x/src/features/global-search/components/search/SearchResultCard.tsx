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
import React from "react";
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

	const validColumns = useMemo(
		() => (columns && Array.isArray(columns) && columns.length > 0 ? columns : []),
		[columns],
	);
	const validRecord =
		record?.id && record?.fields && typeof record.fields === "object" ? record : null;

	const detailPath = useMemo(
		() =>
			validRecord
				? `/object/${objectApiName?.trim() || OBJECT_API_NAMES[0]}/${validRecord.id}`
				: "",
		[validRecord, objectApiName],
	);

	const handleClick = useCallback(() => {
		if (validRecord?.id) navigate(detailPath);
	}, [validRecord?.id, detailPath, navigate]);

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
			validColumns.find(
				(col) =>
					col &&
					col.fieldApiName &&
					(col.fieldApiName.toLowerCase() === "name" ||
						col.fieldApiName.toLowerCase().includes("name")),
			) ||
			validColumns[0] ||
			null
		);
	}, [validColumns]);

	const primaryValue = useMemo(() => {
		return primaryField && primaryField.fieldApiName && validRecord?.fields
			? getNestedFieldValue(validRecord.fields, primaryField.fieldApiName) || "Untitled"
			: "Untitled";
	}, [primaryField, validRecord]);

	const secondaryColumns = useMemo(() => {
		return validColumns.filter(
			(col) => col && col.fieldApiName && col.fieldApiName !== primaryField?.fieldApiName,
		);
	}, [validColumns, primaryField]);

	if (!validRecord) return null;
	if (validColumns.length === 0) return null;

	return (
		<Card
			className="cursor-pointer hover:shadow-md transition-shadow focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2"
			onClick={handleClick}
			onKeyDown={handleKeyDown}
			role="button"
			tabIndex={0}
			aria-label={`View details for ${primaryValue}`}
			aria-describedby={`result-${validRecord.id}-description`}
		>
			<CardHeader>
				<CardTitle className="text-lg" id={`result-${validRecord.id}-title`}>
					{primaryValue}
				</CardTitle>
			</CardHeader>
			<CardContent>
				<div id={`result-${validRecord.id}-description`} className="sr-only">
					Search result: {primaryValue}
				</div>
				<ResultCardFields
					record={validRecord}
					columns={secondaryColumns}
					excludeFieldApiName={primaryField?.fieldApiName}
				/>
			</CardContent>
		</Card>
	);
}
