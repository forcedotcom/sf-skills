/**
 * Back button and title for the record detail page.
 *
 * @param title - Record title (e.g. record name) shown next to the back control.
 * @param onBack - Called when the user activates the back control.
 */
import { Button } from "../../../../components/ui/button";
import { ArrowLeft } from "lucide-react";

interface DetailHeaderProps {
	title: string;
	onBack: () => void;
}

export default function DetailHeader({ title, onBack }: DetailHeaderProps) {
	return (
		<div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
			<Button
				variant="ghost"
				onClick={onBack}
				className="w-fit"
				aria-label="Go back to search results"
			>
				<ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
				Back
			</Button>
			{title ? (
				<h1 className="text-xl font-semibold text-foreground truncate" id="detail-page-title">
					{title}
				</h1>
			) : null}
		</div>
	);
}
