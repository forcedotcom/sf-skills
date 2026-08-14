/**
 * useSearch — orchestrates configuration-driven multi-source search.
 *
 * Owns:
 *  - global `q` (one search box drives all sources)
 *  - per-source filters / sort / pagination (independent state per source)
 *  - URL sync (debounced; namespace `s.<key>.f.<field>=...`)
 *  - one batched GraphQL fetch on every state change
 *
 * Returns a per-source `controller` map plus aggregate loading/error flags.
 * Rendering and routing are the caller's responsibility.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { runSearch } from "../api/searchService";
import {
	GLOBAL_QUERY_KEY,
	readSourceParams,
	writeSourceParams,
	type ActiveFilterValue,
} from "../utils/filterUtils";
import type { SortState } from "../utils/sortUtils";
import { debounce } from "../utils/debounce";
import type {
	SourceConfig,
	SourceController,
	SourceResult,
	SearchConfig,
	SearchHandle,
	SearchScope,
	GlobalPagination,
	MergedResultItem,
} from "../types";
import { ALL_SCOPE, parseScope } from "../types";
import type { SourceRequest } from "../adapters/types";
import { MIN_QUERY_LENGTH } from "../constants";
// `getUIBundleId` supplies the search-query UIBundle id (the isolated swap
// point) and is resolved by this caller BEFORE the sync query builder runs;
// `resolveChannelId` derives the discovery channel id from a CMS result;
// `useSearchableContentTypes` is the session-cached discovery hook;
// `isValidCmsFqn` validates a selected FQN before it enters state or a query.
import { getUIBundleId, isConfiguredUIBundleId } from "../adapters/cms/searchChannel";
import { getOrgSupportsCmsSearch } from "../adapters/cms/api/orgApiVersionService";
import { resolveChannelId } from "../adapters/cms/channelResolver";
import { useSearchableContentTypes } from "../adapters/cms/hooks/useSearchableContentTypes";
import { isValidCmsFqn } from "../adapters/cms/contentTypeUtils";
import { readLastChannelId, writeLastChannelId } from "../adapters/cms/contentTypeSessionCache";

const URL_SYNC_DEBOUNCE_MS = 300;

/**
 * Returns true when `source` should participate in the current scope. Only the
 * scope's `base` (`"all"` or a source key) decides membership — a
 * `"<cmsKey>:<fqn>"` scope has `base === <cmsKey>`, so it naturally includes ONLY
 * that CMS source and drops every SObject source (CMS-only search).
 */
function isSourceInScope(scope: SearchScope, sourceKey: string): boolean {
	const { base } = parseScope(scope);
	return base === ALL_SCOPE || base === sourceKey;
}

/**
 * Validates a raw scope string against the config. Accepts `"all"`, any source
 * key, and the `"<cmsKey>:<fqn>"` form (base must be a CMS source and the FQN
 * must pass `isValidCmsFqn`). Returns a safe scope, falling back to `"all"`.
 */
function validateScope(config: SearchConfig, raw: string): SearchScope {
	if (raw === ALL_SCOPE) return ALL_SCOPE;
	const { base, cmsFqn } = parseScope(raw);
	const source = config.sources.find((s) => s.key === base);
	if (!source) return ALL_SCOPE;
	if (cmsFqn !== undefined) {
		// A content-type scope is only valid on a CMS source with a well-formed FQN.
		return source.kind === "cms" && isValidCmsFqn(cmsFqn) ? raw : ALL_SCOPE;
	}
	return raw;
}

interface SourceLocalState {
	filters: ActiveFilterValue[];
	sort: SortState | null;
	pageSize: number;
	pageIndex: number;
	afterCursor: string | undefined;
	cursorStack: string[];
}

/** Defaults applied when `config.pagination` is omitted. */
const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_PAGE_SIZE_OPTIONS = [10, 25, 50];

interface ResolvedPagination {
	mode: "per-source" | "merged";
	mergeOrder: "sequential" | "interleaved" | "proportional";
	pageSize: number;
	pageSizeOptions: number[];
}

/** Resolves the single global pagination config, filling in defaults. */
function resolvePagination(config: SearchConfig): ResolvedPagination {
	const p = config.pagination;
	const pageSizeOptions =
		p?.pageSizeOptions && p.pageSizeOptions.length > 0
			? p.pageSizeOptions
			: DEFAULT_PAGE_SIZE_OPTIONS;
	return {
		mode: p?.mode ?? "per-source",
		mergeOrder: p?.mergeOrder ?? "sequential",
		pageSize: p?.pageSize ?? pageSizeOptions[0] ?? DEFAULT_PAGE_SIZE,
		pageSizeOptions,
	};
}

