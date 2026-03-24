import { PageHeader } from "../../../components/layout/PageHeader";
import { PageContainer } from "../../../components/layout/PageContainer";

export interface ObjectSearchErrorStateProps {
	/** Page title (e.g. "Applications") */
	title: string;
	/** Page description for the header */
	description: string;
	/** Filter row to show above the error (e.g. ObjectSearchFilterRow) so layout stays consistent */
	filterRow: React.ReactNode;
	/** User-friendly error message. Default: "There was an error loading the data. Please try again." */
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
	title,
	description,
	filterRow,
	message = "There was an error loading the data. Please try again.",
	onGoHome,
	onRetry,
}: ObjectSearchErrorStateProps) {
	return (
		<>
			<PageHeader title={title} description={description} />
			<PageContainer>
				<div className="max-w-7xl mx-auto space-y-6">
					{filterRow}
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
				</div>
			</PageContainer>
		</>
	);
}
