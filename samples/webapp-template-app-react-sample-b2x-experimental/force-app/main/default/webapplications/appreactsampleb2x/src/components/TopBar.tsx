import { useState } from "react";
import { ChevronDown, Menu, UserPen, LogOut, User, Loader2 } from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "../features/authentication/context/AuthContext";
import { ROUTES } from "../features/authentication/authenticationConfig";
import zenLogo from "@/assets/icons/zen-logo.svg";

export interface TopBarProps {
	onMenuClick?: () => void;
}

export function TopBar({ onMenuClick }: TopBarProps) {
	const { user, isAuthenticated, loading } = useAuth();

	return (
		<header
			className="flex h-16 items-center justify-between bg-teal-700 px-6 text-white"
			role="banner"
		>
			<div className="flex items-center gap-4">
				<button
					type="button"
					onClick={onMenuClick}
					className="rounded-md p-2 transition-colors hover:bg-teal-600 md:hidden"
					aria-label="Toggle menu"
				>
					<Menu className="size-6" aria-hidden />
				</button>
				<Logo />
			</div>

			{loading ? (
				<Loader2 className="size-5 animate-spin" aria-label="Loading" />
			) : isAuthenticated ? (
				<AuthenticatedControls userName={user?.name ?? "User"} />
			) : (
				<LoginLink />
			)}
		</header>
	);
}

function Logo() {
	return (
		<div className="flex items-center gap-2">
			<img src={zenLogo} alt="Zenlease Logo" className="size-8" />
			<span className="text-xl tracking-wide">
				<span className="font-light">ZEN</span>
				<span className="font-semibold">LEASE</span>
			</span>
		</div>
	);
}

function LoginLink() {
	return (
		<Link
			to={ROUTES.LOGIN.PATH}
			className="flex items-center gap-2 rounded-md bg-white px-4 py-2 font-medium text-teal-700 transition-colors hover:bg-teal-50"
		>
			<User className="size-4" aria-hidden />
			Sign Up / Sign In
		</Link>
	);
}

function AuthenticatedControls({ userName }: { userName: string }) {
	return (
		<div className="flex items-center gap-4">
			<UserMenu userName={userName} />
		</div>
	);
}

function UserMenu({ userName }: { userName: string }) {
	const { logout } = useAuth();
	const [open, setOpen] = useState(false);

	return (
		<div className="relative">
			<button
				type="button"
				onClick={() => setOpen((prev) => !prev)}
				className="flex items-center gap-2 rounded-md px-3 py-2 transition-colors hover:bg-teal-600"
				aria-label="User menu"
				aria-expanded={open}
				aria-haspopup="true"
			>
				<div
					className="flex size-8 items-center justify-center rounded-full bg-teal-300 font-semibold text-teal-900"
					aria-hidden
				>
					{userName.charAt(0).toUpperCase()}
				</div>
				<span className="hidden font-medium md:inline">{userName.toUpperCase()}</span>
				<ChevronDown className="hidden size-4 md:inline" aria-hidden />
			</button>

			{open && (
				<>
					<div className="fixed inset-0 z-40" onClick={() => setOpen(false)} aria-hidden />
					<div
						className="absolute right-0 top-full z-50 mt-2 w-48 overflow-hidden rounded-lg bg-white py-1 shadow-xl"
						role="menu"
					>
						<Link
							to={ROUTES.PROFILE.PATH}
							onClick={() => setOpen(false)}
							className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 transition-colors hover:bg-gray-100"
							role="menuitem"
						>
							<UserPen className="size-4" aria-hidden />
							Edit Profile
						</Link>
						<div className="mx-3 border-t border-gray-200" />
						<button
							type="button"
							onClick={() => {
								setOpen(false);
								logout();
							}}
							className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 transition-colors hover:bg-gray-100"
							role="menuitem"
						>
							<LogOut className="size-4" aria-hidden />
							Log Out
						</button>
					</div>
				</>
			)}
		</div>
	);
}
