/**
 * Copyright (c) 2026, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { embedAgentforceClient } from "@salesforce/agentforce-conversation-client";
import type { AgentforceClientConfig } from "@salesforce/agentforce-conversation-client";
import { useEffect, useMemo, useRef } from "react";
import type {
	ResolvedEmbedOptions,
	AgentforceConversationClientProps,
} from "../types/conversation";

const GLOBAL_HOST_ID = "agentforce-conversation-client-global-host";

const DEFAULT_STYLE_TOKENS: NonNullable<AgentforceClientConfig["styleTokens"]> = {
	containerBackground: "#fafafa",

	headerBlockBackground: "#372949",
	headerBlockTextColor: "#ffffff",
	headerBlockIconColor: "#ffffff",
	headerBlockBorderBottomColor: "#3b0764",
	headerBlockFocusBorder: "#c4b5fd",

	messageBlockInboundBackgroundColor: "#ffffff",
	messageBlockInboundTextColor: "#1f2937",
	messageBlockInboundBorder: "1px solid #e5e7eb",

	messageBlockOutboundBackgroundColor: "#ede9fe",
	messageBlockOutboundTextColor: "#1f2937",
	messageBlockOutboundBorder: "1px solid #d8b4fe",

	messageInputTextColor: "#1f2937",
	messageInputTextBackgroundColor: "#ffffff",
	messageInputFooterBorderColor: "#d1d5db",
	messageInputFooterBorderFocusColor: "#9ca3af",
	messageInputFocusShadow: "0 0 0 3px rgba(156, 163, 175, 0.25)",
	messageInputFooterPlaceholderText: "#6b7280",

	messageInputFooterSendButton: "#7e22ce",
	messageInputFooterSendButtonHoverColor: "#6b21a8",
	messageInputSendButtonIconColor: "#ffffff",
	messageInputSendButtonDisabledColor: "#e5e7eb",
	messageInputActionButtonFocusBorder: "#a855f7",
};
const SINGLETON_KEY = "__agentforceConversationClientSingleton";

interface AgentforceConversationClientSingleton {
	initPromise?: Promise<void>;
	initialized: boolean;
}

interface WindowWithAgentforceSingleton extends Window {
	[SINGLETON_KEY]?: AgentforceConversationClientSingleton;
}

function getSingleton(): AgentforceConversationClientSingleton {
	const win = window as WindowWithAgentforceSingleton;
	if (!win[SINGLETON_KEY]) {
		win[SINGLETON_KEY] = {
			initialized: false,
		};
	}
	return win[SINGLETON_KEY]!;
}

function getOrCreateGlobalHost(): HTMLDivElement {
	let host = document.getElementById(GLOBAL_HOST_ID) as HTMLDivElement | null;
	if (!host) {
		host = document.createElement("div");
		host.id = GLOBAL_HOST_ID;
		document.body.appendChild(host);
	}
	return host;
}

function getDefaultEmbedOptions(): ResolvedEmbedOptions {
	return { salesforceOrigin: window.location.origin };
}

/**
 * React wrapper that embeds the Agentforce Conversation Client (copilot/agent UI)
 * using Lightning Out. Requires a valid Salesforce session for the given org.
 * Config is passed through from the consumer to the embed client as-is.
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
	salesforceOrigin,
	frontdoorUrl,
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
			agentLabel: agentLabel ?? "Chat with us",
			styleTokens: { ...DEFAULT_STYLE_TOKENS, ...styleTokens },
			renderingConfig,
		};
	}, [agentId, agentLabel, inlineProp, headerEnabled, showHeaderIcon, width, height, styleTokens]);

	const inline = normalizedAgentforceClientConfig?.renderingConfig?.mode === "inline";

	useEffect(() => {
		if (!normalizedAgentforceClientConfig?.agentId) {
			throw new Error(
				"AgentforceConversationClient requires agentId. " +
					"Pass flat props only (agentId, agentLabel, inline, headerEnabled, showHeaderIcon, width, height, styleTokens).",
			);
		}

		const singleton = getSingleton();
		if (singleton.initialized || singleton.initPromise) {
			return;
		}

		if (inline && !containerRef.current) {
			return;
		}

		const initialize = (options: ResolvedEmbedOptions) => {
			if (singleton.initialized) {
				return;
			}
			const existingEmbed = document.querySelector('lightning-out-application[data-lo="acc"]');
			if (existingEmbed) {
				singleton.initialized = true;
				return;
			}
			const host = inline ? containerRef.current! : getOrCreateGlobalHost();

			embedAgentforceClient({
				container: host,
				salesforceOrigin: salesforceOrigin ?? options.salesforceOrigin,
				frontdoorUrl: frontdoorUrl ?? options.frontdoorUrl,
				agentforceClientConfig: normalizedAgentforceClientConfig,
			});
			singleton.initialized = true;
		};

		const shouldFetchFrontdoor = window.location.hostname === "localhost";

		if (shouldFetchFrontdoor) {
			singleton.initPromise = fetch("/__lo/frontdoor")
				.then(async (res) => {
					if (!res.ok) {
						console.error("frontdoor fetch failed");
						return;
					}
					const { frontdoorUrl: resolvedFrontdoorUrl } = await res.json();
					initialize({ frontdoorUrl: resolvedFrontdoorUrl });
				})
				.catch((err) => {
					console.error("AgentforceConversationClient: failed to fetch frontdoor URL", err);
				})
				.finally(() => {
					singleton.initPromise = undefined;
				});
		} else {
			singleton.initPromise = Promise.resolve()
				.then(() => {
					initialize(getDefaultEmbedOptions());
				})
				.catch((err) => {
					console.error("AgentforceConversationClient: failed to embed Agentforce client", err);
				})
				.finally(() => {
					singleton.initPromise = undefined;
				});
		}

		return () => {
			// Intentionally no cleanup:
			// This component guarantees a single LO initialization per window.
		};
	}, [salesforceOrigin, frontdoorUrl, normalizedAgentforceClientConfig, inline]);

	if (!inline) {
		return null;
	}

	return <div ref={containerRef} />;
}

export default AgentforceConversationClient;