/** Clamps a requested size to the configured options. */
function validatePageSize(pagination: ResolvedPagination, size: number): number {
	const valid = pagination.pageSizeOptions;
	if (valid.length === 0) return size;
	return valid.includes(size) ? size : pagination.pageSize;
}

function initSourceState(
	source: SourceConfig,
	params: URLSearchParams,
	pagination: ResolvedPagination,
): SourceLocalState {
	// `filterBy` / `defaultSort` are SObject-only — a CMS source has neither, so
	// it seeds with no filters and no default sort.
	const filterBy = source.kind === "sobject" ? (source.filterBy ?? []) : [];
	const defaultSort = source.kind === "sobject" ? (source.defaultSort ?? null) : null;
	const read = readSourceParams(params, source.key, filterBy);
	const sort = read.sort ?? defaultSort;
	const pageSize = validatePageSize(pagination, read.pageSize ?? pagination.pageSize);
	return {
		filters: read.filters,
		sort,
		pageSize,
		pageIndex: read.pageIndex,
		afterCursor: undefined,
		cursorStack: [],
	};
}

export interface UseSearchOptions {
	/**
	 * Lock the search to a single source key (or "all"). When set:
	 *   - `scope` is forced to this value and `setScope` becomes a no-op.
	 *   - The URL never writes `?scope=` (it's implicit in the page route).
	 *   - The dropdown should be hidden by the caller.
	 *
	 * Use when you embed the search inside a page that already represents
	 * the source (e.g. `/accounts/search` rendering only Accounts).
	 */
	lockedScope?: SearchScope;
}

