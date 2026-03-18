import React from "react";
import type { Application } from "../lib/types";

interface ApplicationsTableProps {
	applications: Application[];
	onRowClick: (application: Application) => void;
}

const getStatusColor = (status: string) => {
	const statusLower = status.toLowerCase();
	if (statusLower.includes("approved")) return "bg-green-100 text-green-700";
	if (statusLower.includes("rejected")) return "bg-red-100 text-red-700";
	if (statusLower.includes("background")) return "bg-blue-100 text-blue-700";
	if (statusLower.includes("review")) return "bg-yellow-100 text-yellow-700";
	return "bg-gray-100 text-gray-700";
};

export const ApplicationsTable: React.FC<ApplicationsTableProps> = ({
	applications,
	onRowClick,
}) => {
	const formatDate = (dateString: string) => {
		if (!dateString) return "N/A";
		try {
			const date = new Date(dateString);
			return date.toLocaleDateString("en-US", {
				year: "numeric",
				month: "short",
				day: "numeric",
			});
		} catch {
			return dateString;
		}
	};

	return (
		<div className="border border-gray-200 rounded-lg shadow-sm overflow-x-auto bg-white">
			<table className="w-full">
				<thead className="bg-gray-50 border-b border-gray-200">
					<tr>
						<th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
							User
						</th>
						<th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
							Start Date
						</th>
						<th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
							Status
						</th>
					</tr>
				</thead>
				<tbody className="bg-white divide-y divide-gray-200">
					{applications.length === 0 ? (
						<tr>
							<td colSpan={3} className="px-6 py-8 text-center text-gray-500">
								No applications found
							</td>
						</tr>
					) : (
						applications.map((application) => (
							<tr
								key={application.id}
								onClick={() => onRowClick(application)}
								className="hover:bg-gray-50 cursor-pointer transition-colors"
							>
								<td className="px-6 py-4 whitespace-nowrap">
									<div className="flex items-center">
										<div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
											<span className="text-sm font-medium text-purple-700">
												{application.applicantName?.charAt(0) || "?"}
											</span>
										</div>
										<div className="ml-4">
											<div className="text-sm font-medium text-gray-900">
												{application.applicantName || "Unknown"}
											</div>
											<div className="text-sm text-gray-500">
												{application.propertyName || application.propertyAddress}
											</div>
										</div>
									</div>
								</td>
								<td className="px-6 py-4 whitespace-nowrap">
									<div className="text-sm text-gray-900">
										{formatDate(application.startDate || application.submittedDate)}
									</div>
								</td>
								<td className="px-6 py-4 whitespace-nowrap">
									<span
										className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(application.status)}`}
									>
										{application.status}
									</span>
								</td>
							</tr>
						))
					)}
				</tbody>
			</table>
		</div>
	);
};
