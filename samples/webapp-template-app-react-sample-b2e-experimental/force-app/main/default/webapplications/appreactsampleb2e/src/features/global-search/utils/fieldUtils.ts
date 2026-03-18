/**
 * Field value extraction and formatting for Salesforce UI API record shapes.
 * Handles primitives, nested paths (e.g. Owner.Alias), reference/relationship display,
 * address and modstamp compound formatting, and layout-item value clubbing.
 */

import type { FieldValue, ComplexFieldValue } from "../types/search/searchResults";

/** Fallback field names for reference/relationship display when object info nameFields are not available. */
const DISPLAY_FIELD_CANDIDATES = [
	"Name",
	"CaseNumber",
	"Subject",
	"Title",
	"DeveloperName",
	"ContractNumber",
] as const;

function isDefined(val: unknown): val is string | number | boolean {
	return val !== null && val !== undefined;
}

function isComplexValue(val: unknown): val is ComplexFieldValue {
	return typeof val === "object" && val !== null && "fields" in val;
}

function extractComplexValue(complex: ComplexFieldValue): string | null {
	const fields = complex.fields;
	if (!fields) return null;

	for (const fieldName of DISPLAY_FIELD_CANDIDATES) {
		const field = fields[fieldName];
		if (field) {
			if (isDefined(field.displayValue)) {
				return field.displayValue;
			}
			if (isDefined(field.value)) {
				return field.value.toString();
			}
		}
	}

	return null;
}

function extractFieldPrimitive(field: FieldValue): string | number | boolean | null {
	if (isDefined(field.displayValue)) {
		return field.displayValue;
	}

	if (isComplexValue(field.value)) {
		const extracted = extractComplexValue(field.value);
		return extracted !== null ? extracted : null;
	}

	if (isDefined(field.value)) {
		return field.value;
	}

	return null;
}

export type FieldValueWithRelationship = FieldValue & {
	relationshipField?: FieldValue | null;
	constituents?: Record<string, FieldValue>;
};

/** Id + Date pairs for Created By / Last Modified By (UI API modstamp convention). */
const MODSTAMP_FIELDS = [
	{ idFieldName: "CreatedById", dateFieldName: "CreatedDate" },
	{ idFieldName: "LastModifiedById", dateFieldName: "LastModifiedDate" },
] as const;

function isModstampConstituents(constituents: Record<string, FieldValue>): boolean {
	return MODSTAMP_FIELDS.some(
		({ idFieldName, dateFieldName }) =>
			idFieldName in constituents && dateFieldName in constituents,
	);
}

/**
 * Formats an ISO 8601 date-time string to the user's locale and timezone.
 * Uses the browser's default locale and local timezone.
 */
export function formatDateTimeForDisplay(isoOrDateString: string): string {
	if (!isoOrDateString || typeof isoOrDateString !== "string") return isoOrDateString;
	const trimmed = isoOrDateString.trim();
	if (!trimmed) return isoOrDateString;
	const date = new Date(trimmed);
	if (Number.isNaN(date.getTime())) return isoOrDateString;
	try {
		return new Intl.DateTimeFormat(undefined, {
			dateStyle: "medium",
			timeStyle: "short",
		}).format(date);
	} catch {
		return isoOrDateString;
	}
}

function formatModstampDisplay(constituents: Record<string, FieldValue>): string {
	for (const { idFieldName, dateFieldName } of MODSTAMP_FIELDS) {
		const idField = constituents[idFieldName];
		const dateField = constituents[dateFieldName];
		if (!idField || !dateField) continue;
		const idWithRel = idField as FieldValueWithRelationship;
		const name =
			idWithRel.relationshipField != null
				? getPrimitiveString(idWithRel.relationshipField)
				: getPrimitiveString(idField);
		const dateRaw = getPrimitiveString(dateField);
		const date = dateRaw ? formatDateTimeForDisplay(dateRaw) : "";
		const parts = [name, date].filter(Boolean);
		if (parts.length) return parts.join(" ");
	}
	return "";
}

const ADDRESS_STREET_SUFFIXES = ["Street"];
const ADDRESS_CITY_SUFFIXES = ["City"];
const ADDRESS_STATE_SUFFIXES = ["State", "StateCode"];
const ADDRESS_POSTAL_SUFFIXES = ["PostalCode"];
const ADDRESS_COUNTRY_SUFFIXES = ["Country", "CountryCode"];

