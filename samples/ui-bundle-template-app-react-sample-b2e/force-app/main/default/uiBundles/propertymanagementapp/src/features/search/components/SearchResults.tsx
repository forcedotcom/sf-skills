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
import { DefaultResultRow } from "./results/DefaultResultRow";
import { DefaultFilterPanel } from "./filters/DefaultFilterPanel";
import { ALL_SCOPE, type SearchHandle } from "../types";

type ResultRenderer = ((node: unknown) => ReactNode) | false;
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
	return (
		<div className="space-y-10">
			{Object.entries(handle.sources).map(([key, controller]) => {
				if (handle.scope !== ALL_SCOPE && handle.scope !== key) return null;
				const overrideResult = renderResult?.[key];
				if (overrideResult === false) return null;
				const resolvedRenderResult: (node: unknown) => ReactNode =
					overrideResult ?? ((node) => <DefaultResultRow node={node} source={controller.config} />);

				const overrideFilters = renderFilters?.[key];
				const hasFilterFields = (controller.config.filterBy?.length ?? 0) > 0;
				const resolvedRenderFilters: (() => ReactNode) | undefined =
					overrideFilters === false
						? undefined
						: (overrideFilters ??
							(hasFilterFields
								? () => <DefaultFilterPanel source={controller.config} />
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
