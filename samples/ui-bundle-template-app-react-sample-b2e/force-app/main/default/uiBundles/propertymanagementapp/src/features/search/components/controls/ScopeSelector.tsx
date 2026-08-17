/**
 * Dropdown that narrows the search to a single source (or "All").
 *
 * Sits next to the search bar in the default {@link Search} layout. The
 * options are derived from the configured sources: an "All" entry plus one
 * entry per source (using each source's `label`). When CMS content types have
 * been discovered at runtime, one extra entry per type is appended under its
 * CMS source — value `"<cmsKey>:<fqn>"`, label the server-provided content-type
 * label — so a user can narrow a CMS search to a single content type.
 *
 * Selecting a non-"All" scope tells {@link useSearch} to fetch and render
 * only that source. Selecting a `"<cmsKey>:<fqn>"` entry runs a CMS-only search
 * for that content type. Switching scope resets per-source pagination cursors —
 * the visible result set is changing.
 */

import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../components/ui/select";
import { ALL_SCOPE, CMS_SCOPE_SEPARATOR, type SearchConfig, type SearchScope } from "../../types";
import type { DiscoveredContentType } from "../../adapters/cms/contentTypeUtils";
import { isCmsSearchSupported } from "../../adapters/cms/api/orgApiVersionService";

interface ScopeSelectorProps {
	config: SearchConfig;
	scope: SearchScope;
	onScopeChange: (scope: SearchScope) => void;
	allLabel?: string;
	/**
	 * CMS content types discovered at runtime (from
	 * {@link SearchHandle.discoveredContentTypes}) — each with its FQN and
	 * server-provided display `label`. Appended as per-type entries under the CMS
	 * source once discovery completes; omit or pass `[]` before then. No-op when
	 * the config has no CMS source.
	 */
	discoveredContentTypes?: DiscoveredContentType[];
	className?: string;
}

export function ScopeSelector({
	config,
	scope,
	onScopeChange,
	allLabel = "All",
	discoveredContentTypes = [],
	className,
}: ScopeSelectorProps) {
	if (config.sources.length === 0) return null;
	// Discovered content types attach to the (single) CMS source. Entries are
	// injected only after discovery, so the dropdown starts with just the config
	// sources and grows once the CMS channel's types are known.
	const cmsSource = config.sources.find((s) => s.kind === "cms");
	const hasDiscoveredTypes = !!cmsSource && discoveredContentTypes.length > 0;
	const contentTypeEntries = hasDiscoveredTypes
		? discoveredContentTypes.map((ct) => ({
				value: `${cmsSource!.key}${CMS_SCOPE_SEPARATOR}${ct.fqn}`,
				label: ct.label,
			}))
		: [];
	return (
		<div className={className}>
			<Select value={scope} onValueChange={onScopeChange}>
				<SelectTrigger size="sm" className="min-w-[140px]" aria-label="Search scope">
					<SelectValue />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value={ALL_SCOPE}>{allLabel}</SelectItem>
					{config.sources.map((source) => {
						// CMS search is skipped entirely on builds below the CMS-search API
						// version (same gate `useSearch` uses to drop the CMS request), so
						// its scope entry ("Content") would only ever yield an empty result.
						// Hide it. Build-version-only — safe to evaluate during render.
						if (source.kind === "cms" && !isCmsSearchSupported()) {
							return null;
						}
						// Once the CMS channel's content types are known, the generic CMS
						// source entry (e.g. "Content") is redundant — its per-type entries
						// (appended below) cover the same source at finer granularity, so
						// drop the catch-all to avoid a duplicate-looking scope option.
						// EXCEPTION: keep it while it is the current scope. Discovery can
						// complete AFTER the user has selected the generic CMS scope; if we
						// removed the only matching item, the controlled Radix select would
						// hold a value no item represents and render blank — leaving AT
						// users unable to identify the active scope (WCAG 4.1.2).
						if (source.kind === "cms" && hasDiscoveredTypes && scope !== source.key) {
							return null;
						}
						return (
							<SelectItem key={source.key} value={source.key}>
								{source.label}
							</SelectItem>
						);
					})}
					{contentTypeEntries.map((entry) => (
						<SelectItem key={entry.value} value={entry.value}>
							{entry.label}
						</SelectItem>
					))}
				</SelectContent>
			</Select>
		</div>
	);
}
