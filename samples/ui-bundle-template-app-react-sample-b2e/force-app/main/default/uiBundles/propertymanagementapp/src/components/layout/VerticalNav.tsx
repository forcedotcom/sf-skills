import React from "react";
import { Link, useLocation } from "react-router";
import dashboardIcon from "../../assets/icons/dashboard.svg";
import filesIcon from "../../assets/icons/files.svg";
import propertiesIcon from "../../assets/icons/properties.svg";
import maintenanceIcon from "../../assets/icons/maintenance.svg";
import maintenanceWorkerIcon from "../../assets/icons/maintenance-worker.svg";
import { PATHS } from "../../lib/routeConfig";

interface NavItem {
	path: string;
	icon: string;
	label: string;
}

const navItems: NavItem[] = [
	{ path: PATHS.HOME, icon: dashboardIcon, label: "Dashboard" },
	{ path: PATHS.APPLICATIONS, icon: filesIcon, label: "Applications" },
	{ path: PATHS.PROPERTIES, icon: propertiesIcon, label: "Properties" },
	{ path: PATHS.MAINTENANCE_REQUESTS, icon: maintenanceIcon, label: "Maintenance Requests" },
	{ path: PATHS.MAINTENANCE_WORKERS, icon: maintenanceWorkerIcon, label: "Maintenance Workers" },
];

interface VerticalNavProps {
	isOpen?: boolean;
	onClose?: () => void;
}

export const VerticalNav: React.FC<VerticalNavProps> = ({ isOpen = false, onClose }) => {
	const location = useLocation();

	const isActive = (path: string) => {
		if (path === "/") {
			return location.pathname === "/";
		}
		return location.pathname.startsWith(path);
	};

	const navContent = (handleClick?: () => void) =>
		navItems.map((item) => (
			<Link
				key={item.path}
				to={item.path}
				onClick={handleClick}
				className={`flex flex-col items-center justify-center gap-2 py-4 px-2 transition-colors ${
					isActive(item.path)
						? "bg-purple-100 text-purple-700 border-l-4 border-purple-700"
						: "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
				}`}
				title={item.label}
			>
				<img src={item.icon} alt={item.label} className="w-6 h-6" />
				<span className="text-xs font-medium text-center">{item.label}</span>
			</Link>
		));

	return (
		<>
			{/* Desktop sidebar */}
			<div className="hidden md:flex flex-col w-24 bg-white border-r border-gray-200 py-8 space-y-4">
				{navContent()}
			</div>

			{/* Mobile overlay */}
			{isOpen && (
				<>
					<div className="fixed inset-0 z-40 bg-black/50" onClick={onClose} aria-hidden />
					<div className="fixed left-0 top-0 bottom-0 z-50 flex flex-col w-24 bg-white border-r border-gray-200 py-8 space-y-4">
						{navContent(onClose)}
					</div>
				</>
			)}
		</>
	);
};
