import type { ReactNode } from "react";
import { Label } from "../../../../../components/ui/label";

interface FilterFieldWrapperProps {
	label: string;
	htmlFor?: string;
	errorId?: string;
	helpText?: string;
	error?: string;
	className?: string;
	children: ReactNode;
}

export function FilterFieldWrapper({
	label,
	htmlFor,
	errorId,
	helpText,
	error,
	className,
	children,
}: FilterFieldWrapperProps) {
	return (
		<div className={`space-y-1 ${className ?? ""}`}>
			<Label htmlFor={htmlFor}>{label}</Label>
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
