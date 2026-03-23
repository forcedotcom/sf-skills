import React from "react";
import { useNavigate } from "react-router";
import { PATHS } from "../lib/routeConfig";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import type { MaintenanceRequest } from "../lib/types";
import PlumbingIcon from "../assets/icons/plumbing.svg";
import HVACIcon from "../assets/icons/hvac.svg";
import ElectricalIcon from "../assets/icons/electrical.svg";
import AppliancesIcon from "../assets/icons/appliances.svg";
import PestIcon from "../assets/icons/pest.svg";

interface MaintenanceTableProps {
	requests: MaintenanceRequest[];
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

export const MaintenanceTable: React.FC<MaintenanceTableProps> = ({ requests }) => {
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
				{requests.length === 0 ? (
					<div className="text-center py-8 text-gray-500">No maintenance requests</div>
				) : (
					requests.slice(0, 5).map((request) => (
						<div
							key={request.id}
							className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
						>
							{/* Mobile: stacked card layout */}
							<div className="flex items-start gap-3 md:hidden">
								<div
									className={`flex items-center justify-center w-12 h-12 ${issueIconColors[request.issueType] || "bg-purple-100"} rounded-lg flex-shrink-0`}
								>
									{issueIcons[request.issueType] ? (
										<img
											src={issueIcons[request.issueType]}
											alt={request.issueType}
											className="w-6 h-6"
										/>
									) : (
										<span className="text-2xl">🔧</span>
									)}
								</div>
								<div className="min-w-0 flex-1">
									<div className="flex items-center gap-2 mb-1 flex-wrap">
										<h3 className="font-semibold text-gray-900">{request.issueType}</h3>
										<span className="text-gray-500">|</span>
										<span className="text-sm text-gray-600 truncate">
											{request.propertyAddress.split(",")[0]}
										</span>
									</div>
									<p className="text-sm text-gray-700 truncate mb-1">
										{request.description || "No description"}
									</p>
									<div className="flex items-center gap-2">
										<div className="w-6 h-6 bg-gray-300 rounded-full flex items-center justify-center flex-shrink-0">
											<span className="text-xs font-medium text-gray-700">
												{request.tenantName?.charAt(0) || "?"}
											</span>
										</div>
										<span className="text-sm text-gray-700 font-medium truncate">
											{request.tenantName || "Unknown"}
										</span>
									</div>
								</div>
							</div>

							{/* Desktop: horizontal flex row with proportional columns */}
							<div className="hidden md:flex items-center min-w-0 overflow-hidden">
								{/* Icon */}
								<div
									className={`flex items-center justify-center w-12 h-12 ${issueIconColors[request.issueType] || "bg-purple-100"} rounded-lg flex-shrink-0`}
								>
									{issueIcons[request.issueType] ? (
										<img
											src={issueIcons[request.issueType]}
											alt={request.issueType}
											className="w-6 h-6"
										/>
									) : (
										<span className="text-2xl">🔧</span>
									)}
								</div>

								{/* Issue Type and Address */}
								<div className="ml-4 flex-[2_2_0] min-w-0 overflow-hidden">
									<div className="flex items-center gap-2 mb-1">
										<h3 className="font-semibold text-gray-900 shrink-0">{request.issueType}</h3>
										<span className="text-gray-500 shrink-0">|</span>
										<span className="text-sm text-gray-600 truncate">
											{request.propertyAddress.split(",")[0]}
										</span>
									</div>
									<p className="text-sm text-gray-500 truncate">
										Request ID: {request.id.substring(0, 8)}...
									</p>
								</div>

								{/* Issue description */}
								<div className="ml-4 flex-[3_3_0] min-w-0 overflow-hidden">
									<p className="text-sm text-gray-700 truncate">
										{request.description || "No description"}
									</p>
								</div>

								{/* Tenant */}
								<div className="ml-4 flex-[2_2_0] min-w-0 overflow-hidden flex items-center gap-2">
									<div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center flex-shrink-0">
										<span className="text-sm font-medium text-gray-700">
											{request.tenantName?.charAt(0) || "?"}
										</span>
									</div>
									<span className="text-sm text-gray-700 font-medium truncate">
										{request.tenantName || "Unknown"}
									</span>
								</div>
							</div>
						</div>
					))
				)}
			</div>
		</Card>
	);
};
