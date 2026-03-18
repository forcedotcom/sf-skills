/**
 * Placeholder content when Property List search API is unavailable.
 * Shows skeleton cards and a friendly message so the layout still feels like the search experience.
 */
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

const SKELETON_CARD_COUNT = 3;

export default function PropertySearchPlaceholder({
	message = "Search is temporarily unavailable. Please try again later.",
}: {
	message?: string;
}) {
	return (
		<div className="space-y-4" role="status" aria-live="polite">
			<Alert
				variant="default"
				className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30"
			>
				<AlertCircle className="h-4 w-4" aria-hidden="true" />
				<AlertTitle>Service temporarily unavailable</AlertTitle>
				<AlertDescription>{message}</AlertDescription>
			</Alert>
			<p className="text-sm text-muted-foreground">Showing placeholder results</p>
			<div className="space-y-4" aria-hidden="true">
				{[...Array(SKELETON_CARD_COUNT)].map((_, i) => (
					<Card key={i}>
						<CardContent className="flex gap-4 p-4">
							<Skeleton className="size-[200px] shrink-0 rounded-xl" />
							<div className="min-w-0 flex-1 space-y-3">
								<Skeleton className="h-5 w-3/4" />
								<Skeleton className="h-4 w-full" />
								<Skeleton className="h-4 w-1/2" />
								<Skeleton className="h-4 w-2/3" />
								<div className="flex gap-2 pt-2">
									<Skeleton className="h-9 w-24" />
									<Skeleton className="h-9 w-28" />
								</div>
							</div>
						</CardContent>
					</Card>
				))}
			</div>
		</div>
	);
}
