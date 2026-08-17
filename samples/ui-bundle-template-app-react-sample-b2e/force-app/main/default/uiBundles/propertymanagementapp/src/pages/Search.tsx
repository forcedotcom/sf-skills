import { UnifiedSearch } from "../components/search/UnifiedSearch";

/**
 * Unified search across every searchable object (properties, maintenance
 * requests, workers, applications). A scope selector lets the user narrow to a
 * single object; one global pagination control advances every in-scope source.
 */
export default function Search() {
	return (
		<UnifiedSearch
			title="Search"
			subtitle="Search across properties, maintenance requests, workers, and applications."
			searchPlaceholder="Search everything…"
		/>
	);
}