export function useSearch(config: SearchConfig, options?: UseSearchOptions): SearchHandle {
	const [searchParams, setSearchParams] = useSearchParams();
	const lockedScope = options?.lockedScope;

	// Single global pagination config — page size, options, mode, merge order.
	// There is no per-source pagination; this applies to every scope, including
	// locked single-object pages and dropdown-narrowed scope.
	const pagination = useMemo(
		() => resolvePagination(config),
		// config is stable for the hook's lifetime.
		// eslint-disable-next-line react-hooks/exhaustive-deps
		[],
	);

	// One-time seed from URL.
	const initialSourceStates = useMemo(() => {
		const map: Record<string, SourceLocalState> = {};
		for (const source of config.sources) {
			map[source.key] = initSourceState(source, searchParams, pagination);
		}
		return map;
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);
	const initialQ = useMemo(() => searchParams.get(GLOBAL_QUERY_KEY) ?? "", []);
	const initialScope = useMemo<SearchScope>(() => {
		// When the caller locks the scope, that always wins. A locked scope is
		// always a plain source key (or "all") — never a content-type form.
		if (lockedScope !== undefined) {
			if (lockedScope === ALL_SCOPE) return ALL_SCOPE;
			return config.sources.some((s) => s.key === lockedScope) ? lockedScope : ALL_SCOPE;
		}
		// A fresh load always starts in "All" scope. We deliberately do NOT restore
		// a persisted `?scope=` — a narrowed scope (especially a CMS content-type
		// scope) depends on runtime-discovered content types that aren't known yet
		// on first paint, so restoring it would show a blank/orphaned selection.
		// Starting at "All" re-runs the full search, which re-drives discovery.
		return ALL_SCOPE;
	}, [lockedScope, config.sources]);

	const [q, setQState] = useState(initialQ);
	const [scope, setScopeState] = useState<SearchScope>(initialScope);
	const [sourceStates, setSourceStates] =
		useState<Record<string, SourceLocalState>>(initialSourceStates);

	// Merged pagination treats the cumulative result set as one fixed-size-paged
	// list (see SearchPaginationConfig). It needs a single global page index +
	// size rather than the per-source cursors above; per-source state is still
	// kept (for filters / sort) but its cursors stay at page 0.
	const mergedMode = pagination.mode === "merged";
	const mergeOrder = pagination.mergeOrder;

	const [globalPageIndex, setGlobalPageIndex] = useState(0);
	const [globalPageSize, setGlobalPageSize] = useState(pagination.pageSize);

	// Snapshot ref so debounced URL sync sees the latest state without
	// recreating callbacks on every render.
	const stateRef = useRef({ q, scope, sourceStates });
	useEffect(() => {
		stateRef.current = { q, scope, sourceStates };
	});

	// -- URL sync --------------------------------------------------------------

	const syncToUrl = useCallback(
		(nextQ: string, nextScope: SearchScope, nextStates: Record<string, SourceLocalState>) => {
			const params = new URLSearchParams();
			if (nextQ) params.set(GLOBAL_QUERY_KEY, nextQ);
			// Intentionally NOT persisting `?scope=`: a fresh load always starts in
			// "All" (see `initialScope`), so writing the scope would leave a stale
			// param the next load ignores. `nextScope` is kept in the signature for
			// call-site compatibility.
			void nextScope;
			for (const source of config.sources) {
				const state = nextStates[source.key];
				if (!state) continue;
				writeSourceParams(
					params,
					source.key,
					state.filters,
					state.sort,
					state.pageSize,
					state.pageIndex,
					// Omit sort / page size from the URL when they equal the
					// defaults, so a reset (or untouched source) leaves a clean
					// query string instead of echoing the defaults. `defaultSort` is
					// SObject-only (CMS has none).
					{
						sort: source.kind === "sobject" ? (source.defaultSort ?? null) : null,
						pageSize: pagination.pageSize,
					},
				);
			}
			setSearchParams(params, { replace: true });
		},
		[config.sources, setSearchParams, lockedScope, pagination.pageSize],
	);

	const debouncedSyncRef = useRef(debounce(syncToUrl, URL_SYNC_DEBOUNCE_MS));
	useEffect(() => {
		debouncedSyncRef.current = debounce(syncToUrl, URL_SYNC_DEBOUNCE_MS);
	}, [syncToUrl]);

	// Update one source's state and (optionally) reset its pagination.
	const updateSource = useCallback(
		(
			sourceKey: string,
			updater: (prev: SourceLocalState) => SourceLocalState,
			resetPagination: boolean,
		) => {
			// A filter / sort / page-size change reshapes the result set, so the
			// global merged page returns to the first page too.
			if (resetPagination) setGlobalPageIndex(0);
			setSourceStates((prev) => {
				const prior = prev[sourceKey];
				if (!prior) return prev;
				let next = updater(prior);
				if (resetPagination) {
					next = { ...next, pageIndex: 0, afterCursor: undefined, cursorStack: [] };
				}
				const merged = { ...prev, [sourceKey]: next };
				debouncedSyncRef.current(stateRef.current.q, stateRef.current.scope, merged);
				return merged;
			});
		},
		[],
	);

	// -- Global q --------------------------------------------------------------

	const setQ = useCallback((nextQ: string) => {
		setQState(nextQ);
		// A new term changes the whole result set — back to the first page.
		setGlobalPageIndex(0);
		// Changing the global term invalidates every cursor.
		setSourceStates((prev) => {
			const next: Record<string, SourceLocalState> = {};
			for (const [key, state] of Object.entries(prev)) {
				next[key] = { ...state, pageIndex: 0, afterCursor: undefined, cursorStack: [] };
			}
			debouncedSyncRef.current(nextQ, stateRef.current.scope, next);
			return next;
		});
	}, []);

	// -- Scope -----------------------------------------------------------------

	const setScope = useCallback(
		(nextScope: SearchScope) => {
			// Locked scope wins over user input — silently no-op.
			if (lockedScope !== undefined) return;
			// Reject unknown scope values; fall back to "all". Accepts a plain
			// source key, "all", or the CMS-only "<cmsKey>:<fqn>" form.
			const validated: SearchScope = validateScope(config, nextScope);
			setScopeState(validated);
			// The visible set changes — reset the global page too.
			setGlobalPageIndex(0);
			// Narrowing or widening invalidates every cursor — the visible result
			// set is changing.
			setSourceStates((prev) => {
				const next: Record<string, SourceLocalState> = {};
				for (const [key, state] of Object.entries(prev)) {
					next[key] = { ...state, pageIndex: 0, afterCursor: undefined, cursorStack: [] };
				}
				debouncedSyncRef.current(stateRef.current.q, validated, next);
				return next;
			});
		},
		[config, lockedScope],
	);

	// -- Reset all -------------------------------------------------------------

	const resetAll = useCallback(() => {
		setQState("");
		setGlobalPageIndex(0);
		// Preserve locked scope; otherwise widen back to "all".
		const nextScope: SearchScope = lockedScope ?? ALL_SCOPE;
		setScopeState(nextScope);
		const empty: Record<string, SourceLocalState> = {};
		for (const source of config.sources) {
			empty[source.key] = {
				filters: [],
				// `defaultSort` is SObject-only; CMS resets to no sort.
				sort: source.kind === "sobject" ? (source.defaultSort ?? null) : null,
				pageSize: pagination.pageSize,
				pageIndex: 0,
				afterCursor: undefined,
				cursorStack: [],
			};
		}
		setSourceStates(empty);
		setGlobalPageSize(pagination.pageSize);
		syncToUrl("", nextScope, empty);
	}, [config.sources, syncToUrl, lockedScope, pagination.pageSize]);

	// -- Fetch -----------------------------------------------------------------

	// -- CMS content-type discovery --------------------------------------------
	//
	// The channel id used to DISCOVER content types is derived FROM a CMS search
	// result (the permanent path — distinct from the temporary `getUIBundleId()`
	// fed INTO the query). After a CMS result arrives, the fetch effect resolves
	// it via `resolveChannelId` and stores it here; the session-cached hook then
	// fetches the searchable content types ONCE per channel. The discovered FQNs
	// (a) refine every subsequent all/cms-scope request to `contentTypes` and
	// (b) are exposed for the scope dropdown to append per-type entries.
	// Seed from the last discovered channel persisted in sessionStorage so a hard
	// reload rehydrates the content-type scope entries immediately — even when
	// the current scope is a non-CMS source (which would never re-query CMS and
	// thus never re-derive the channel id on its own). The persisted pointer is
	// keyed by UIBundle id, so this seed waits for `getUIBundleId()` (below) —
	// starting null avoids seeding a DIFFERENT bundle's channel/content types.
	const [discoveryChannelId, setDiscoveryChannelId] = useState<string | null>(null);
	// Resolve the current UIBundle id once and seed the discovery channel from
	// THIS bundle's persisted pointer. Keyed lookup prevents a second bundle
	// opened in the same session from inheriting the first bundle's channel.
	useEffect(() => {
		let cancelled = false;
		getUIBundleId()
			.then((uiBundleId) => {
				if (cancelled || !isConfiguredUIBundleId(uiBundleId)) return;
				const seeded = readLastChannelId(uiBundleId);
				if (seeded) setDiscoveryChannelId((prev) => prev ?? seeded);
			})
			.catch(() => {
				// Seeding is best-effort; a CMS result will still drive discovery.
			});
		return () => {
			cancelled = true;
		};
	}, []);
	const { contentTypes: discoveredContentTypes } = useSearchableContentTypes(discoveryChannelId);
	// The query filter and request key work in FQNs only; the `{ fqn, label }`
	// objects are threaded to the handle for the scope dropdown's display labels.
	const discoveredContentTypeFqns = useMemo(
		() => discoveredContentTypes.map((ct) => ct.fqn),
		[discoveredContentTypes],
	);

	const requestKey = useMemo(() => {
		// Stable string key that changes only when something fetch-relevant changes.
		// Sources outside the current scope are listed (with `skip: true`) so
		// the key still changes when scope toggles, but they don't contribute
		// per-source state to the diff.
		return JSON.stringify({
			q,
			// `scope` already carries the selected CMS content-type fqn (the
			// "<cmsKey>:<fqn>" form), so a content-type selection re-fires the fetch
			// with no imperative refetch.
			scope,
			// Discovered content types are part of the key so that once discovery
			// completes, the effect re-fires and every in-scope CMS request switches
			// from the bootstrap call (no `contentTypes`) to the discovered set.
			ct: discoveredContentTypeFqns,
			// Merged mode paginates globally: every in-scope source fetches the
			// same front-anchored window, so the global page/size drive the fetch
			// rather than per-source cursors.
			m: mergedMode ? { gp: globalPageIndex, gs: globalPageSize } : null,
			s: config.sources.map((source) => {
				if (!isSourceInScope(scope, source.key)) {
					return { k: source.key, skip: true };
				}
				const st = sourceStates[source.key];
				return {
					k: source.key,
					f: st?.filters,
					o: st?.sort,
					// In merged mode per-source size/cursor are overridden below.
					p: mergedMode ? undefined : st?.pageSize,
					a: mergedMode ? undefined : (st?.afterCursor ?? null),
				};
			}),
		});
	}, [
		q,
		scope,
		discoveredContentTypes,
		sourceStates,
		config.sources,
		mergedMode,
		globalPageIndex,
		globalPageSize,
	]);

	const [results, setResults] = useState<Record<string, SourceResult>>({});
	// Per-source errors, keyed by `source.key`. A source that failed while a
	// sibling succeeded surfaces its own message here without blanking others.
	const [sourceErrors, setSourceErrors] = useState<Record<string, string>>({});
	const [loading, setLoading] = useState(true);
	// Page-level error — set ONLY when EVERY in-scope source failed, or on a
	// whole-request / network failure (`runSearch` throwing).
	const [error, setError] = useState<string | null>(null);
	const fetchGenRef = useRef(0);

	useEffect(() => {
		const generation = ++fetchGenRef.current;
		setLoading(true);
		setError(null);
		setSourceErrors({});

		const activeSources = config.sources.filter((source) => isSourceInScope(scope, source.key));

		// All sources gated out — clear results and exit without firing a request.
		if (activeSources.length === 0) {
			setResults({});
			setLoading(false);
			return;
		}

		// Keyword gate: only fire a search once the user has typed at least
		// MIN_QUERY_LENGTH characters. On landing (or after clearing the box) `q`
		// is empty, so we clear results and exit WITHOUT firing a request — no
		// unfiltered "browse the first page" query, and no CMS bootstrap call
		// until there's a keyword. The minimum matters beyond UX: the SObject and
		// CMS search backends reject terms shorter than MIN_QUERY_LENGTH, which
		// otherwise surfaces as "Search failed for this source." across every
		// source. Gating here keeps the too-short case client-side.
		if (q.trim().length < MIN_QUERY_LENGTH) {
			setResults({});
			setLoading(false);
			return;
		}

		// A "<cmsKey>:<fqn>" scope narrows to one content type. Because its `base`
		// is the CMS source key, `activeSources` already excludes every SObject
		// source (CMS-only search); the fqn flows through as `contentTypes = [fqn]`.
		const { cmsFqn } = parseScope(scope);

		// Merged mode: fetch the whole front-anchored window — (page + 1) * size
		// rows — from every in-scope source, with no cursor. Concatenating these
		// and slicing [page*size, (page+1)*size) yields the exact global page,
		// because the first (page+1)*size items of the concatenation are always
		// the true merged prefix regardless of how rows interleave.
		const mergedFetchSize = (globalPageIndex + 1) * globalPageSize;

		// Resolve the async CMS preconditions ONCE, up front, then thread them into
		// each CMS request so the synchronous query builder never resolves a promise:
		//  - the UIBundle id (`getUIBundleId`), and
		//  - whether the build-time API version carries the CMS search backend
		//    (`getOrgSupportsCmsSearch`).
		let cancelled = false;
		// True once this run's request set is a DISCOVERY-driven refetch: an
		// all/cms-scope search that auto-applies the content-type FQNs discovered
		// from a prior successful CMS result (as opposed to a user-selected fqn).
		// Such a refetch only NARROWS an already-successful bootstrap, so if it
		// fails it must not destroy the good bootstrap results or raise a
		// page-level error — content-type narrowing is an enhancement, not a
		// hard requirement. Read in `.catch` below.
		let isDiscoveryRefetch = false;
		Promise.all([getUIBundleId(), getOrgSupportsCmsSearch()])
			.then(([uiBundleId, orgSupportsCmsSearch]) => {
				if (cancelled || generation !== fetchGenRef.current) return;

				const requests: SourceRequest[] = activeSources.flatMap((source) => {
					const st = sourceStates[source.key]!;
					const base: SourceRequest = {
						source,
						q,
						filters: st.filters,
						sort: st.sort,
						pageSize: mergedMode ? mergedFetchSize : st.pageSize,
						afterCursor: mergedMode ? undefined : st.afterCursor,
					};
					if (source.kind !== "cms") return [base];
					// CMS is gated on (a) a CONFIGURED (9YE-shaped) UIBundle id and
					// (b) a build-time API version with the CMS search backend (v68+,
					// core 264+). Skip silently when either is absent.
					if (!isConfiguredUIBundleId(uiBundleId) || !orgSupportsCmsSearch) {
						return [];
					}
					// CMS request: attach the resolved channel id and content types.
					//   - specific fqn selected → exactly that type.
					//   - all / cms-key scope → the discovered set if known, else
					//     omit `contentTypes` entirely (the bootstrap call).
					const contentTypes = cmsFqn
						? [cmsFqn]
						: discoveredContentTypeFqns.length > 0
							? discoveredContentTypeFqns
							: undefined;
					// A non-fqn scope that carries auto-discovered content types is a
					// discovery-driven refetch — the bootstrap CMS call already
					// succeeded (that's how the FQNs were discovered). Flag it so a
					// failure here degrades to the bootstrap results instead of
					// blanking them (see `.catch`).
					if (!cmsFqn && discoveredContentTypeFqns.length > 0) {
						isDiscoveryRefetch = true;
					}
					return [{ ...base, uiBundleId, contentTypes }];
				});

				// Every in-scope source was gated out (e.g. a CMS-only scope while CMS
				// is not yet configured): nothing to fetch. Clear results and stop,
				// mirroring the "all sources gated out" branch above.
				if (requests.length === 0) {
					setResults({});
					setLoading(false);
					return;
				}

				// The sources actually queried (CMS may have been skipped above). Used
				// for the all-failed check so a skipped/not-configured CMS source is
				// never counted as a failure.
				const requestedSources = requests.map((r) => r.source);

				return runSearch(requests).then((outcome) => {
					if (cancelled || generation !== fetchGenRef.current) return;
					const { results: nextResults, errors: nextErrors } = outcome;

					// Discovery-driven refetch that came back with a failed source:
					// the narrowing query erred, but the bootstrap results are still
					// valid and on screen. Keep them — fall back to the prior result
					// for any source this refetch failed to produce, and drop the
					// spurious error rather than blanking the grid / raising a
					// page-level error below. (Sources that DID return data still
					// update to the narrowed set.)
					if (isDiscoveryRefetch && requestedSources.some((s) => nextErrors[s.key] != null)) {
						setResults((prev) => {
							const merged = { ...prev };
							for (const source of requestedSources) {
								if (nextResults[source.key] != null) merged[source.key] = nextResults[source.key];
								// else: refetch produced nothing for this source — retain prev.
							}
							return merged;
						});
						// Discovery is already complete for this channel, so there is no
						// further channel id to resolve; just stop here without touching
						// sourceErrors / the page-level error.
						return;
					}

					setResults(nextResults);
					setSourceErrors(nextErrors);

					// Page-level error only when EVERY queried source failed; a mix of
					// success + failure surfaces per-source (below) with the grid intact.
					const allFailed =
						requestedSources.length > 0 &&
						requestedSources.every((source) => nextErrors[source.key] != null);
					if (allFailed) {
						// De-duplicate identical messages: when every source fails with the
						// same backend error (e.g. "Search isn't enabled on this channel"),
						// show it once rather than repeating it per source in the banner.
						const combined = [
							...new Set(
								requestedSources
									.map((source) => nextErrors[source.key])
									.filter((m): m is string => !!m),
							),
						].join("; ");
						setError(combined || "Unified search failed");
					}

					// Content-type discovery: once a CMS source returns data, derive the
					// discovery channel id from it and hand it to the session-cached hook.
					for (const source of requestedSources) {
						if (source.kind !== "cms") continue;
						const channelId = resolveChannelId(nextResults[source.key]);
						if (channelId) {
							setDiscoveryChannelId((prev) => (prev === channelId ? prev : channelId));
							// Persist the pointer keyed by THIS UIBundle so a reload seeds
							// only this bundle's channel — never a different bundle's.
							writeLastChannelId(uiBundleId, channelId);
							break;
						}
					}
				});
			})
			.catch((err: unknown) => {
				if (cancelled || generation !== fetchGenRef.current) return;
				console.error(err);
				// A discovery-driven refetch (content-type narrowing over an
				// already-successful bootstrap) that fails must NOT surface as a
				// page-level error or blank the good bootstrap results — the user
				// still has valid, un-narrowed results on screen. Degrade silently
				// and keep them; `finally` resets loading below.
				if (isDiscoveryRefetch) return;
				// A whole-request / network failure (or a failure to resolve the
				// channel id) is page-level, preserving the original behaviour.
				setError(err instanceof Error ? err.message : "Unified search failed");
				// Clear stale rows so a prior page's results don't linger under the
				// error banner (the per-source layout would otherwise keep rendering
				// them). `finally` resets loading below.
				setResults({});
				setSourceErrors({});
			})
			.finally(() => {
				if (cancelled || generation !== fetchGenRef.current) return;
				setLoading(false);
			});

		return () => {
			cancelled = true;
		};
		// requestKey is the dependency-of-record; sourceStates and q are
		// captured via the ref-like closure above each render.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [requestKey]);

	// -- Per-source controllers ------------------------------------------------

	const controllers = useMemo(() => {
		const out: Record<string, SourceController> = {};
		for (const source of config.sources) {
			const state = sourceStates[source.key];
			const result = results[source.key] ?? null;

			const setFilter = (field: string, value: ActiveFilterValue | undefined) => {
				updateSource(
					source.key,
					(prev) => {
						const filtered = prev.filters.filter((f) => f.field !== field);
						if (value) filtered.push(value);
						return { ...prev, filters: filtered };
					},
					true,
				);
			};
			const removeFilter = (field: string) => {
				updateSource(
					source.key,
					(prev) => ({
						...prev,
						filters: prev.filters.filter((f) => f.field !== field),
					}),
					true,
				);
			};
			const setSort = (sort: SortState | null) => {
				updateSource(source.key, (prev) => ({ ...prev, sort }), true);
			};
			const setPageSize = (size: number) => {
				updateSource(
					source.key,
					(prev) => ({ ...prev, pageSize: validatePageSize(pagination, size) }),
					true,
				);
			};
			const goToNextPage = () => {
				const cursor = result?.pageInfo?.endCursor;
				if (!cursor) return;
				updateSource(
					source.key,
					(prev) => ({
						...prev,
						cursorStack: [...prev.cursorStack, cursor],
						afterCursor: cursor,
						pageIndex: prev.pageIndex + 1,
					}),
					false,
				);
			};
			const goToPreviousPage = () => {
				updateSource(
					source.key,
					(prev) => {
						if (prev.pageIndex === 0) return prev;
						const nextStack = prev.cursorStack.slice(0, -1);
						return {
							...prev,
							cursorStack: nextStack,
							afterCursor: nextStack[nextStack.length - 1],
							pageIndex: Math.max(0, prev.pageIndex - 1),
						};
					},
					false,
				);
			};

			out[source.key] = {
				config: source,
				result,
				loading,
				// Per-source error (set only when THIS source failed) — not the
				// page-level `error` (which is set only when every source failed).
				error: sourceErrors[source.key] ?? null,
				filters: {
					active: state?.filters ?? [],
					set: setFilter,
					remove: removeFilter,
				},
				sort: {
					current: state?.sort ?? null,
					set: setSort,
				},
				pagination: {
					pageSize: state?.pageSize ?? pagination.pageSize,
					pageSizeOptions: pagination.pageSizeOptions,
					pageIndex: state?.pageIndex ?? 0,
					hasNextPage: result?.pageInfo?.hasNextPage ?? false,
					hasPreviousPage: (state?.pageIndex ?? 0) > 0,
					setPageSize,
					goToNextPage,
					goToPreviousPage,
				},
			};
		}
		return out;
	}, [config.sources, sourceStates, results, loading, sourceErrors, updateSource, pagination]);

	const scopeLocked = lockedScope !== undefined;

	// -- Aggregate (cross-source) view -----------------------------------------

	const inScopeSources = useMemo(
		() =>
			config.sources
				.map((s) => controllers[s.key])
				.filter((c): c is SourceController => !!c && isSourceInScope(scope, c.config.key)),
		[config.sources, controllers, scope],
	);

	// Cumulative result count is mode-independent: sum the in-scope totals.
	const totalCount = useMemo(
		() =>
			inScopeSources.reduce(
				(sum, c) => sum + (c.result?.totalCount ?? c.result?.nodes.length ?? 0),
				0,
			),
		[inScopeSources],
	);

	// Every in-scope source's fetched nodes flattened into one list, ordered per
	// `mergeOrder`:
	//   - sequential: all of source 1, then source 2, … (config order).
	//   - interleaved: round-robin, one node per source per round — equal priority.
	//   - proportional: each item gets a key (i + 0.5) / weight (weight = source's
	//     totalCount); sorting by key spreads each source evenly across the list
	//     in proportion to its size, so larger sources appear more often.
	// All three stay exact in merged mode. Each source fetched (page + 1) * size
	// rows from its front, so the first (page + 1) * size items of this list are
	// the true cumulative prefix: the round index / sort position of any item in
	// that prefix needs at most that many rows from a single source, and those
	// rows were all fetched, so per-source truncation never disturbs the slice.
	// Proportional uses the true totalCount as the weight (not the fetched
	// length), keeping each item's key — and thus the order — stable across pages.
	const concatenatedNodes = useMemo<MergedResultItem[]>(() => {
		const lists = inScopeSources.map((c) => ({
			key: c.config.key,
			nodes: c.result?.nodes ?? [],
			// Proportional weight: the source's true total, falling back to how many
			// we actually have when totalCount is absent.
			weight: c.result?.totalCount ?? c.result?.nodes.length ?? 0,
		}));
		const out: MergedResultItem[] = [];

		if (mergeOrder === "interleaved") {
			const maxLen = lists.reduce((m, l) => Math.max(m, l.nodes.length), 0);
			for (let round = 0; round < maxLen; round++) {
				for (const l of lists) {
					if (round < l.nodes.length) out.push({ sourceKey: l.key, node: l.nodes[round] });
				}
			}
		} else if (mergeOrder === "proportional") {
			// Tag each node with its spread key + source index, then stable-sort.
			const tagged = lists.flatMap((l, sIdx) =>
				l.nodes.map((node, i) => ({
					sourceKey: l.key,
					node,
					sIdx,
					i,
					sortKey: (i + 0.5) / (l.weight > 0 ? l.weight : 1),
				})),
			);
			tagged.sort((a, b) => a.sortKey - b.sortKey || a.sIdx - b.sIdx || a.i - b.i);
			for (const t of tagged) out.push({ sourceKey: t.sourceKey, node: t.node });
		} else {
			for (const l of lists) {
				for (const node of l.nodes) out.push({ sourceKey: l.key, node });
			}
		}
		return out;
	}, [inScopeSources, mergeOrder]);

	// -- Merged mode: one fixed-size-paged list over the cumulative results -----

	const mergedGlobalPagination = useMemo<GlobalPagination>(() => {
		// Options come from the global pagination config, NOT the in-scope source —
		// so narrowing the dropdown to one object keeps the global page sizes.
		const pageSizeOptions = pagination.pageSizeOptions;
		const pageCount = totalCount === 0 ? 0 : Math.ceil(totalCount / globalPageSize);
		// Clamp in case totalCount shrank (e.g. a filter) below the current page.
		const pageIndex = pageCount === 0 ? 0 : Math.min(globalPageIndex, pageCount - 1);
		return {
			pageIndex,
			pageCount,
			pageSize: globalPageSize,
			pageSizeOptions,
			hasNextPage: pageIndex + 1 < pageCount,
			hasPreviousPage: pageIndex > 0,
			totalCount,
			goToNextPage: () => setGlobalPageIndex((p) => p + 1),
			goToPreviousPage: () => setGlobalPageIndex((p) => Math.max(0, p - 1)),
			goToPage: (next: number) => setGlobalPageIndex(Math.max(0, Math.floor(next))),
			// Validate the requested size against the configured options before it
			// becomes `$cmsLimit` / `first`, matching the per-source setter.
			setPageSize: (size: number) => {
				setGlobalPageSize(validatePageSize(pagination, size));
				setGlobalPageIndex(0);
			},
		};
	}, [pagination, totalCount, globalPageSize, globalPageIndex]);

	const mergedModeResults = useMemo<MergedResultItem[]>(() => {
		const start = mergedGlobalPagination.pageIndex * globalPageSize;
		return concatenatedNodes.slice(start, start + globalPageSize);
	}, [concatenatedNodes, mergedGlobalPagination.pageIndex, globalPageSize]);

	// -- Per-source mode: independent cursors, "global page" = furthest source --
	//
	// Sources paginate with independent cursors (there is no global offset), so a
	// "global page" is the furthest-advanced in-scope source's page. A source
	// that runs out of pages is left behind at a lower pageIndex and stops
	// contributing nodes — its last page was already shown on an earlier global
	// page, so re-emitting it would duplicate rows in the merged list.

	const perSourceGlobalPagination = useMemo<GlobalPagination>(() => {
		const lead = inScopeSources[0];
		const pageSize = lead?.pagination.pageSize ?? pagination.pageSize;
		const pageSizeOptions = pagination.pageSizeOptions;

		const pageIndex = inScopeSources.reduce((max, c) => Math.max(max, c.pagination.pageIndex), 0);

		// Pages a source spans: prefer totalCount; otherwise a lower bound from its
		// own position (current page, plus one more if it reports a next page).
		const pageCount = inScopeSources.reduce((max, c) => {
			const tc = c.result?.totalCount;
			const span =
				tc != null && pageSize > 0
					? Math.max(1, Math.ceil(tc / pageSize))
					: c.pagination.pageIndex + (c.pagination.hasNextPage ? 2 : 1);
			return Math.max(max, span);
		}, 0);

		const hasNextPage = inScopeSources.some((c) => c.pagination.hasNextPage);
		const hasPreviousPage = pageIndex > 0;

		const goToNextPage = () =>
			inScopeSources.forEach((c) => {
				if (c.pagination.hasNextPage) c.pagination.goToNextPage();
			});
		const goToPreviousPage = () =>
			inScopeSources.forEach((c) => {
				if (c.pagination.pageIndex === pageIndex) c.pagination.goToPreviousPage();
			});

		return {
			pageIndex,
			pageCount: totalCount === 0 ? 0 : pageCount,
			pageSize,
			pageSizeOptions,
			hasNextPage,
			hasPreviousPage,
			totalCount,
			goToNextPage,
			goToPreviousPage,
			// Cursors can't seek to an arbitrary offset — honour adjacent pages only.
			goToPage: (next: number) => {
				if (next === pageIndex + 1 && hasNextPage) goToNextPage();
				else if (next === pageIndex - 1 && hasPreviousPage) goToPreviousPage();
			},
			setPageSize: (size: number) => inScopeSources.forEach((c) => c.pagination.setPageSize(size)),
		};
	}, [inScopeSources, totalCount, pagination]);

	const perSourceResults = useMemo<MergedResultItem[]>(() => {
		const globalPageIndex = perSourceGlobalPagination.pageIndex;
		return concatenatedNodes.filter((item) => {
			const c = controllers[item.sourceKey];
			// Only sources caught up to the current global page contribute; a
			// left-behind source already showed its final page earlier.
			return c?.pagination.pageIndex === globalPageIndex;
		});
	}, [concatenatedNodes, controllers, perSourceGlobalPagination.pageIndex]);

	const globalPagination = mergedMode ? mergedGlobalPagination : perSourceGlobalPagination;
	const mergedResults = mergedMode ? mergedModeResults : perSourceResults;

	return useMemo(
		() => ({
			q,
			setQ,
			scope,
			setScope,
			scopeLocked,
			sources: controllers,
			inScopeSources,
			mergedResults,
			globalPagination,
			loading,
			error,
			discoveredContentTypes,
			resetAll,
		}),
		[
			q,
			setQ,
			scope,
			setScope,
			scopeLocked,
			controllers,
			inScopeSources,
			mergedResults,
			globalPagination,
			loading,
			error,
			discoveredContentTypes,
			resetAll,
		],
	);
}
