import { CenteredPageLayout } from "./centered-page-layout";
import { Card, CardContent, CardHeader } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";

interface CardSkeletonProps {
	/**
	 * Maximum width of the content container.
	 * @default "sm"
	 */
	contentMaxWidth?: "sm" | "md" | "lg";
	/**
	 * Accessible label for screen readers.
	 * @default "Loading…"
	 */
	loadingText?: string;
}

/**
 * Full-page loading indicator with skeleton card placeholder.
 */
export function CardSkeleton({ contentMaxWidth, loadingText = "Loading…" }: CardSkeletonProps) {
	return (
		<CenteredPageLayout contentMaxWidth={contentMaxWidth}>
			<div role="status" aria-live="polite">
				<Card className="w-full">
					<CardHeader>
						<Skeleton className="h-4 w-2/3" />
						<Skeleton className="h-4 w-1/2" />
					</CardHeader>
					<CardContent>
						<Skeleton className="aspect-video w-full" />
					</CardContent>
				</Card>
				<span className="sr-only">{loadingText}</span>
			</div>
		</CenteredPageLayout>
	);
}
