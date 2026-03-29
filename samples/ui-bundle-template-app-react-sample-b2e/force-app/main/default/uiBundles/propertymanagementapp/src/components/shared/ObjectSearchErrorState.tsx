export interface ObjectSearchErrorStateProps {
	message?: string;
	/** Called when user clicks "Go to home" */
	onGoHome: () => void;
	/** Called when user clicks "Retry" */
	onRetry: () => void;
}

/**
 * Shared error state for object-search pages. Shows a friendly message with Go home and Retry actions.
 * Renders the same layout (header + filters) to avoid layout shift.
 */
export function ObjectSearchErrorState({
	message = "There was an error loading the data. Please try again.",
	onGoHome,
	onRetry,
}: ObjectSearchErrorStateProps) {
	return (
		<>
			<div
				className="flex flex-col items-center justify-center py-16 px-4 rounded-lg border border-gray-200 bg-gray-50"
				role="alert"
				aria-live="assertive"
			>
				<p className="text-gray-700 mb-6 text-center">{message}</p>
				<div className="flex gap-3">
					<button
						type="button"
						onClick={onGoHome}
						className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
					>
						Go to home
					</button>
					<button
						type="button"
						onClick={onRetry}
						className="px-4 py-2 text-sm font-medium text-white bg-purple-700 rounded-lg hover:bg-purple-800"
					>
						Retry
					</button>
				</div>
			</div>
		</>
	);
}
