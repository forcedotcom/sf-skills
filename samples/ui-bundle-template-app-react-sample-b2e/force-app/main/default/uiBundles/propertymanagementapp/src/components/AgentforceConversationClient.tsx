/**
 * Copyright (c) 2026, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { embedAgentforceClient } from "@salesforce/agentforce-conversation-client";
import type { AgentforceClientConfig } from "@salesforce/agentforce-conversation-client";
import { createAccEmbedder } from "@salesforce/agentforce-conversation-client/ui-bundle";
import { useEffect, useMemo, useRef } from "react";
import type { AgentforceConversationClientProps } from "../types/conversation";

// The embed orchestration (window singleton, global host, dev frontdoor fetch,
// SFDC_ENV default, partial-embed cleanup) lives in the shared, framework-agnostic
// @salesforce/agentforce-conversation-client/ui-bundle glue. We hand it the
// low-level embed function via dependency injection.
const embedder = createAccEmbedder<AgentforceClientConfig>(embedAgentforceClient);

/**
 * React wrapper that embeds the Agentforce Conversation Client (copilot/agent UI)
 * using Lightning Out. Requires a valid Salesforce session for the given org.
 * Flat props are normalized into an `AgentforceClientConfig` and passed through
 * to the shared embedder as-is.
 */
export function AgentforceConversationClient({
	agentId,
	agentLabel,
	inline: inlineProp,
	headerEnabled,
	showHeaderIcon,
	width,
	height,
	styleTokens,
	isFileBased,
	salesforceOrigin,
	frontdoorUrl,
	onReady,
	onError,
}: AgentforceConversationClientProps) {
	const containerRef = useRef<HTMLDivElement>(null);
	const normalizedAgentforceClientConfig = useMemo<AgentforceClientConfig>(() => {
		const renderingConfig: NonNullable<AgentforceClientConfig["renderingConfig"]> = {
			mode: inlineProp ? "inline" : "floating",
			...(headerEnabled !== undefined && { headerEnabled }),
			...(showHeaderIcon !== undefined && { showHeaderIcon }),
			...{ showAvatar: false },
			...(width !== undefined && { width }),
			...(height !== undefined && { height }),
		};

		return {
			...(agentId !== undefined && { agentId }),
			...(agentLabel !== undefined && { agentLabel }),
			...(styleTokens !== undefined && { styleTokens }),
			...(isFileBased !== undefined && { isFileBased }),
			renderingConfig,
			channel: "Vibes",
		};
	}, [
		agentId,
		agentLabel,
		inlineProp,
		headerEnabled,
		showHeaderIcon,
		width,
		height,
		styleTokens,
		isFileBased,
	]);

	const inline = normalizedAgentforceClientConfig?.renderingConfig?.mode === "inline";

	useEffect(() => {
		embedder.embedAcc(
			normalizedAgentforceClientConfig,
			{ salesforceOrigin, frontdoorUrl },
			containerRef.current,
			{ onReady, onError },
		);

		return () => {
			// Intentionally no cleanup:
			// This component guarantees a single LO initialization per window.
		};
	}, [salesforceOrigin, frontdoorUrl, normalizedAgentforceClientConfig, onReady, onError]);

	if (!inline) {
		return null;
	}

	return <div ref={containerRef} />;
}

export default AgentforceConversationClient;
