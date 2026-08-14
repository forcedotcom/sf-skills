/**
 * Renders one SourceSection per configured source, in declaration order.
 *
 * Customization is optional — sensible defaults kick in for any source you
 * don't override:
 *   - `renderResult[sourceKey]` — per-node renderer. Default: title from
 *     `displayFields[0]`, subtitle from the rest, optional `<Link>` driven
 *     by `routePattern`.
 *   - `renderFilters[sourceKey]` — sidebar filter UI. Default: one input per
 *     `filterBy` entry, with picklist options resolved from inline
 *     config or auto-fetched from the GraphQL aggregate API.
 *
 * Pass `false` for either entry to suppress the default for that source.
 *
 * Filter chrome (sidebar + active-filter chips + sort dropdown) is
 * automatically hidden when `handle.scope === "all"` — per-source controls
 * would be unreachable with every source on screen, and dangling chips
 * would be confusing. Pre-existing filter / sort selections stay in state,
 * so narrowing the scope brings them back unchanged.
 */

import type { ReactNode } from "react";
import { SourceSection } from "./SourceSection";
import { DefaultFilterPanel } from "./filters/DefaultFilterPanel";
import { resolveResultRenderer, type ResultRenderer } from "./results/resolveResultRenderer";
import { ALL_SCOPE, parseScope, type SearchHandle } from "../types";
import { isCmsSearchSupported } from "../adapters/cms/api/orgApiVersionService";

type FilterRenderer = (() => ReactNode) | false;

interface SearchResultsProps {
	handle: SearchHandle;
	renderResult?: Record<string, ResultRenderer>;
	renderFilters?: Record<string, FilterRenderer>;
	emptyMessages?: Record<string, string>;
}

export function SearchResults({
	handle,
	renderResult,
	renderFilters,
	emptyMessages,
}: SearchResultsProps) {
	const filtersHidden = handle.scope === ALL_SCOPE;
	// Match sections against the base scope so a "<cmsKey>:<fqn>" scope still
	// renders the CMS source's section (the fqn only narrows the query).
	const { base: scopeBase } = parseScope(handle.scope);
	return (
		<div className="space-y-10">
			{Object.entries(handle.sources).map(([key, controller]) => {
				if (scopeBase !== ALL_SCOPE && scopeBase !== key) return null;
				// CMS search is skipped on builds below the CMS-search API version, so a
				// CMS source never returns rows — rendering its section would only show
				// an empty "Content" heading. Hide it (same gate as the CMS fetch skip).
				if (controller.config.kind === "cms" && !isCmsSearchSupported()) return null;
				// Resolve the renderer through the shared helper so a CMS source
				// renders via CmsResultRow (never DefaultResultRow) in this mode; a
				// `renderResult[key]` override — including `false` (hide) — still wins.
				const resolvedRenderResult = resolveResultRenderer(controller.config, renderResult);
				if (resolvedRenderResult === false) return null;

				// CMS sources have no `filterBy`; the guard below keeps their chrome off.
				const overrideFilters = renderFilters?.[key];
				const sourceConfig = controller.config;
				const hasFilterFields =
					sourceConfig.kind === "sobject" && (sourceConfig.filterBy?.length ?? 0) > 0;
				const resolvedRenderFilters: (() => ReactNode) | undefined =
					overrideFilters === false
						? undefined
						: (overrideFilters ??
							(hasFilterFields && sourceConfig.kind === "sobject"
								? () => <DefaultFilterPanel source={sourceConfig} />
								: undefined));

				return (
					<SourceSection
						key={key}
						controller={controller}
						renderResult={resolvedRenderResult}
						renderFilters={resolvedRenderFilters}
						hideFilterChrome={filtersHidden}
						emptyMessage={emptyMessages?.[key]}
					/>
				);
			})}
		</div>
	);
}
