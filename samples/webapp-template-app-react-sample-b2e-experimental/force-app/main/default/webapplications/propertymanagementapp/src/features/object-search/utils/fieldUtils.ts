export function fieldValue(
	field: { displayValue?: string | null; value?: unknown } | null | undefined,
): string | null {
	if (field?.displayValue != null) return field.displayValue;
	if (field?.value != null) return String(field.value);
	return null;
}

export function getAddressFieldLines(address: {
	street?: string | null;
	city?: string | null;
	state?: string | null;
	postalCode?: string | null;
	country?: string | null;
}) {
	const cityStateZip = [address.city, address.state].filter(Boolean).join(", ");
	const cityStateZipLine = [cityStateZip, address.postalCode].filter(Boolean).join(" ");
	const lines = [address.street, cityStateZipLine, address.country].filter(Boolean);
	if (lines.length === 0) return null;
	return lines;
}

export function formatDateTimeField(
	value?: string | null,
	...args: Parameters<Date["toLocaleString"]>
) {
	if (!value) return null;
	return new Date(value).toLocaleString(...args);
}
