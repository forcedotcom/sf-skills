interface PageLoadingStateProps {
	message?: string;
}

/**
 * Full-page loading state. Uses aria-live="polite" so screen readers can announce updates.
 */
export function PageLoadingState({ message = "Loading..." }: PageLoadingStateProps) {
	return (
		<div
			className="flex justify-center items-center min-h-[200px] bg-gray-50"
			aria-live="polite"
			aria-busy="true"
		>
			<p className="text-gray-600">{message}</p>
		</div>
	);
}
