/** Address as link to Google Maps search. External link: target _blank, rel noopener noreferrer. */

const GOOGLE_MAPS_SEARCH_BASE = "https://www.google.com/maps/search/?api=1&query=";

export interface FormattedAddressProps {
	/** Full address string (e.g. "10 Main Rd.\nNew York, NY 31349\nUSA"). */
	value: string;
	className?: string;
}

export function FormattedAddress({ value, className }: FormattedAddressProps) {
	if (!value || !value.trim()) return null;
	const url = GOOGLE_MAPS_SEARCH_BASE + encodeURIComponent(value.trim());
	return (
		<a
			href={url}
			target="_blank"
			rel="noopener noreferrer"
			className={className}
			aria-label="Open address in Google Maps"
		>
			{value.split("\n").map((line, i) => (
				<span key={i} className="block">
					{line}
				</span>
			))}
		</a>
	);
}
