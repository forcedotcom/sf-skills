import type { SearchableObjectConfig } from "../../lib/constants";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { Search } from "lucide-react";

type SearchableObjectApiName = SearchableObjectConfig["objectApiName"];

export interface GlobalSearchBarProps {
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
 * Home page search: object dropdown + search input. Uses fallback labels from config.
 */
export function GlobalSearchBar({
	searchableObjects,
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
		<div className="flex flex-wrap gap-2 items-center mb-4">
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
						{searchableObjects.map((obj) => (
							<SelectItem key={obj.objectApiName} value={obj.objectApiName}>
								{obj.fallbackLabelPlural ?? "Records"}
							</SelectItem>
						))}
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
					<Search className="w-5 h-5 text-gray-500" aria-hidden="true" />
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
