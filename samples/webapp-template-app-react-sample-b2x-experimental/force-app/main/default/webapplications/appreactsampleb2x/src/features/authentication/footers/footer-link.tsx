import { Link } from "react-router";
import { cn } from "../../../lib/utils";

interface FooterLinkProps extends Omit<React.ComponentProps<typeof Link>, "children"> {
	/** Link text prefix (e.g., "Don't have an account?") */
	text?: string;
	/** Link label (e.g., "Sign up") */
	linkText: string;
}

/**
 * Footer link component.
 */
export function FooterLink({ text, to, linkText, className, ...props }: FooterLinkProps) {
	return (
		<p className={cn("w-full text-center text-sm text-muted-foreground", className)}>
			{text && (
				<>
					{text}
					{/* Robustness: Explicit space ensures formatting tools don't strip it */}
					{"\u00A0"}
				</>
			)}
			<Link
				to={to}
				className={cn(
					"font-medium underline hover:text-primary transition-colors",
					"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
				)}
				{...props}
			>
				{linkText}
			</Link>
		</p>
	);
}
