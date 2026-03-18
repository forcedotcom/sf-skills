/**
 * Transforms Layout API sections into a structure for the detail form: section → rows → items.
 * Uses layout response (sections, layoutRows, layoutItems, layoutComponents) and optional
 * object info for compound field names and dataType. Section merge when useHeading === false.
 */

import type { LayoutSection, LayoutRow, LayoutItem } from "../types/recordDetail/recordDetail";

const HIDE_EMPTY_SECTIONS = true;
const EMPTY_OPTIONS: PicklistOption[] = [];

export interface ObjectInfoField {
	compoundFieldName?: string;
	dataType?: string;
}

export interface ObjectInfo {
	apiName?: string;
	fields?: Record<string, ObjectInfoField>;
}

/** Picklist/lookup options for a field (e.g. [{ label, value }]). */
export type PicklistOption = {
	label: string | null;
	value: string | number | boolean;
	validFor?: unknown[];
};

export interface LayoutTransformContext {
	recordId: string;
	objectInfo?: ObjectInfo | null;
	lookupRecords?: Record<string, PicklistOption[] | null> | null;
	getSectionCollapsedState: (sectionId: string) => boolean;
	calculatePicklistValues?: (itemApiName: string, item: LayoutItem) => PicklistOption[] | null;
	formOverrides?: { fieldVariant?: string } | null;
}

export interface TransformedLayoutItem {
	key: string;
	isField: boolean;
	label?: string;
	required?: boolean;
	readOnly?: boolean;
	apiName?: string;
	contextName?: string;
	options?: PicklistOption[];
	variant?: string;
	dataType?: string;
	layoutComponentApiNames?: string[];
}

/** Single row in a section. */
export interface TransformedLayoutRow {
	key: string;
	layoutItems: TransformedLayoutItem[];
}

/** Section ready for Section/SectionRow rendering. */
export interface TransformedSection {
	id: string;
	key: string;
	heading: string;
	useHeading: boolean;
	collapsible: boolean;
	collapsed: boolean;
	layoutRows: TransformedLayoutRow[];
}

export function createSectionKey(index: number): string {
	return "section-" + index;
}

export function getTransformedSections(
	sections: LayoutSection[],
	transformContext: LayoutTransformContext,
): TransformedSection[] {
	const calculatedSections: TransformedSection[] = [];
	let previousSection: TransformedSection | null = null;

	sections.forEach((section, index) => {
		if (previousSection !== null && section.useHeading === false) {
			const sectionKey = createSectionKey(index);
			const appendedRows = section.layoutRows
				.map((row, i) => rowTransform(row, i, sectionKey, transformContext))
				.filter((r): r is TransformedLayoutRow => r !== null);
			previousSection.layoutRows.push(...appendedRows);
			return;
		}

		const newSection = sectionTransform(section, index, transformContext);
		if (newSection) {
			calculatedSections.push(newSection);
			previousSection = newSection;
		}
	});

	return calculatedSections;
}

export function sectionTransform(
	section: LayoutSection,
	index: number,
	transformContext: LayoutTransformContext,
): TransformedSection | null {
	const { getSectionCollapsedState } = transformContext;
	const sectionKey = createSectionKey(index);
	const layoutRows = section.layoutRows
		.map((row, i) => rowTransform(row, i, sectionKey, transformContext))
		.filter((r): r is TransformedLayoutRow => r !== null);

	if (layoutRows.length === 0 && HIDE_EMPTY_SECTIONS) {
		return null;
	}

	return {
		key: sectionKey,
		collapsible: section.collapsible,
		collapsed: getSectionCollapsedState(section.id),
		useHeading: section.useHeading,
		heading: section.heading,
		id: section.id,
		layoutRows,
	};
}

export function rowTransform(
	row: LayoutRow,
	index: number,
	sectionKey: string,
	transformContext: LayoutTransformContext,
): TransformedLayoutRow | null {
	const layoutItems = row.layoutItems.map((item, i) => transformItem(item, i, transformContext));

	const allItemsHaveNoComponents = layoutItems.every((item) => !item.apiName || !item.isField);
	if (allItemsHaveNoComponents) {
		return null;
	}
	return {
		key: sectionKey + "-" + index,
		layoutItems,
	};
}

export function transformItem(
	item: LayoutItem,
	index: number,
	transformContext: LayoutTransformContext,
): TransformedLayoutItem {
	const { recordId, objectInfo, lookupRecords, calculatePicklistValues, formOverrides } =
		transformContext;

	let itemApiName: string | undefined;
	let itemComponentType: string | undefined;

	if (item.layoutComponents.length >= 1) {
		const itemComponent = item.layoutComponents[0];
		itemComponentType = itemComponent.componentType;
		const componentApiName = itemComponent.apiName;
		const topLevelCompoundName =
			item.layoutComponents.length > 1 &&
			componentApiName &&
			objectInfo?.fields?.[componentApiName]?.compoundFieldName;
		if (topLevelCompoundName) {
			itemApiName = topLevelCompoundName;
		} else {
			itemApiName = componentApiName ?? undefined;
		}
	}

	const lookupOptions =
		itemApiName != null && lookupRecords?.[itemApiName] != null ? lookupRecords[itemApiName] : null;

	const isFieldType = itemComponentType === "Field";

	const options: PicklistOption[] =
		lookupOptions ??
		(itemApiName ? (calculatePicklistValues?.(itemApiName, item) ?? null) : null) ??
		EMPTY_OPTIONS;

	const fieldMeta = itemApiName ? objectInfo?.fields?.[itemApiName] : undefined;
	const layoutComponentApiNames = item.layoutComponents
		.filter((c) => c.componentType === "Field" && c.apiName != null)
		.map((c) => c.apiName as string);

	let newItem: TransformedLayoutItem = {
		key: "item-" + index,
		apiName: itemApiName,
		contextName: recordId,
		label: item.label,
		required: item.required,
		variant: formOverrides?.fieldVariant ?? "label-stacked",
		readOnly: !item.editableForUpdate,
		isField: isFieldType,
		options,
		dataType: fieldMeta?.dataType,
		layoutComponentApiNames:
			layoutComponentApiNames.length > 0 ? layoutComponentApiNames : undefined,
	};

	if (objectInfo?.apiName?.endsWith("__kav")) {
		newItem = { ...newItem, readOnly: true };
	}

	if (newItem.required === true && newItem.readOnly === true) {
		newItem = { ...newItem, required: false };
	}

	return newItem;
}

export function layoutReducer<T>(
	sections: TransformedSection[],
	reducer: (
		acc: T,
		ctx: {
			section: TransformedSection;
			layoutRow: TransformedLayoutRow;
			layoutItem: TransformedLayoutItem;
		},
	) => T,
	initialValue: T,
): T {
	let accumulator = initialValue;
	sections.forEach((section) =>
		section.layoutRows.forEach((layoutRow) =>
			layoutRow.layoutItems.forEach((layoutItem) => {
				accumulator = reducer(accumulator, {
					section,
					layoutRow,
					layoutItem,
				});
			}),
		),
	);
	return accumulator;
}
