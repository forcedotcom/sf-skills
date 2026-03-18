/** URL as external link (new tab, noopener noreferrer). Falls back to plain text if not http(s). */

import { isAllowedLinkUrl } from "../../../utils/linkUtils";

export interface FormattedUrlProps {
	value: string;
	className?: string;
	/** Optional display text; defaults to the URL. */
	displayText?: string;
}

export function FormattedUrl({ value, className, displayText }: FormattedUrlProps) {
	const str = (value || "").trim();
	if (!str) return null;
	const href = str.startsWith("http://") || str.startsWith("https://") ? str : `https://${str}`;
	if (!isAllowedLinkUrl(href)) return <span className={className}>{str}</span>;
	const label = displayText ?? str;
	return (
		<a
			href={href}
			target="_blank"
			rel="noopener noreferrer"
			className={className}
			aria-label={`Open link in new tab: ${label}`}
		>
			{label}
		</a>
	);
}