function getPrimitiveString(fv: FieldValue | undefined): string {
	if (!fv) return "";
	const p = extractFieldPrimitive(fv);
	return ((p as string) || "").trim();
}

function fieldNameEndsWithOneOf(name: string, suffixes: string[]): boolean {
	return suffixes.some(
		(s) =>
			name === s || name.endsWith(s) || (name.endsWith("__c") && name.slice(0, -3).endsWith(s)),
	);
}

function findAddressPartKey(keys: string[], suffixes: string[]): string | undefined {
	return keys.find((k) => fieldNameEndsWithOneOf(k, suffixes));
}

export interface AddressParts {
	street: string;
	city: string;
	state: string;
	postalCode: string;
	country: string;
}

export function getAddressPartsFromConstituents(
	constituents: Record<string, FieldValue>,
): AddressParts {
	const keys = Object.keys(constituents);
	const streetKey = findAddressPartKey(keys, ADDRESS_STREET_SUFFIXES);
	const cityKey = findAddressPartKey(keys, ADDRESS_CITY_SUFFIXES);
	const stateKey = findAddressPartKey(keys, ADDRESS_STATE_SUFFIXES);
	const postalKey = findAddressPartKey(keys, ADDRESS_POSTAL_SUFFIXES);
	const countryKey = findAddressPartKey(keys, ADDRESS_COUNTRY_SUFFIXES);
	return {
		street: streetKey ? getPrimitiveString(constituents[streetKey]) : "",
		city: cityKey ? getPrimitiveString(constituents[cityKey]) : "",
		state: stateKey ? getPrimitiveString(constituents[stateKey]) : "",
		postalCode: postalKey ? getPrimitiveString(constituents[postalKey]) : "",
		country: countryKey ? getPrimitiveString(constituents[countryKey]) : "",
	};
}

export function isAddressConstituents(constituents: Record<string, FieldValue>): boolean {
	const keys = Object.keys(constituents);
	const hasStreet = !!findAddressPartKey(keys, ADDRESS_STREET_SUFFIXES);
	const hasCity = !!findAddressPartKey(keys, ADDRESS_CITY_SUFFIXES);
	const hasState = !!findAddressPartKey(keys, ADDRESS_STATE_SUFFIXES);
	const hasCountry = !!findAddressPartKey(keys, ADDRESS_COUNTRY_SUFFIXES);
	return hasStreet && (hasCity || hasState || hasCountry);
}

export function formatAddressDisplay(parts: AddressParts): string {
	const { street, city, state, postalCode, country } = parts;
	const statePostal = [state, postalCode].filter(Boolean).join(" ");
	const line2 = city ? (statePostal ? `${city}, ${statePostal}` : city) : statePostal;
	const lines = [street, line2, country].filter(Boolean);
	return lines.join("\n").trim();
}

export function formatAddressFromConstituents(constituents: Record<string, FieldValue>): string {
	const parts = getAddressPartsFromConstituents(constituents);
	return formatAddressDisplay(parts);
}

function isModstampApiNames(apiNames: string[]): boolean {
	return MODSTAMP_FIELDS.some(
		({ idFieldName, dateFieldName }) =>
			apiNames.includes(idFieldName) && apiNames.includes(dateFieldName),
	);
}

function isAddressApiNames(apiNames: string[]): boolean {
	const hasStreet = apiNames.some((n) => fieldNameEndsWithOneOf(n, ADDRESS_STREET_SUFFIXES));
	const hasCity = apiNames.some((n) => fieldNameEndsWithOneOf(n, ADDRESS_CITY_SUFFIXES));
	const hasState = apiNames.some((n) => fieldNameEndsWithOneOf(n, ADDRESS_STATE_SUFFIXES));
	const hasCountry = apiNames.some((n) => fieldNameEndsWithOneOf(n, ADDRESS_COUNTRY_SUFFIXES));
	return hasStreet && (hasCity || hasState || hasCountry);
}

export interface LayoutItemDisplayResult {
	value: string | number | boolean | null;
	dataType?: string;
}

