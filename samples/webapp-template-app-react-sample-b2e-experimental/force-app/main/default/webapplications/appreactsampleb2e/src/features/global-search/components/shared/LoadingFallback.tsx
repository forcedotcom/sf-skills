/**
 * LoadingFallback Component
 *
 * Loading fallback component for Suspense boundaries.
 * Displays a centered spinner while lazy-loaded components are being fetched.
 *
 * @remarks
 * - Used with React Suspense for code splitting
 * - Simple centered spinner design
 * - Responsive and accessible
 *
 * @example
 * ```tsx
 * <Suspense fallback={<LoadingFallback />}>
 *   <LazyComponent />
 * </Suspense>
 * ```
 */
import { cva, type VariantProps } from "class-variance-authority";
import { Spinner } from "../../../../components/ui/spinner";

/**
 * Spinner size variants based on content width.
 */
const spinnerVariants = cva("", {
	variants: {
		contentMaxWidth: {
			sm: "size-6",
			md: "size-8",
			lg: "size-10",
		},
	},
	defaultVariants: {
		contentMaxWidth: "sm",
	},
});

interface LoadingFallbackProps extends VariantProps<typeof spinnerVariants> {
	/**
	 * Maximum width of the content container. Also scales the spinner size.
	 * @default "sm"
	 */
	contentMaxWidth?: "sm" | "md" | "lg";
	/**
	 * Accessible label for screen readers.
	 * @default "Loading…"
	 */
	loadingText?: string;
}

export default function LoadingFallback({
	contentMaxWidth = "sm",
	loadingText = "Loading…",
}: LoadingFallbackProps) {
	return (
		<div className="flex justify-center" role="status" aria-live="polite">
			<Spinner className={spinnerVariants({ contentMaxWidth })} aria-hidden="true" />
			<span className="sr-only">{loadingText}</span>
		</div>
	);
}
