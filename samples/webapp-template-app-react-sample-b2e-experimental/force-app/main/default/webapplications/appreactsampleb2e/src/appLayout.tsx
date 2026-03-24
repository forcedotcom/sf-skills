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
			{/* Top Bar */}
			<TopBar onMenuClick={() => setIsNavOpen(true)} />

			{/* Main Content Area with Sidebar */}
			<div className="flex flex-1 overflow-hidden">
				{/* Vertical Navigation */}
				<VerticalNav isOpen={isNavOpen} onClose={() => setIsNavOpen(false)} />

				{/* Page Content */}
				<main className="flex-1 overflow-auto">
					<Outlet />
				</main>
			</div>

			{/* Agentforce Conversation Client */}
			<AgentforceConversationClient agentId="<USER_AGENT_ID_18_CHAR_0Xx...>" />
		</div>
	);
}