export function getDisplayValueForLayoutItem(
	fields: Record<string, FieldValue> | undefined,
	componentApiNames: string[],
): LayoutItemDisplayResult {
	if (!fields || componentApiNames.length === 0) {
		return { value: null };
	}
	if (componentApiNames.length === 1) {
		const value = getDisplayValueForDetailField(
			fields[componentApiNames[0]] as FieldValueWithRelationship | undefined,
		);
		return { value };
	}
	const constituents: Record<string, FieldValue> = {};
	for (const apiName of componentApiNames) {
		if (fields[apiName] != null) constituents[apiName] = fields[apiName];
	}
	if (isModstampApiNames(componentApiNames)) {
		const value = formatModstampDisplay(constituents);
		return { value: value || null };
	}
	if (isAddressApiNames(componentApiNames)) {
		const parts = getAddressPartsFromConstituents(constituents);
		const value = formatAddressDisplay(parts);
		return { value: value || null, dataType: "Address" };
	}
	const values = componentApiNames
		.map((apiName) =>
			getDisplayValueForDetailField(fields[apiName] as FieldValueWithRelationship | undefined),
		)
		.filter((v) => v !== null && v !== undefined && v !== "");
	return { value: values.length > 0 ? values.join(", ") : null };
}

export function getDisplayValueForDetailField(
	field: FieldValueWithRelationship | undefined,
): string | number | boolean | null {
	if (!field) return null;
	const withExt = field as FieldValueWithRelationship;
	if (withExt.relationshipField != null) {
		const fromRel = extractFieldPrimitive(withExt.relationshipField);
		if (fromRel !== null && fromRel !== undefined && fromRel !== "") {
			return fromRel;
		}
	}
	if (withExt.constituents != null) {
		if (isModstampConstituents(withExt.constituents)) {
			const formatted = formatModstampDisplay(withExt.constituents);
			if (formatted) return formatted;
		} else if (isAddressConstituents(withExt.constituents)) {
			const formatted = formatAddressFromConstituents(withExt.constituents);
			if (formatted) return formatted;
		}
	}
	return extractFieldPrimitive(field);
}

export function getNestedFieldValue(
	fields: Record<string, FieldValue> | undefined,
	fieldPath: string,
): string | number | boolean | null {
	if (!fields || !fieldPath) {
		return null;
	}

	const pathParts = fieldPath.split(".");
	if (pathParts.length === 1) {
		const field = fields[fieldPath];
		if (!field) return null;

		return extractFieldPrimitive(field);
	}

	let currentFields: Record<string, FieldValue> | undefined = fields;
	for (let i = 0; i < pathParts.length - 1; i++) {
		const part = pathParts[i];
		if (!currentFields || !currentFields[part]) {
			return null;
		}

		const field: FieldValue = currentFields[part];
		if (isComplexValue(field.value)) {
			currentFields = field.value.fields;
		} else {
			return null;
		}
	}

	const finalFieldName = pathParts[pathParts.length - 1];
	if (!currentFields || !currentFields[finalFieldName]) {
		return null;
	}

	const finalField = currentFields[finalFieldName];
	return extractFieldPrimitive(finalField);
}

/** Minimal metadata for record display name (nameFields from object info API). */
export type RecordDisplayNameMetadata = { nameFields?: string[] } | null;

/**
 * Resolves a display name for a record: tries metadata.nameFields first, then
 * DISPLAY_FIELD_CANDIDATES (Name, Subject, etc.), then record.id.
 */
export function getRecordDisplayName(
	record: { id: string; fields: Record<string, FieldValue> },
	metadata?: RecordDisplayNameMetadata,
): string {
	const candidates = [...(metadata?.nameFields ?? []), ...DISPLAY_FIELD_CANDIDATES];
	for (const fieldPath of candidates) {
		const v = getNestedFieldValue(record.fields, fieldPath);
		return v as string;
	}
	return record.id;
}

/** Adapts object info (e.g. ObjectInfoResult) to the shape expected by getRecordDisplayName. */
export function toRecordDisplayNameMetadata(obj: unknown): RecordDisplayNameMetadata {
	if (obj != null && typeof obj === "object" && "nameFields" in obj) {
		const nameFields = (obj as { nameFields?: string[] }).nameFields;
		if (Array.isArray(nameFields)) return { nameFields };
	}
	return null;
}

export function extractFieldValue(
	fieldValue: FieldValue | undefined,
	useDisplayValue: boolean = false,
): string {
	if (!fieldValue) {
		return "—";
	}

	if (useDisplayValue && isDefined(fieldValue.displayValue)) {
		return fieldValue.displayValue;
	}

	const extracted = extractFieldPrimitive(fieldValue);

	if (extracted !== null) {
		return extracted as string;
	}

	return "—";
}
