/**
 * SearchHeader Component
 *
 * Displays the header for search results or browse-all (same UI).
 * labelPlural comes from object metadata (e.g. useObjectInfoBatch) so it is not hard-coded.
 */
interface SearchHeaderProps {
	query?: string;
	isBrowseAll?: boolean;
	/** Plural label for the primary object (e.g. "Accounts"). From object metadata. */
	labelPlural?: string;
}

export default function SearchHeader({
	query,
	isBrowseAll,
	labelPlural = "records",
}: SearchHeaderProps) {
	return (
		<header className="mb-6" aria-label="Search results header">
			<h1 className="text-3xl font-bold mb-2">
				{isBrowseAll ? `Browse All ${labelPlural}` : "Search Results"}
			</h1>
			{!isBrowseAll && query && (
				<p className="text-lg" aria-live="polite">
					Results for: <span className="font-semibold">"{query}"</span>
				</p>
			)}
		</header>
	);
}
