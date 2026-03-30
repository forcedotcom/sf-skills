/**
 * Copyright (c) 2026, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

export interface ResolvedEmbedOptions {
	salesforceOrigin?: string;
	frontdoorUrl?: string;
}

export type StyleTokens = Record<string, string>;

export interface AgentforceConversationClientProps {
	/** Required in practice: id of the agent to load. */
	agentId: string;
	/** If true, renders inline. If omitted/false, renders floating. */
	inline?: boolean;
	/** Show/hide chat header. Defaults to true for floating; can only be set for inline mode. */
	headerEnabled?: boolean;
	/** Show/hide agent icon in the header. */
	showHeaderIcon?: boolean;
	/** Inline width. */
	width?: string | number;
	/** Inline height. */
	height?: string | number;
	/** Theme overrides for the chat UI. */
	styleTokens?: StyleTokens;
	/** Optional. If not provided, resolved internally (e.g. from /__lo/frontdoor in dev, window.location.origin in prod). */
	salesforceOrigin?: string;
	/** Optional. If not provided, resolved internally in dev via /__lo/frontdoor. */
	frontdoorUrl?: string;
}
