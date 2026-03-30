import React from "react";
import { useNavigate } from "react-router";
import { PATHS } from "../../lib/routeConfig";
import { Card } from "../ui/card";
import { Button } from "../ui/button";
import { Skeleton } from "../ui/skeleton";
import type { DashboardMaintenanceNode } from "../../api/dashboard/dashboard";
import PlumbingIcon from "../../assets/icons/plumbing.svg";
import HVACIcon from "../../assets/icons/hvac.svg";
import ElectricalIcon from "../../assets/icons/electrical.svg";
import AppliancesIcon from "../../assets/icons/appliances.svg";
import PestIcon from "../../assets/icons/pest.svg";

interface MaintenanceTableProps {
	requests: NonNullable<DashboardMaintenanceNode>[];
	loading?: boolean;
	onView?: (id: string) => void;
}

const issueIcons: Record<string, string> = {
	Plumbing: PlumbingIcon,
	HVAC: HVACIcon,
	Electrical: ElectricalIcon,
	Appliance: AppliancesIcon,
	Pest: PestIcon,
};

const issueIconColors: Record<string, string> = {
	Plumbing: "bg-purple-100",
	HVAC: "bg-purple-100",
	Electrical: "bg-purple-100",
	Appliance: "bg-purple-100",
	Pest: "bg-purple-100",
};

export const MaintenanceTable: React.FC<MaintenanceTableProps> = ({ requests, loading }) => {
	const navigate = useNavigate();

	const handleSeeAll = () => {
		navigate(PATHS.MAINTENANCE_REQUESTS);
	};

	return (
		<Card className="p-6 border-gray-200 shadow-sm">
			<div className="flex items-center justify-between mb-6">
				<h2 className="text-lg font-semibold text-primary-purple uppercase tracking-wide">
					Maintenance Requests
				</h2>
				<Button variant="link" onClick={handleSeeAll} className="cursor-pointer">
					See All
				</Button>
			</div>
			<div className="space-y-4">
				{loading ? (
					Array.from({ length: 5 }, (_, i) => (
						<div key={i} className="flex items-center p-4 bg-gray-50 rounded-lg">
							<Skeleton className="w-12 h-12 rounded-lg shrink-0" />
							<div className="ml-4 w-64 shrink-0 space-y-2">
								<Skeleton className="h-4 w-40" />
								<Skeleton className="h-3 w-32" />
							</div>
							<div className="ml-4 w-80 shrink-0">
								<Skeleton className="h-3 w-56" />
							</div>
							<div className="ml-4 w-48 shrink-0 flex items-center gap-2">
								<Skeleton className="w-8 h-8 rounded-full shrink-0" />
								<Skeleton className="h-4 w-24" />
							</div>
						</div>
					))
				) : requests.length === 0 ? (
					<div className="text-center py-8 text-gray-500">No maintenance requests</div>
				) : (
					requests.slice(0, 5).map((request) => {
						const issueType = request.Type__c?.value || "General";
						const propertyAddress = request.Property__r?.Address__c?.value || "Unknown Address";
						const description = request.Description__c?.value || "";
						const tenantName = request.User__r?.Name?.value || "Unknown";

						return (
							<div
								key={request.Id}
								className="flex items-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
							>
								<div
									className={`flex items-center justify-center w-12 h-12 ${issueIconColors[issueType] || "bg-purple-100"} rounded-lg flex-shrink-0`}
								>
									{issueIcons[issueType] ? (
										<img src={issueIcons[issueType]} alt={issueType} className="w-6 h-6" />
									) : (
										<span className="text-2xl">🔧</span>
									)}
								</div>

								<div className="ml-4 w-64 flex-shrink-0">
									<div className="flex items-center gap-2 mb-1">
										<h3 className="font-semibold text-gray-900">{issueType}</h3>
										<span className="text-gray-500">|</span>
										<span className="text-sm text-gray-600 truncate">
											{propertyAddress.split(",")[0]}
										</span>
									</div>
									<p className="text-sm text-gray-500">
										Request ID: {request.Id.substring(0, 8)}...
									</p>
								</div>

								<div className="ml-4 w-80 flex-shrink-0">
									<p className="text-sm text-gray-700 truncate">
										{description || "No description"}
									</p>
								</div>

								<div className="ml-4 w-48 flex-shrink-0 flex items-center gap-2">
									<div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center flex-shrink-0">
										<span className="text-sm font-medium text-gray-700">
											{tenantName.charAt(0) || "?"}
										</span>
									</div>
									<span className="text-sm text-gray-700 font-medium truncate">{tenantName}</span>
								</div>
							</div>
						);
					})
				)}
			</div>
		</Card>
	);
};
