import { Link, useLocation } from "react-router";
import { Home, Search, BarChart3, Wrench, Phone, type LucideIcon } from "lucide-react";
import { useAuth } from "@/features/authentication/context/AuthContext";
import { useMemo } from "react";

interface NavItem {
	path: string;
	icon: LucideIcon;
	label: string;
	authRequired?: boolean;
}

const navItems: NavItem[] = [
	{ path: "/", icon: Home, label: "Home" },
	{ path: "/dashboard", icon: BarChart3, label: "Dashboard", authRequired: true },
	{ path: "/properties", icon: Search, label: "Property Search" },
	{ path: "/maintenance", icon: Wrench, label: "Maintenance Requests", authRequired: true },
	{ path: "/contact", icon: Phone, label: "Contact Us" },
];

interface NavMenuProps {
	isOpen?: boolean;
	onClose?: () => void;
}

export function NavMenu({ isOpen = false, onClose }: NavMenuProps) {
	const location = useLocation();
	const { isAuthenticated } = useAuth();

	const visibleItems = useMemo(
		() => navItems.filter((item) => !item.authRequired || isAuthenticated),
		[isAuthenticated],
	);

	const isActive = (path: string) => {
		if (path === "/") return location.pathname === "/";
		return location.pathname.startsWith(path);
	};

	const navContent = (handleClick?: () => void) =>
		visibleItems.map((item) => {
			const Icon = item.icon;
			const active = isActive(item.path);
			return (
				<Link
					key={item.path}
					to={item.path}
					onClick={handleClick}
					className={`flex flex-col items-center justify-center gap-2 px-2 py-4 transition-colors ${
						active
							? "border-l-4 border-teal-700 bg-teal-100 text-teal-700"
							: "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
					}`}
					title={item.label}
					aria-label={item.label}
				>
					<Icon className="size-6 shrink-0" aria-hidden />
					<span className="text-center text-xs font-medium leading-tight">{item.label}</span>
				</Link>
			);
		});

	return (
		<>
			{/* Desktop sidebar */}
			<nav
				className="hidden md:flex w-24 flex-col border-r border-gray-200 bg-white py-8"
				aria-label="Main navigation"
			>
				{navContent()}
			</nav>

			{/* Mobile overlay */}
			{isOpen && (
				<>
					<div className="fixed inset-0 z-40 bg-black/50" onClick={onClose} aria-hidden />
					<nav
						className="fixed left-0 top-0 bottom-0 z-50 flex w-24 flex-col border-r border-gray-200 bg-white py-8"
						aria-label="Main navigation"
					>
						{navContent(onClose)}
					</nav>
				</>
			)}
		</>
	);
}
