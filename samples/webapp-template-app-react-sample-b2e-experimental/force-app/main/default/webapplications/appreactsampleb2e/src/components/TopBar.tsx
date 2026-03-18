import React, { useEffect, useState } from "react";
import { Search, Bell, ChevronDown, Menu } from "lucide-react";
import zenLogo from "../assets/icons/zen-logo.svg";
import { getUserInfo } from "../api/dashboard";

interface TopBarProps {
	onMenuClick?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onMenuClick }) => {
	const [userName, setUserName] = useState<string>("User");
	const [showNotifications, setShowNotifications] = useState(false);

	useEffect(() => {
		const loadUserInfo = async () => {
			const userInfo = await getUserInfo();
			if (userInfo) {
				setUserName(userInfo.name);
			}
		};
		loadUserInfo();
	}, []);

	const handleNotificationClick = () => {
		setShowNotifications(!showNotifications);
	};

	const handleCloseNotifications = () => {
		setShowNotifications(false);
	};
	return (
		<div className="bg-[#372949] text-white h-16 flex items-center justify-between px-6">
			{/* Left section - Logo and Menu */}
			<div className="flex items-center gap-4">
				<button
					onClick={onMenuClick}
					className="p-2 hover:bg-purple-700 rounded-md transition-colors md:hidden"
					aria-label="Toggle menu"
				>
					<Menu className="w-6 h-6" />
				</button>
				<div className="flex items-center gap-2">
					<img src={zenLogo} alt="Zenlease Logo" className="w-8 h-8" />
					<span className="text-xl tracking-wide">
						<span className="font-light">ZEN</span>
						<span className="font-semibold">LEASE</span>
					</span>
				</div>
			</div>

			{/* Right section - Search, Notifications, Profile */}
			<div className="flex items-center gap-4">
				{/* Search Icon (Mobile) */}
				<button
					className="p-2 hover:bg-purple-700 rounded-md transition-colors md:hidden"
					aria-label="Search"
				>
					<Search className="w-5 h-5" />
				</button>

				{/* Notifications */}
				<div className="relative">
					<button
						onClick={handleNotificationClick}
						className="p-2 hover:bg-purple-700 rounded-md transition-colors relative"
						aria-label="Notifications"
					>
						<Bell className="w-5 h-5" />
					</button>

					{/* Notifications Overlay */}
					{showNotifications && (
						<>
							{/* Backdrop */}
							<div className="fixed inset-0 z-40" onClick={handleCloseNotifications} />

							{/* Notification Panel */}
							<div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-lg shadow-xl z-50 overflow-hidden">
								<div className="p-4 border-b border-gray-200">
									<h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
								</div>
								<div className="p-8 text-center">
									<Bell className="w-12 h-12 mx-auto text-gray-300 mb-3" />
									<p className="text-sm text-gray-500">No new notifications</p>
								</div>
							</div>
						</>
					)}
				</div>

				{/* User Profile */}
				<button className="flex items-center gap-2 px-3 py-2 hover:bg-purple-700 rounded-md transition-colors">
					<div className="w-8 h-8 bg-purple-300 rounded-full flex items-center justify-center text-purple-900 font-semibold">
						{userName.charAt(0).toUpperCase()}
					</div>
					<span className="hidden md:inline font-medium">{userName.toUpperCase()}</span>
					<ChevronDown className="w-4 h-4 hidden md:inline" />
				</button>
			</div>
		</div>
	);
};
