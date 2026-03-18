interface FilterErrorAlertProps {
	message: string;
}

/** Inline alert for filter validation errors (e.g. range min > max). Announced to screen readers. */
export function FilterErrorAlert({ message }: FilterErrorAlertProps) {
	return (
		<div
			role="alert"
			className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-4 py-2"
		>
			{message}
		</div>
	);
}
