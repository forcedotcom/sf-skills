/**
 * Session-cache hook for a CMS channel's searchable content types.
 *
 * A module-level `Map` cache + a `Map` of in-flight promises, keyed by
 * `channelId`, so the Connect endpoint is hit once per channel per session and
 * concurrent callers share one request. A `null` channelId short-circuits (no
 * fetch) — discovery only runs after a CMS result yields a channel id.
 */

import { useState, useEffect, useRef } from "react";
import { fetchSearchableContentTypes } from "../api/searchableContentTypesService";
import type { DiscoveredContentType } from "../contentTypeUtils";
import { readCachedContentTypes, writeCachedContentTypes } from "../contentTypeSessionCache";

/** Session cache: channelId → discovered content types. Populated once, reused after. */
const cache = new Map<string, DiscoveredContentType[]>();
/** In-flight dedupe: channelId → the pending fetch promise. */
const inflight = new Map<string, Promise<DiscoveredContentType[]>>();

/**
 * Returns any already-known content types for `channelId` WITHOUT fetching:
 * the in-memory module cache first, then the `sessionStorage` cache (which
 * survives a hard reload). The `sessionStorage` hit is promoted into the module
 * cache so subsequent lookups stay in memory. Returns `null` when neither holds
 * the channel, so callers know a network fetch is still required.
 */
function peekCachedContentTypes(channelId: string): DiscoveredContentType[] | null {
	const inMemory = cache.get(channelId);
	if (inMemory) return inMemory;
	const persisted = readCachedContentTypes(channelId);
	if (persisted) {
		cache.set(channelId, persisted);
		return persisted;
	}
	return null;
}

/**
 * Fetches (once per session) and caches the searchable content types for a
 * channel. Concurrent callers for the same channel share one request. Results
 * are cached in memory AND persisted to `sessionStorage` so a hard reload can
 * rehydrate them without a re-fetch.
 */
export function getSearchableContentTypes(channelId: string): Promise<DiscoveredContentType[]> {
	const cached = peekCachedContentTypes(channelId);
	if (cached) return Promise.resolve(cached);

	const pending = inflight.get(channelId);
	if (pending) return pending;

	const promise = (async () => {
		try {
			const result = await fetchSearchableContentTypes(channelId);
			cache.set(channelId, result);
			// Persist so the scope dropdown keeps the types across hard reloads.
			writeCachedContentTypes(channelId, result);
			return result;
		} finally {
			inflight.delete(channelId);
		}
	})();
	inflight.set(channelId, promise);
	return promise;
}

export interface UseSearchableContentTypesResult {
	/** Discovered, validated content types (FQN + label; empty until resolved). */
	contentTypes: DiscoveredContentType[];
	loading: boolean;
	error: string | null;
}

/**
 * React hook wrapping {@link getSearchableContentTypes}. Re-runs only when the
 * `channelId` string changes; a `null` id yields an empty, non-loading state.
 */
export function useSearchableContentTypes(
	channelId: string | null,
): UseSearchableContentTypesResult {
	// Seed synchronously from the in-memory OR sessionStorage cache so a hard
	// reload shows the persisted content types on the first render (before any
	// CMS search result comes back), with no fetch and no loading flash.
	const [state, setState] = useState<UseSearchableContentTypesResult>(() => {
		const seeded = channelId ? peekCachedContentTypes(channelId) : null;
		return {
			contentTypes: seeded ?? [],
			loading: channelId != null && seeded == null,
			error: null,
		};
	});
	const isCancelled = useRef(false);

	useEffect(() => {
		isCancelled.current = false;

		if (channelId == null) {
			setState({ contentTypes: [], loading: false, error: null });
			return;
		}

		const cached = peekCachedContentTypes(channelId);
		if (cached) {
			setState({ contentTypes: cached, loading: false, error: null });
			return;
		}

		setState((s) => ({ ...s, loading: true, error: null }));
		getSearchableContentTypes(channelId)
			.then((contentTypes) => {
				if (isCancelled.current) return;
				setState({ contentTypes, loading: false, error: null });
			})
			.catch((err) => {
				if (isCancelled.current) return;
				setState({
					contentTypes: [],
					loading: false,
					error: err instanceof Error ? err.message : String(err),
				});
			});

		return () => {
			isCancelled.current = true;
		};
	}, [channelId]);

	return state;
}
