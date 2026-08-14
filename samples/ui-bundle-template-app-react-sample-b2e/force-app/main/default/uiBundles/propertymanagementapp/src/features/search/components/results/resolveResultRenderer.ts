/**
 * Single source of truth for choosing how one source's result node is rendered.
 *
 * Every result layout (`SearchResults`, `MergedSearchResults`, and any future
 * grid/list) MUST resolve its per-node renderer through this helper so the
 * kind-aware default can never be missed in one mode. The rule, in order:
 *
 *   1. A `renderResult[source.key]` config override wins in EVERY mode —
 *      including `false`, which hides the source entirely.
 *   2. Otherwise `source.kind === "cms"` → {@link CmsResultRow}.
 *   3. Otherwise (SObject) → {@link DefaultResultRow}.
 *
 * Returning the same union the callers already use (`renderer | false`) lets a
 * component early-return `null` for a hidden source without special-casing.
 */

import { createElement, type ReactNode } from "react";
import type { SourceConfig } from "../../types";
import { DefaultResultRow } from "./DefaultResultRow";
import { CmsResultRow } from "./CmsResultRow";

/** A per-node renderer, or `false` to hide the source's results. */
export type ResultRenderer = ((node: unknown) => ReactNode) | false;

/**
 * Resolves the renderer for one source. See the module doc for the precedence
 * rules. `renderResult` is the optional per-source override map from `<Search>`.
 */
export function resolveResultRenderer(
	source: SourceConfig,
	renderResult?: Record<string, ResultRenderer>,
): ResultRenderer {
	const override = renderResult?.[source.key];
	// A config override wins in every mode — including `false` (hide).
	if (override !== undefined) return override;

	// Assign a `displayName` so React DevTools shows a readable label for the
	// per-node component factory and the `react/display-name` lint rule is
	// satisfied. (This is a debug label only — it does not affect reference
	// identity; a new function is still created on each call.)
	if (source.kind === "cms") {
		const renderCmsRow = (node: unknown) => createElement(CmsResultRow, { node, source });
		renderCmsRow.displayName = "CmsResultRowRenderer";
		return renderCmsRow;
	}
	const renderDefaultRow = (node: unknown) => createElement(DefaultResultRow, { node, source });
	renderDefaultRow.displayName = "DefaultResultRowRenderer";
	return renderDefaultRow;
}
