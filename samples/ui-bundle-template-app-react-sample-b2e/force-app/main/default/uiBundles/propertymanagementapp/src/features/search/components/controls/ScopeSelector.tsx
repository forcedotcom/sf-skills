/**
 * Dropdown that narrows the search to a single source (or "All").
 *
 * Sits next to the search bar in the default {@link Search} layout. The
 * options are derived from the configured sources: an "All" entry plus one
 * entry per source (using each source's `label`).
 *
 * Selecting a non-"All" scope tells {@link useSearch} to fetch and render
 * only that source. Switching scope resets per-source pagination cursors —
 * the visible result set is changing.
 */

import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../components/ui/select";
import { ALL_SCOPE, type SearchConfig, type SearchScope } from "../../types";

interface ScopeSelectorProps {
	config: SearchConfig;
	scope: SearchScope;
	onScopeChange: (scope: SearchScope) => void;
	allLabel?: string;
	className?: string;
}

export function ScopeSelector({
	config,
	scope,
	onScopeChange,
	allLabel = "All",
	className,
}: ScopeSelectorProps) {
	if (config.sources.length === 0) return null;
	return (
		<div className={className}>
			<Select value={scope} onValueChange={onScopeChange}>
				<SelectTrigger size="sm" className="min-w-[140px]" aria-label="Search scope">
					<SelectValue />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value={ALL_SCOPE}>{allLabel}</SelectItem>
					{config.sources.map((source) => (
						<SelectItem key={source.key} value={source.key}>
							{source.label}
						</SelectItem>
					))}
				</SelectContent>
			</Select>
		</div>
	);
}
