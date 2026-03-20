import { useState, useCallback, useMemo, useId } from "react";
import type { LayoutResponse } from "../../types/recordDetail/recordDetail";
import type { GraphQLRecordNode } from "../../api/recordListGraphQLService";
import {
	getDisplayValueForLayoutItemFromNode,
	getDisplayValueForDetailFieldFromNode,
} from "../../utils/graphQLNodeFieldUtils";
import type { ObjectInfoMetadata } from "../../utils/formDataTransformUtils";
import {
	getTransformedSections,
	type LayoutTransformContext,
	type ObjectInfo,
	type PicklistOption,
	type TransformedLayoutItem,
} from "../../utils/layoutTransformUtils";
import { FieldValueDisplay } from "./formatted/FieldValueDisplay";
import { Section } from "./Section";
import { SectionRow } from "./SectionRow";

export interface DetailFormProps {
	layout: LayoutResponse;
	record: GraphQLRecordNode;
	metadata?: ObjectInfoMetadata | null;
	objectInfo?: ObjectInfo | null;
	lookupRecords?: Record<string, PicklistOption[] | null> | null;
	showSectionHeaders?: boolean;
	collapsibleSections?: boolean;
}

function FieldCell({
	item,
	record,
	metadata,
}: {
	item: TransformedLayoutItem;
	record: GraphQLRecordNode;
	metadata?: ObjectInfoMetadata | null;
}) {
	if (!item.isField || item.apiName == null) return null;
	const label = item.label ?? item.apiName;
	const hasComponents = item.layoutComponentApiNames && item.layoutComponentApiNames.length > 0;
	const layoutResult = hasComponents
		? getDisplayValueForLayoutItemFromNode(
				record,
				item.layoutComponentApiNames as string[],
				metadata,
			)
		: null;
	const value = hasComponents
		? (layoutResult?.value ?? null)
		: getDisplayValueForDetailFieldFromNode(record, item.apiName, metadata);
	const dataType =
		(hasComponents ? layoutResult?.dataType : undefined) ?? item.dataType ?? undefined;
	const labelId = useId();
	const valueId = useId();
	return (
		<div
			className="flex flex-col gap-1"
			role="group"
			aria-labelledby={labelId}
			aria-describedby={valueId}
		>
			<dt id={labelId} className="text-sm font-medium text-muted-foreground">
				{label}
			</dt>
			<dd id={valueId} className="text-sm text-foreground">
				<FieldValueDisplay value={value} dataType={dataType} />
			</dd>
		</div>
	);
}

/**
 * Read-only detail form: layout API + record (+ optional object info) drive sections, rows, and
 * field values. Uses layoutComponents to club multi-component items (address, Created By, etc.).
 */
export function DetailForm({
	layout,
	record,
	metadata = null,
	objectInfo = null,
	lookupRecords = null,
	showSectionHeaders = true,
	collapsibleSections = true,
}: DetailFormProps) {
	const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});

	const recordId = (record.Id as string) ?? "";

	const layoutObjectInfo = objectInfo ?? metadata;

	const transformContext: LayoutTransformContext = useMemo(
		() => ({
			recordId,
			objectInfo: layoutObjectInfo,
			lookupRecords,
			getSectionCollapsedState: (sectionId: string) => Boolean(collapsedSections[sectionId]),
		}),
		[recordId, layoutObjectInfo, lookupRecords, collapsedSections],
	);

	const computedSections = useMemo(
		() => getTransformedSections(layout.sections, transformContext),
		[layout.sections, transformContext],
	);

	const handleSectionToggle = useCallback((sectionId: string, collapsed: boolean) => {
		setCollapsedSections((prev) => ({ ...prev, [sectionId]: collapsed }));
	}, []);

	return (
		<div
			className="space-y-6"
			role="region"
			aria-label="Record details"
			aria-roledescription="Detail form"
		>
			{computedSections.map((section) => (
				<Section
					key={section.key}
					sectionId={section.id}
					titleLabel={section.heading}
					showHeader={showSectionHeaders && section.useHeading}
					collapsible={collapsibleSections && section.collapsible}
					collapsed={section.collapsed}
					onToggle={handleSectionToggle}
				>
					<div className="space-y-4">
						{section.layoutRows.map((row) => (
							<SectionRow key={row.key}>
								{row.layoutItems.map((item) => {
									const cellKey = `${section.key}-${row.key}-${item.apiName ?? item.key}`;
									return item.isField ? (
										<FieldCell key={cellKey} item={item} record={record} metadata={metadata} />
									) : (
										<div key={cellKey} className="min-h-[2.5rem]" aria-hidden="true" />
									);
								})}
							</SectionRow>
						))}
					</div>
				</Section>
			))}
		</div>
	);
}
