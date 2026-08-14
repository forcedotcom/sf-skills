import { useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router";
import { TopBar } from "@/components/layout/TopBar";
import { VerticalNav } from "@/components/layout/VerticalNav";
import { Toaster } from "@/components/ui/sonner";
import { TenantAccessProvider } from "@/context/TenantAccessContext";

const APP_NAME = "ZENLEASE";

const atPath = (base: string) => (p: string) => p === base || p.startsWith(`${base}/`);

const PAGE_TITLES: { match: (path: string) => boolean; title: string }[] = [
	{ match: (p) => p === "/", title: "Home" },
	{ match: atPath("/properties"), title: "Property Search" },
	{
		match: (p) => p.startsWith("/property/") || p.startsWith("/object/"),
		title: "Property Details",
	},
	{ match: atPath("/dashboard"), title: "Dashboard" },
	{ match: atPath("/maintenance"), title: "Maintenance" },
	{ match: atPath("/contact"), title: "Contact" },
	{ match: atPath("/application"), title: "Application" },
];

function pageTitleFor(pathname: string): string {
	const page = PAGE_TITLES.find((entry) => entry.match(pathname))?.title ?? "Page Not Found";
	return `${page} · ${APP_NAME}`;
}

export default function AppLayout() {
	const [isNavOpen, setIsNavOpen] = useState(false);
	const menuButtonRef = useRef<HTMLButtonElement>(null);
	const mainRef = useRef<HTMLElement>(null);
	const { pathname } = useLocation();
	const previousPathname = useRef(pathname);

	useEffect(() => {
		document.title = pageTitleFor(pathname);
		if (pathname !== previousPathname.current) {
			previousPathname.current = pathname;
			mainRef.current?.focus();
		}
	}, [pathname]);

	const closeNav = () => {
		setIsNavOpen(false);
		menuButtonRef.current?.focus();
	};

	return (
		<TenantAccessProvider>
			<div className="flex min-h-screen flex-col bg-gray-50">
				<Toaster />
				<a
					href="#main-content"
					className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:ring-2 focus:ring-white focus:ring-offset-2"
				>
					Skip to main content
				</a>
				<TopBar
					onMenuClick={() => setIsNavOpen((open) => !open)}
					isNavOpen={isNavOpen}
					menuButtonRef={menuButtonRef}
				/>

				<div className="flex flex-1 overflow-hidden">
					<VerticalNav isOpen={isNavOpen} onClose={closeNav} />

					<main
						id="main-content"
						ref={mainRef}
						tabIndex={-1}
						className="flex-1 overflow-auto bg-gray-50 p-4 outline-none md:p-8"
						role="main"
					>
						<Outlet />
					</main>
				</div>
			</div>
		</TenantAccessProvider>
	);
}
