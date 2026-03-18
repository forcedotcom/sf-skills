interface PageErrorStateProps {
	message: string;
}

/**
 * Full-page error state when list or metadata fails to load.
 * Uses role="alert" so screen readers announce the error.
 */
export function PageErrorState({ message }: PageErrorStateProps) {
	return (
		<div
			className="flex justify-center items-center min-h-[200px] bg-gray-50"
			role="alert"
			aria-live="assertive"
		>
			<p className="text-red-600">{message}</p>
		</div>
	);
}
