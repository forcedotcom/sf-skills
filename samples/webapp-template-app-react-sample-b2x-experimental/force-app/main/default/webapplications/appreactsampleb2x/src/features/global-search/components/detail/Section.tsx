import { useState, useCallback, useEffect, useRef } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

export interface SectionProps {
	sectionId: string;
	titleLabel: string;
	showHeader: boolean;
	collapsible: boolean;
	/** When provided, section is controlled (parent owns state). When undefined, section is uncontrolled (internal state). */
	collapsed?: boolean;
	onToggle?: (sectionId: string, collapsed: boolean) => void;
	children: ReactNode;
}

/**
 * Section block with optional heading and collapsible content. Controlled when
 * `collapsed` is passed; uncontrolled otherwise. Accessible: aria-expanded, aria-controls, keyboard (Enter/Space).
 */
export function Section({
	sectionId,
	titleLabel,
	showHeader,
	collapsible,
	collapsed: controlledCollapsed,
	onToggle,
	children,
}: SectionProps) {
	const [internalCollapsed, setInternalCollapsed] = useState(false);
	const isControlled = controlledCollapsed !== undefined;
	const collapsed = isControlled ? controlledCollapsed : internalCollapsed;

	const warnedUncontrolledRef = useRef(false);
	useEffect(() => {
		if (
			process.env.NODE_ENV === "development" &&
			onToggle != null &&
			!isControlled &&
			!warnedUncontrolledRef.current
		) {
			warnedUncontrolledRef.current = true;
			console.warn(
				"[Section] onToggle is passed but collapsed is undefined; section is uncontrolled. Pass collapsed to control from parent.",
			);
		}
	}, [onToggle, isControlled]);

	const contentId = `section-content-${sectionId}`;
	const headerId = `section-header-${sectionId}`;

	const handleToggle = useCallback(() => {
		const next = !collapsed;
		if (!isControlled) setInternalCollapsed(next);
		onToggle?.(sectionId, next);
	}, [collapsed, isControlled, onToggle, sectionId]);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (!collapsible) return;
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				handleToggle();
			}
		},
		[collapsible, handleToggle],
	);

	return (
		<section
			className="border-b border-border last:border-b-0 pb-6 last:pb-0"
			aria-labelledby={showHeader ? headerId : undefined}
		>
			{showHeader && titleLabel && (
				<h3 id={headerId} className="text-base font-semibold text-foreground mb-4">
					{collapsible ? (
						<button
							type="button"
							className="flex items-center gap-2 w-full text-left hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded"
							onClick={handleToggle}
							onKeyDown={handleKeyDown}
							aria-expanded={!collapsed}
							aria-controls={contentId}
							aria-label={`${titleLabel}, ${collapsed ? "expand" : "collapse"} section`}
							aria-roledescription="Section toggle"
						>
							{collapsed ? (
								<ChevronRight className="h-4 w-4 shrink-0" aria-hidden />
							) : (
								<ChevronDown className="h-4 w-4 shrink-0" aria-hidden />
							)}
							<span>{titleLabel}</span>
						</button>
					) : (
						<span className="block">{titleLabel}</span>
					)}
				</h3>
			)}
			<div
				id={contentId}
				className={showHeader && collapsible ? "mt-2" : ""}
				aria-hidden={collapsible ? collapsed : undefined}
				hidden={collapsible && collapsed}
			>
				{children}
			</div>
		</section>
	);
}
