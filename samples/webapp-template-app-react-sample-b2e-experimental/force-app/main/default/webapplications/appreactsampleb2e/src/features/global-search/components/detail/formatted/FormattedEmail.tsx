/** Email as mailto: link. */

export interface FormattedEmailProps {
	value: string;
	className?: string;
}

export function FormattedEmail({ value, className }: FormattedEmailProps) {
	const str = (value || "").trim();
	if (!str) return null;
	const href = `mailto:${encodeURIComponent(str)}`;
	return (
		<a href={href} className={className} aria-label={`Email ${str}`}>
			{str}
		</a>
	);
}
