import type { ReactNode } from "react";

export interface SectionRowProps {
	children: ReactNode;
}

/**
 * One row of the detail form: definition list (dl) with two-column grid. Each child
 * is a layout item (field cell or placeholder) from the layout API row.
 */
export function SectionRow({ children }: SectionRowProps) {
	return (
		<dl
			className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 sm:gap-y-2"
			aria-label="Row of fields"
		>
			{children}
		</dl>
	);
}
