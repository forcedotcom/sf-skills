import { Link, useLocation } from "react-router";
import { Home, Search, BarChart3, Wrench, Phone, type LucideIcon } from "lucide-react";
import { useAuth } from "@/features/authentication/context/AuthContext";
import { useTenantAccess } from "@/context/TenantAccessContext";
import { useEffect, useMemo } from "react";

interface VerticalNavItem {
	path: string;
	icon: LucideIcon;
	label: string;
	authRequired?: boolean;
}

const navItems: VerticalNavItem[] = [
	{ path: "/", icon: Home, label: "Home" },
	{ path: "/dashboard", icon: BarChart3, label: "Dashboard", authRequired: true },
	{ path: "/properties", icon: Search, label: "Property Search" },
	{ path: "/maintenance", icon: Wrench, label: "Maintenance Requests", authRequired: true },
	{ path: "/contact", icon: Phone, label: "Contact Us" },
];

interface VerticalNavProps {
	isOpen?: boolean;
	onClose?: () => void;
}

export function VerticalNav({ isOpen = false, onClose }: VerticalNavProps) {
	const location = useLocation();
	const { isAuthenticated } = useAuth();
	const { hasTenantRecord } = useTenantAccess();

	useEffect(() => {
		if (!isOpen) return;
		const onKey = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose?.();
		};
		document.addEventListener("keydown", onKey);
		return () => document.removeEventListener("keydown", onKey);
	}, [isOpen, onClose]);

	const visibleItems = useMemo(
		() =>
			navItems.filter((item) => {
				if (!item.authRequired) return true;
				if (!isAuthenticated) return false;
				if (item.path === "/dashboard" || item.path === "/maintenance") {
					return hasTenantRecord;
				}
				return true;
			}),
		[hasTenantRecord, isAuthenticated],
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
					aria-current={active ? "page" : undefined}
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
					{/*
					 * Distinct label from the desktop sidebar: both navs are in the DOM at the
					 * same time, and two navigation landmarks sharing one name is ambiguous.
					 */}
					<nav
						id="mobile-nav"
						className="fixed left-0 top-0 bottom-0 z-50 flex w-24 flex-col border-r border-gray-200 bg-white py-8"
						aria-label="Mobile navigation"
					>
						{navContent(onClose)}
					</nav>
				</>
			)}
		</>
	);
}
