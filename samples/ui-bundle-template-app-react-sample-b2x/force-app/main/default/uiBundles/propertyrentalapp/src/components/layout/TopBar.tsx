import { ChevronDown, Menu, User } from "lucide-react";
import { Link } from "react-router";
import type { RefObject } from "react";
import { ROUTES } from "@/features/authentication/authenticationConfig";
import zenLogo from "@/assets/icons/zen-logo.svg";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { AuthMenu } from "@/features/authentication/menu/AuthMenu";

export interface TopBarProps {
	onMenuClick?: () => void;
	isNavOpen?: boolean;
	menuButtonRef?: RefObject<HTMLButtonElement | null>;
}

export function TopBar({ onMenuClick, isNavOpen, menuButtonRef }: TopBarProps) {
	return (
		<header className="flex h-16 items-center justify-between bg-teal-700 px-6 text-white">
			<div className="flex items-center gap-4">
				<Button
					ref={menuButtonRef}
					variant="ghost"
					size="icon"
					onClick={onMenuClick}
					className="text-white hover:bg-teal-600 aria-expanded:bg-teal-600 aria-expanded:text-white md:hidden"
					aria-label="Toggle menu"
					aria-expanded={isNavOpen}
					aria-controls={isNavOpen ? "mobile-nav" : undefined}
				>
					<Menu className="size-6" aria-hidden />
				</Button>
				<Logo />
			</div>

			<AuthMenu
				trigger={(user) => (
					<Button
						variant="ghost"
						className="h-10 gap-2 rounded-lg px-3 text-base text-white hover:bg-teal-800 hover:text-white"
						aria-label="User menu"
					>
						<Avatar className="size-7 bg-teal-300 text-teal-900">
							<AvatarFallback className="bg-teal-300 font-semibold text-teal-900">
								{user.name.charAt(0).toUpperCase()}
							</AvatarFallback>
						</Avatar>
						<span className="hidden font-medium md:inline">{user.name.toUpperCase()}</span>
						<ChevronDown className="hidden size-4 md:block" aria-hidden />
					</Button>
				)}
				guestContent={
					<Button
						asChild
						variant="secondary"
						size="icon"
						className="rounded-full bg-white text-teal-700 hover:bg-teal-50 md:h-9 md:w-auto md:gap-2 md:rounded-lg md:px-4"
					>
						<Link to={ROUTES.LOGIN.PATH} aria-label="Sign Up / Sign In">
							<User className="size-5 md:size-4" aria-hidden="true" />
							<span className="hidden md:inline">Sign Up / Sign In</span>
						</Link>
					</Button>
				}
			/>
		</header>
	);
}

function Logo() {
	return (
		<Link to="/" aria-label="ZENLEASE home" className="flex items-center gap-2">
			{/* Decorative: the accessible name comes from the link's aria-label. */}
			<img src={zenLogo} alt="" className="size-8" />
			<span className="text-xl tracking-wide">
				<span className="font-light">ZEN</span>
				<span className="font-semibold">LEASE</span>
			</span>
		</Link>
	);
}
