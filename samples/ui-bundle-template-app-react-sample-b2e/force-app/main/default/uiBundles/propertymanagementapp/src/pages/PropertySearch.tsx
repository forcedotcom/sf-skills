import { UnifiedSearch } from "../components/search/UnifiedSearch";
import { SOURCE_KEYS } from "../lib/searchConfig";

export default function PropertySearch() {
	return (
		<UnifiedSearch
			title="Properties"
			subtitle="Browse and search rental properties"
			searchPlaceholder="Search by name or address..."
			restrictTo={SOURCE_KEYS.PROPERTIES}
		/>
	);
}
