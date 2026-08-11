import { UnifiedSearch } from "../components/search/UnifiedSearch";
import { SOURCE_KEYS } from "../lib/searchConfig";

export default function MaintenanceWorkerSearch() {
	return (
		<UnifiedSearch
			title="Maintenance Workers"
			subtitle="Find maintenance workers and contractors"
			searchPlaceholder="Search by name or phone..."
			restrictTo={SOURCE_KEYS.WORKERS}
		/>
	);
}
