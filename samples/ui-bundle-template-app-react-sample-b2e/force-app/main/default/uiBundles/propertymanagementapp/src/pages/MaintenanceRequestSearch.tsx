import { UnifiedSearch } from "../components/search/UnifiedSearch";
import { SOURCE_KEYS } from "../lib/searchConfig";

export default function MaintenanceRequestSearch() {
	return (
		<UnifiedSearch
			title="Maintenance Requests"
			subtitle="Track and update maintenance requests"
			searchPlaceholder="Search by subject, tenant, address, or worker..."
			restrictTo={SOURCE_KEYS.MAINTENANCE}
		/>
	);
}
