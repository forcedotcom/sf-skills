import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";

interface FilterFieldWrapperProps extends React.ComponentProps<"div"> {
	label: string;
	htmlFor?: string;
	helpText?: string;
	error?: string;
}

export function FilterFieldWrapper({
	label,
	htmlFor,
	helpText,
	error,
	className,
	children,
	...props
}: FilterFieldWrapperProps) {
	return (
		<div className={cn("space-y-1", className)} {...props}>
			<Label htmlFor={htmlFor}>{label}</Label>
			{children}
			<div className="min-h-4">
				{error ? (
					<p className="text-xs text-destructive">{error}</p>
				) : (
					helpText && <p className="text-xs text-muted-foreground">{helpText}</p>
				)}
			</div>
		</div>
	);
}
