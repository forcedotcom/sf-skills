import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../../lib/utils";

/**
 * Variant styles for the content container's maximum width.
 * Controls the maximum width of the inner content area within the page layout.
 */
const contentContainerVariants = cva("w-full", {
	variants: {
		contentMaxWidth: {
			sm: "max-w-sm",
			md: "max-w-md",
			lg: "max-w-lg",
		},
	},
	defaultVariants: {
		contentMaxWidth: "sm",
	},
});

/**
 * Props for the CenteredPageLayout component.
 */
interface CenteredPageLayoutProps
	extends React.ComponentProps<"div">, VariantProps<typeof contentContainerVariants> {
	/** The content to be displayed within the page layout */
	children: React.ReactNode;
	/**
	 * Maximum width of the content container.
	 * @default "sm"
	 */
	contentMaxWidth?: "sm" | "md" | "lg";
	/**
	 * Optional page title. If provided, will render a <title> component that React will place in the document head.
	 */
	title?: string;
	/**
	 * When true, content is aligned to the top instead of being vertically centered.
	 * @default true
	 */
	topAligned?: boolean;
}

/**
 * CenteredPageLayout component that provides consistent page structure and spacing.
 *
 * This component creates a full-viewport-height container that centers its content
 * horizontally. By default, content is top-aligned; set `topAligned={false}` to
 * vertically center instead. The inner content area has a configurable maximum width
 * to prevent content from becoming too wide on large screens.
 *
 * @example
 * ```tsx
 * <CenteredPageLayout contentMaxWidth="md">
 *   <YourPageContent />
 * </CenteredPageLayout>
 *
 * <CenteredPageLayout contentMaxWidth="md" topAligned={false}>
 *   <VerticallyCenteredContent />
 * </CenteredPageLayout>
 * ```
 */
export function CenteredPageLayout({
	contentMaxWidth,
	className,
	children,
	title,
	topAligned = true,
	...props
}: CenteredPageLayoutProps) {
	return (
		<>
			{title && <title>{title}</title>}
			<main
				className={cn(
					"flex min-h-svh w-full justify-center p-6 md:p-10",
					topAligned ? "items-start" : "items-center",
					className,
				)}
				data-slot="page-layout"
				{...props}
			>
				<div className={contentContainerVariants({ contentMaxWidth })}>{children}</div>
			</main>
		</>
	);
}
