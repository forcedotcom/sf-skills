/**
 * Picks formatter by dataType (Address, Phone, Url, Email) or plain text. Empty values show "—" with a11y label.
 */
import { FormattedAddress } from "./FormattedAddress";
import { FormattedEmail } from "./FormattedEmail";
import { FormattedPhone } from "./FormattedPhone";
import { FormattedText } from "./FormattedText";
import { FormattedUrl } from "./FormattedUrl";

/** Salesforce UI API dataType values that have dedicated formatters. */
const DATA_TYPES = {
	Address: "Address",
	Email: "Email",
	Phone: "Phone",
	Url: "Url",
} as const;

/** Normalize dataType to canonical casing so "PHONE" / "phone" match Phone, etc. */
function normalizeDataType(dataType: string | undefined): string | undefined {
	if (dataType == null || dataType === "") return dataType;
	const lower = dataType.toLowerCase();
	const canonical: Record<string, string> = {
		phone: DATA_TYPES.Phone,
		email: DATA_TYPES.Email,
		url: DATA_TYPES.Url,
		address: DATA_TYPES.Address,
	};
	return canonical[lower] ?? dataType;
}

export interface FieldValueDisplayProps {
	/** Resolved display value (string, number, boolean, or null). */
	value: string | number | boolean | null | undefined;
	/** Field dataType from object info (e.g. Phone, Email, Url, Address). */
	dataType?: string;
	className?: string;
}

const DEFAULT_CLASS = "text-sm text-foreground";
const LINK_CLASS =
	"text-sm text-foreground text-primary underline underline-offset-2 hover:opacity-80";

export function FieldValueDisplay({
	value,
	dataType,
	className = DEFAULT_CLASS,
}: FieldValueDisplayProps) {
	const str = value || null;

	if (str === null) {
		return (
			<span className={className} aria-label="No value">
				—
			</span>
		);
	}

	const linkClassName = className === DEFAULT_CLASS ? LINK_CLASS : className;
	const normalizedType = normalizeDataType(dataType);

	switch (normalizedType) {
		case DATA_TYPES.Address:
			return <FormattedAddress value={str as string} className={linkClassName} />;
		case DATA_TYPES.Phone:
			return <FormattedPhone value={str as string} className={linkClassName} />;
		case DATA_TYPES.Url:
			return <FormattedUrl value={str as string} className={linkClassName} />;
		case DATA_TYPES.Email:
			return <FormattedEmail value={str as string} className={linkClassName} />;
		default:
			return <FormattedText value={value} className={className} />;
	}
}
