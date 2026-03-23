import React, { useEffect, useState } from "react";
import { ChevronDown, Menu } from "lucide-react";
import zenLogo from "../assets/icons/zen-logo.svg";
import { getUserInfo } from "../api/dashboard";

interface TopBarProps {
	onMenuClick?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onMenuClick }) => {
	const [userName, setUserName] = useState<string>("User");

	useEffect(() => {
		const loadUserInfo = async () => {
			const userInfo = await getUserInfo();
			if (userInfo) {
				setUserName(userInfo.name);
			}
		};
		loadUserInfo();
	}, []);
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

			{/* Right section - Profile */}
			<div className="flex items-center gap-4">
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
