/** Plain-text field value when dataType has no dedicated formatter. */

export interface FormattedTextProps {
	value: string | number | boolean | null | undefined;
	className?: string;
}

export function FormattedText({ value, className }: FormattedTextProps) {
	if (!value) return null;
	return <span className={className}>{value as string}</span>;
}
