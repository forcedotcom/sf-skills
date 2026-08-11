/**
 * Default per-node row used when no `renderResult` is supplied for a source.
 *
 * Layout:
 *   - Title: first entry in `displayFields` (preferring displayValue).
 *   - Subtitle: remaining display fields joined with " · ".
 *   - When `routePattern` is configured on the source, the row is wrapped in
 *     a react-router `<Link>` whose `to` is built by substituting `:fieldName`
 *     tokens with the corresponding field values (special token `:id`
 *     resolves to the configured `idField`, default "Id").
 *
 * Applications can still pass `renderResult[sourceKey]` to override.
 */

import type { ReactNode } from "react";
import { Link } from "react-router";
import { fieldValue } from "../../utils/fieldUtils";
import type { DisplayField, SObjectSourceConfig } from "../../types";

const ROUTE_TOKEN = /:([A-Za-z_][A-Za-z0-9_]*)/g;

function fieldName(f: DisplayField): string {
	return typeof f === "string" ? f : f.name;
}

/** Resolves a single dot-path against a node, returning a string or null. */
function readPath(node: unknown, path: string): string | null {
	if (!node || typeof node !== "object") return null;
	const parts = path.split(".");
	let cursor: unknown = node;
	for (let i = 0; i < parts.length - 1; i++) {
		if (!cursor || typeof cursor !== "object") return null;
		cursor = (cursor as Record<string, unknown>)[parts[i]];
	}
	const leaf = (cursor as Record<string, unknown> | null)?.[parts[parts.length - 1]];
	if (leaf == null) return null;
	if (typeof leaf === "object") {
		return fieldValue(leaf as { value?: unknown; displayValue?: string | null });
	}
	return String(leaf);
}

/** Reads the user-facing string for a top-level display field. */
function readDisplayField(node: unknown, field: DisplayField): string | null {
	if (typeof field === "string") return readPath(node, field);
	if ("raw" in field) return readPath(node, field.name);
	// Relationship: prefer the first scalar subfield's display value.
	const sub = field.subfields[0];
	if (!sub) return null;
	const subName = fieldName(sub);
	return readPath(node, `${field.name}.${subName}`);
}

/** Substitutes `:fieldName` tokens in routePattern with node values. */
function resolveRoute(pattern: string, node: unknown, idField: string): string | null {
	let failed = false;
	const out = pattern.replace(ROUTE_TOKEN, (_, token) => {
		const path = token === "id" ? idField : token;
		const value = readPath(node, path);
		if (value == null) {
			failed = true;
			return "";
		}
		return encodeURIComponent(value);
	});
	return failed ? null : out;
}

interface DefaultResultRowProps {
	node: unknown;
	source: SObjectSourceConfig;
}

export function DefaultResultRow({ node, source }: DefaultResultRowProps) {
	const idField = source.idField ?? "Id";
	const fields = source.displayFields;
	const titleField = fields[0];
	const title = titleField ? readDisplayField(node, titleField) : null;

	const subtitleParts = fields
		.slice(1)
		.map((f) => readDisplayField(node, f))
		.filter((s): s is string => s != null && s !== "");

	const content: ReactNode = (
		<>
			<span className="font-medium">{title ?? "—"}</span>
			{subtitleParts.length > 0 && (
				<p className="text-sm text-muted-foreground">{subtitleParts.join(" · ")}</p>
			)}
		</>
	);

	if (source.routePattern) {
		const href = resolveRoute(source.routePattern, node, idField);
		if (href) {
			return (
				<Link
					to={href}
					className="block hover:bg-accent rounded-md px-3 -mx-3 py-1 transition-colors"
				>
					{content}
				</Link>
			);
		}
	}

	return <div className="px-3 -mx-3 py-1">{content}</div>;
}
