/**
 * Copyright (c) 2026, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import AgentforceConversationClient from "../components/AgentforceConversationClient";

export default function TestAccPage() {
	return (
		<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
			<div className="text-center">
				<h1 className="text-4xl font-bold text-gray-900 mb-4">ACC</h1>
				<p className="text-lg text-gray-600 mb-8">Welcome to your ACC application.</p>
			</div>
			<AgentforceConversationClient agentId="0Xx000000000000AAA" />
		</div>
	);
}
