import { z } from "zod";

/**
 * Type definitions and Zod schemas for Record Detail APIs:
 * - Layout API (layout/{objectApiName}?layoutType=Full&mode=View&recordTypeId=...)
 * - Record API (records/{recordId}?optionalFields=...)
 */

const LayoutComponentSchema = z.object({
	apiName: z.string().nullable(),
	behavior: z.string().optional(),
	componentType: z.enum(["Field", "CustomLink", "EmptySpace"]),
	customLinkUrl: z.string().optional(),
	label: z.string().optional(),
});

export type LayoutComponent = z.infer<typeof LayoutComponentSchema>;

const LayoutItemSchema = z.object({
	editableForNew: z.boolean(),
	editableForUpdate: z.boolean(),
	label: z.string(),
	layoutComponents: z.array(LayoutComponentSchema),
	lookupIdApiName: z.string().nullable(),
	required: z.boolean(),
	sortable: z.boolean(),
	uiBehavior: z.string().nullable(),
});

export type LayoutItem = z.infer<typeof LayoutItemSchema>;

const LayoutRowSchema = z.object({
	layoutItems: z.array(LayoutItemSchema),
});

const LayoutSectionSchema = z.object({
	collapsible: z.boolean(),
	columns: z.number(),
	heading: z.string(),
	id: z.string(),
	layoutRows: z.array(LayoutRowSchema),
	rows: z.number(),
	tabOrder: z.string(),
	useHeading: z.boolean(),
});

export type LayoutSection = z.infer<typeof LayoutSectionSchema>;

export const LayoutResponseSchema = z.object({
	eTag: z.string(),
	id: z.string(),
	layoutType: z.string(),
	mode: z.string(),
	objectApiName: z.string(),
	recordTypeId: z.string(),
	saveOptions: z.array(z.unknown()).optional(),
	sections: z.array(LayoutSectionSchema),
});

export type LayoutResponse = z.infer<typeof LayoutResponseSchema>;
export type LayoutRow = z.infer<typeof LayoutRowSchema>;
