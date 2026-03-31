import { cn } from "../../lib/utils";

interface FilterRowProps extends React.ComponentProps<"div"> {
	ariaLabel?: string;
}

export function FilterRow({
	className,
	ariaLabel = "Filters",
	children,
	...props
}: FilterRowProps) {
	return (
		<div
			className={cn("bg-white rounded-lg shadow-sm border border-gray-200 p-4 pb-2", className)}
			role="region"
			aria-label={ariaLabel}
			{...props}
		>
			<div className="flex flex-wrap items-center gap-x-8 gap-y-4">{children}</div>
		</div>
	);
}
