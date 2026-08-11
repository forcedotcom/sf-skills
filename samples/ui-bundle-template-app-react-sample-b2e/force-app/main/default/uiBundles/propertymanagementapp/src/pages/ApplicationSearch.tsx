import { UnifiedSearch } from "../components/search/UnifiedSearch";
import { SOURCE_KEYS } from "../lib/searchConfig";

export default function ApplicationSearch() {
	return (
		<UnifiedSearch
			title="Applications"
			subtitle="Manage and review rental applications"
			searchPlaceholder="Search by application #, applicant, or address..."
			restrictTo={SOURCE_KEYS.APPLICATIONS}
		/>
	);
}
