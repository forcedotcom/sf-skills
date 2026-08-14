/**
 * Per-node row for a CMS source. Used by both the per-source section
 * (`SearchResults`) and the merged grid (`MergedSearchResults`) via the shared
 * `resolveResultRenderer` (UI-owned) whenever `source.kind === "cms"`.
 *
 * Renders a title, a published-date subtitle, an optional content-type badge,
 * and a react-router `<Link>` when a route can be built.
 *
 * Link target:
 *   - `source.routePattern` tokens: `:id` (managedContentId), `:key`
 *     (managedContentKey), `:contentType` (contentType).
 *   - falls back to `/content/:contentType/:id` when no `routePattern` is
 *     configured.
 *
 * The content-type label is rendered only when its FQN passes `isValidCmsFqn`.
 */

import type { ReactNode } from "react";
import { Link } from "react-router";
import type { CmsSourceConfig, CmsSearchItem } from "../../adapters/cms/types";
import { formatContentTypeLabel, isValidCmsFqn } from "../../adapters/cms/contentTypeUtils";

/** Formats an ISO date string for display; echoes the raw string on failure. */
function formatPublishedDate(dateStr: string): string {
	const date = new Date(dateStr);
	if (isNaN(date.getTime())) return dateStr;
	return date.toLocaleDateString(undefined, {
		year: "numeric",
		month: "short",
		day: "numeric",
	});
}

/**
 * Substitutes `:id` / `:key` / `:contentType` tokens in a route pattern with
 * the item's values (URL-encoded). Returns `null` if a required token has no
 * value.
 */
function resolveRoute(pattern: string, item: CmsSearchItem): string | null {
	const tokens: Record<string, string | undefined> = {
		id: item.managedContentId,
		key: item.managedContentKey,
		contentType: item.contentType,
	};
	let failed = false;
	const out = pattern.replace(/:([A-Za-z_][A-Za-z0-9_]*)/g, (_match, token: string) => {
		const value = tokens[token];
		if (value == null || value === "") {
			failed = true;
			return "";
		}
		return encodeURIComponent(value);
	});
	return failed ? null : out;
}

interface CmsResultRowProps {
	node: unknown;
	source: CmsSourceConfig;
}

export function CmsResultRow({ node, source }: CmsResultRowProps) {
	const item = node as CmsSearchItem;

	const publishedDate = item.managedContentChannelDeliveryDetails?.[0]?.publishedDate;
	const showType = typeof item.contentType === "string" && isValidCmsFqn(item.contentType);

	const subtitleParts: string[] = [];
	if (showType) subtitleParts.push(formatContentTypeLabel(item.contentType));
	if (publishedDate) subtitleParts.push(`Published: ${formatPublishedDate(publishedDate)}`);

	const content: ReactNode = (
		<>
			<span className="font-medium">{item.title ?? "—"}</span>
			{item.highlightedSnippet && (
				<p className="text-sm text-muted-foreground">{item.highlightedSnippet}</p>
			)}
			{subtitleParts.length > 0 && (
				<p className="text-sm text-muted-foreground">{subtitleParts.join(" · ")}</p>
			)}
		</>
	);

	// Only render a drill-down link when the source explicitly configures a
	// routePattern. Without one, content rows render as plain (non-linked) rows
	// so they never navigate to an unbuilt detail route.
	const href = source.routePattern ? resolveRoute(source.routePattern, item) : null;
	if (href) {
		return (
			<Link
				to={href}
				className="block hover:bg-accent rounded-md px-3 -mx-3 py-1 transition-colors"
				aria-label={`View content: ${item.title}`}
			>
				{content}
			</Link>
		);
	}

	return <div className="px-3 -mx-3 py-1">{content}</div>;
}
