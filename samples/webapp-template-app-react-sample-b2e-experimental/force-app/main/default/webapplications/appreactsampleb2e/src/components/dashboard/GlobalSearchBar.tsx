import type { ObjectInfoResult } from "../../features/global-search/types/objectInfo/objectInfo";
import type { SearchableObjectConfig } from "../../lib/globalSearchConstants";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../components/ui/select";

type SearchableObjectApiName = SearchableObjectConfig["objectApiName"];

interface GlobalSearchBarProps {
	objectApiNames: SearchableObjectApiName[];
	objectInfos: (ObjectInfoResult | null)[];
	searchableObjects: readonly SearchableObjectConfig[];
	selectedObjectApiName: SearchableObjectApiName;
	onSelectedObjectChange: (objectApiName: SearchableObjectApiName) => void;
	searchQuery: string;
	onSearchQueryChange: (value: string) => void;
	onSearchSubmit: () => void;
	onBrowseAll: () => void;
	labelPlural: string;
}

/**
 * Home page search: object dropdown + search input in a single combined control.
 * Uses shadcn Select and object metadata for labels when available.
 */
export function GlobalSearchBar({
	searchableObjects,
	objectApiNames,
	objectInfos,
	selectedObjectApiName,
	onSelectedObjectChange,
	searchQuery,
	onSearchQueryChange,
	onSearchSubmit,
	onBrowseAll,
	labelPlural,
}: GlobalSearchBarProps) {
	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") {
			e.preventDefault();
			onSearchSubmit();
		}
	};

	return (
		<div className="flex flex-wrap justify-end gap-2 items-center mb-4">
			<div
				className="w-full max-w-xl bg-white rounded-full px-4 py-3 shadow-sm border border-gray-200 flex items-center gap-2"
				role="search"
				aria-label={`Search ${labelPlural}`}
			>
				<Select
					value={selectedObjectApiName}
					onValueChange={(v) => onSelectedObjectChange(v as SearchableObjectApiName)}
				>
					<SelectTrigger
						className="border-0 bg-transparent shadow-none focus:ring-0 focus:ring-offset-0 min-w-[120px] py-0 h-auto font-medium text-gray-700"
						aria-label="Search in"
					>
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{searchableObjects.map((obj) => {
							const idx = objectApiNames.indexOf(obj.objectApiName);
							const info = idx >= 0 ? objectInfos[idx] : null;
							const label =
								(info?.labelPlural as string | undefined) ?? obj.fallbackLabelPlural ?? "Records";
							return (
								<SelectItem key={obj.objectApiName} value={obj.objectApiName}>
									{label}
								</SelectItem>
							);
						})}
					</SelectContent>
				</Select>
				<span className="text-gray-300 shrink-0" aria-hidden="true">
					|
				</span>
				<input
					type="search"
					placeholder={`Search ${labelPlural}`}
					value={searchQuery}
					onChange={(e) => onSearchQueryChange(e.target.value)}
					onKeyDown={handleKeyDown}
					className="flex-1 outline-none text-gray-600 bg-transparent min-w-0"
					aria-label={`Search ${labelPlural}`}
				/>
				<button
					type="button"
					onClick={onSearchSubmit}
					disabled={!searchQuery.trim()}
					className="p-1 rounded-full hover:bg-gray-100 disabled:opacity-50 disabled:pointer-events-none shrink-0"
					aria-label="Submit search"
				>
					<svg
						className="w-5 h-5 text-gray-500"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						aria-hidden="true"
					>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2}
							d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
						/>
					</svg>
				</button>
			</div>
			<button
				type="button"
				onClick={onBrowseAll}
				className="px-4 py-3 text-sm font-medium text-[#372949] bg-white border border-gray-200 rounded-full shadow-sm hover:bg-gray-50 whitespace-nowrap"
				aria-label={`Browse all ${labelPlural}`}
			>
				Browse all {labelPlural}
			</button>
		</div>
	);
}
