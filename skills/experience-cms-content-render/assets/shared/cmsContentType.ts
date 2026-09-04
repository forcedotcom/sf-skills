/**
 * {{Type}} — per-type typed module (codegen-managed). ABOVE marker: user-editable
 * (layouts, slots, className presets), preserved verbatim. BELOW marker: generated
 * from the schema, rewritten on every Schema Sync. Missing/malformed markers → the
 * skill HALTs (never auto-heals). Algorithm: references/schema-sync.md.
 *
 * Tokens: {{Type}} PascalCase · {{type}} camelCase · {{TYPE}} UPPER_SNAKE.
 */
import type { CmsFieldType, CmsImageField } from '../../shared/cmsCore.types';

// <experience-cms-content-render:above-begin>
// User-editable — layouts, slot overrides, className presets.
// Preserved across regeneration.

export const {{type}}Layouts = {
  card: { fields: ['title', 'bannerImage', 'excerpt'] as const, className: 'cms-{{type}}-card' },
  detail: { fields: undefined, className: 'cms-{{type}}-detail' },
} as const;

export type {{Type}}Layout = keyof typeof {{type}}Layouts;

export const {{type}}Slots: {
  Title?: unknown;
  Image?: unknown;
  RichText?: unknown;
} = {};

// <experience-cms-content-render:above-end>


// <experience-cms-content-render:below-begin>
// GENERATED — do not edit. Regenerated on schema sync.
//
// One field per schema entry. Scalars are PLAIN PRIMITIVES (Rule 5) — Text/RichText/
// URL/Date/DateTime → string, Number → number, Boolean → boolean; only Image →
// CmsImageField. NEVER `{ value: T }`.

export interface {{Type}}Body {
  // One typed property per schema field; the index keeps off-schema fields open.
  [field: string]: string | number | boolean | CmsImageField | undefined;
}

export const {{type}}FieldTypes: Readonly<Record<string, CmsFieldType>> = {
  // One entry per field, mapping lightningType → lowerCamel CmsFieldType literal
  // (Text→'text', RichText→'richText', … — translate the casing, never copy the
  // PascalCase token). E.g.: body: 'richText', excerpt: 'text', bannerImage: 'image'.
};

// <experience-cms-content-render:below-end>
