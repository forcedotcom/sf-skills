import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";

interface FilterFieldWrapperProps extends React.ComponentProps<"div"> {
	label: string;
	htmlFor?: string;
	/** id applied to the visible label so a non-native control can reference it via aria-labelledby */
	labelId?: string;
	/** id applied to the error message so a control can reference it via aria-describedby */
	errorId?: string;
	helpText?: string;
	error?: string;
}

export function FilterFieldWrapper({
	label,
	htmlFor,
	labelId,
	errorId,
	helpText,
	error,
	className,
	children,
	...props
}: FilterFieldWrapperProps) {
	return (
		<div className={cn("space-y-1", className)} {...props}>
			<Label id={labelId} htmlFor={htmlFor}>
				{label}
			</Label>
			{children}
			<div className="min-h-4">
				{error ? (
					<p id={errorId} role="alert" className="text-xs text-destructive">
						{error}
					</p>
				) : (
					helpText && <p className="text-xs text-muted-foreground">{helpText}</p>
				)}
			</div>
		</div>
	);
}
