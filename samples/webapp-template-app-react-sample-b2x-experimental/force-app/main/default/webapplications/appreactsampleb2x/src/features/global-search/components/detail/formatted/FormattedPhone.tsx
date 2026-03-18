/** Phone value as tel: link for dialer/VoIP. */

export interface FormattedPhoneProps {
	value: string;
	className?: string;
}

/** Normalizes value for tel: (digits and + only). */
function telHref(value: string): string {
	const cleaned = value.replace(/[^\d+]/g, "");
	return cleaned ? `tel:${cleaned}` : "#";
}

export function FormattedPhone({ value, className }: FormattedPhoneProps) {
	if (!value) return null;
	const trimmed = (value || "").trim();
	const href = telHref(trimmed);
	if (href === "#") return <span className={className}>{trimmed}</span>;
	return (
		<a href={href} className={className} aria-label={`Call ${trimmed}`}>
			{trimmed}
		</a>
	);
}
