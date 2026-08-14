import React from "react";
import { HardHat, Phone, MapPin, Star, DollarSign } from "lucide-react";
import type { MaintenanceWorkerSearchNode } from "../../api/maintenanceWorkers/maintenanceWorkerSearchService";

interface WorkerCardProps {
	worker: MaintenanceWorkerSearchNode;
	onClick?: (worker: MaintenanceWorkerSearchNode) => void;
}

export const WorkerCard: React.FC<WorkerCardProps> = ({ worker, onClick }) => {
	const name = worker.Name?.value || "Worker";
	const employmentType = worker.Employment_Type__c?.value || worker.Type__c?.value;
	const phone = worker.Phone__c?.value;
	const location = worker.Location__c?.value;
	const rating = worker.Rating__c?.value;
	const hourlyRate = worker.Hourly_Rate__c?.value;
	const isActive = worker.IsActive__c?.value;
	const active = typeof isActive === "boolean" ? isActive : undefined;

	const handleClick = () => onClick?.(worker);

	return (
		<div
			role="button"
			tabIndex={0}
			aria-label={name}
			className="h-full bg-white rounded-lg shadow-md p-5 hover:shadow-lg transition-shadow cursor-pointer flex flex-col gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-purple focus-visible:ring-offset-2"
			onClick={handleClick}
			onKeyDown={(e) => {
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault();
					handleClick();
				}
			}}
		>
			<div className="flex items-start justify-between gap-2">
				<div className="flex items-center gap-3 min-w-0">
					<div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
						<HardHat className="w-5 h-5 text-purple-700" />
					</div>
					<div className="min-w-0">
						<h2 className="text-base font-semibold text-gray-900 truncate">{name}</h2>
						{employmentType && <p className="text-sm text-gray-500 truncate">{employmentType}</p>}
					</div>
				</div>
				{active !== undefined && (
					<span
						className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium ${
							active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
						}`}
					>
						{active ? "Active" : "Inactive"}
					</span>
				)}
			</div>

			<div className="mt-auto space-y-1 text-sm text-gray-600">
				{phone && (
					<div className="flex items-center gap-2">
						<Phone className="w-4 h-4 text-gray-400 shrink-0" />
						<span className="truncate">{phone}</span>
					</div>
				)}
				{location && (
					<div className="flex items-center gap-2">
						<MapPin className="w-4 h-4 text-gray-400 shrink-0" />
						<span className="truncate">{location}</span>
					</div>
				)}
				<div className="flex items-center gap-4">
					{rating != null && (
						<div className="flex items-center gap-1">
							<Star className="w-4 h-4 text-yellow-500 shrink-0" />
							<span>{rating}</span>
						</div>
					)}
					{hourlyRate != null && (
						<div className="flex items-center gap-1">
							<DollarSign className="w-4 h-4 text-gray-400 shrink-0" />
							<span>{hourlyRate}/hr</span>
						</div>
					)}
				</div>
			</div>
		</div>
	);
};
