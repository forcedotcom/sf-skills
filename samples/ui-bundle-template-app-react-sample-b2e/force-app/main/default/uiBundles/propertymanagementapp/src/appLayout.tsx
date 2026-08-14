import { useState } from "react";
import { Outlet } from "react-router";
import { TopBar } from "./components/layout/TopBar";
import { VerticalNav } from "./components/layout/VerticalNav";
import { AgentforceConversationClient } from "./components/AgentforceConversationClient";
import { Toaster } from "./components/ui/sonner";

export default function AppLayout() {
	const [isNavOpen, setIsNavOpen] = useState(false);

	return (
		<div className="flex flex-col">
			<Toaster />
			<a
				href="#main-content"
				className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-white focus:px-4 focus:py-2 focus:text-purple-700 focus:shadow-lg focus:outline focus:outline-2 focus:outline-purple-700"
			>
				Skip to main content
			</a>
			{/* Top Bar */}
			<TopBar onMenuClick={() => setIsNavOpen(true)} />

			{/* Main Content Area with Sidebar */}
			<div className="flex flex-1 overflow-hidden">
				{/* Vertical Navigation */}
				<VerticalNav isOpen={isNavOpen} onClose={() => setIsNavOpen(false)} />

				{/* Page Content */}
				<main id="main-content" className="flex-1 overflow-auto">
					<Outlet />
				</main>
			</div>

			{/* Agentforce Conversation Client */}
			<AgentforceConversationClient agentId="<USER_AGENT_ID_18_CHAR_0Xx...>" />
		</div>
	);
}
