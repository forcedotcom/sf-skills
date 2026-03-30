import { Card, CardContent } from "@/components/ui/card";
import { Link } from "react-router";
import MaintenanceRequestList from "@/components/maintenanceRequests/MaintenanceRequestList";
import { WeatherWidget } from "@/components/dashboard/WeatherWidget";
import { useMaintenanceRequests } from "@/hooks/useMaintenanceRequests";

export default function Dashboard() {
	const {
		requests: maintenanceRequests,
		loading: maintenanceLoading,
		error: maintenanceError,
	} = useMaintenanceRequests();
	const recentMaintenance = maintenanceRequests.slice(0, 5);

	return (
		<div className="mx-auto flex max-w-[1100px] flex-col gap-6 lg:flex-row">
			<div className="min-w-0 flex-1">
				<Card className="border-gray-200 p-6 shadow-sm">
					<div className="mb-6 flex items-center justify-between">
						<h2 className="text-lg font-semibold tracking-wide text-primary">
							Maintenance Requests
						</h2>
						<Link
							to="/maintenance"
							className="cursor-pointer text-primary underline-offset-4 hover:underline"
						>
							See All
						</Link>
					</div>
					<CardContent className="space-y-4 p-0">
						<MaintenanceRequestList
							requests={recentMaintenance}
							loading={maintenanceLoading}
							error={maintenanceError}
						/>
					</CardContent>
				</Card>
			</div>
			<div className="w-full shrink-0 lg:w-[320px]">
				<WeatherWidget />
			</div>
		</div>
	);
}
