import { useCallback, useEffect, useState } from "react";

interface UseAsyncDataResult<T> {
	data: T | null;
	loading: boolean;
	error: string | null;
}

interface CacheOptions {
	/** Unique cache key. Used for lookups and invalidation via `clearCacheEntry`. */
	key: string;
	/** Time-to-live in ms. Default: 30_000 (30s) */
	ttl?: number;
	/** Max entries in the cache. Default: 50. Evicts oldest entry when exceeded. */
	maxSize?: number;
}

interface CacheEntry {
	data: unknown;
	timestamp: number;
}

/**
 * Module-level cache shared across all useCachedAsyncData consumers.
 * Cleared automatically on page reload since it only lives in memory.
 * Keys are caller-provided so different hook call-sites get independent entries.
 */
const cache = new Map<string, CacheEntry>();

/**
 * Returns a cached entry if it exists and hasn't exceeded its TTL.
 * Expired entries are deleted lazily here rather than on a timer,
 * so there's no background cleanup overhead.
 */
function getValidEntry(key: string, ttl: number): CacheEntry | undefined {
	const entry = cache.get(key);
	if (!entry) return undefined;
	if (Date.now() - entry.timestamp > ttl) {
		cache.delete(key);
		return undefined;
	}
	return entry;
}

/**
 * Stores a result in the cache. If the cache is at capacity and the key
 * is new, the oldest entry (first in Map insertion order — FIFO) is evicted.
 */
function setEntry(key: string, data: unknown, maxSize: number): void {
	if (!cache.has(key) && cache.size >= maxSize) {
		const firstKey = cache.keys().next().value;
		if (firstKey !== undefined) cache.delete(firstKey);
	}
	cache.set(key, { data, timestamp: Date.now() });
}

/**
 * Removes a single cache entry by key. The key must match the
 * `options.key` passed to `useCachedAsyncData`.
 *
 * @example
 * // Hook:
 * useCachedAsyncData(() => fetchAccountDetail(id), [id], { key: `account:${id}` });
 *
 * // Invalidate after a mutation:
 * await updateAccount(id, fields);
 * clearCacheEntry(`account:${id}`);
 */
export function clearCacheEntry(key: string): void {
	cache.delete(key);
}

/**
 * Removes all cache entries. Useful for global invalidation scenarios
 * like user logout or after a bulk operation.
 *
 * @example
 * async function handleLogout() {
 *   await logout();
 *   clearCache();
 *   navigate("/login");
 * }
 */
export function clearCache(): void {
	cache.clear();
}

/**
 * Async data hook with in-memory caching. Works like `useAsyncData` but
 * avoids redundant network calls when the same data is requested again
 * (e.g. navigating away from a page and back).
 *
 * Cache behaviour:
 * - **Key**: Provided via `options.key`. Must be unique per logical data source.
 *   Use the same key with `clearCacheEntry` to invalidate.
 * - **Hit**: Data is returned synchronously on the initial render —
 *   `loading` starts as `false`, so there's no flash of a loading state.
 * - **Miss**: The fetcher runs, and the result is stored for future hits.
 * - **TTL**: Entries expire after `options.ttl` ms (default 30 s).
 *   Expiry is checked lazily on read, not on a timer.
 * - **Max size**: Oldest entries are evicted FIFO when the cache exceeds
 *   `options.maxSize` (default 50).
 *
 * @example
 * // Cache picklist options for 5 minutes (data rarely changes)
 * const { data: types } = useCachedAsyncData(fetchDistinctTypes, [], {
 *   key: "distinctTypes",
 *   ttl: 300_000,
 * });
 *
 * // Cache search results with default 30 s TTL (back-nav returns instantly)
 * const { data } = useCachedAsyncData(
 *   () => searchAccounts({ where, orderBy, first, after }),
 *   [where, orderBy, first, after],
 *   { key: `accounts:${JSON.stringify({ where, orderBy, first, after })}` },
 * );
 *
 * // Invalidate a specific entry after a mutation
 * await updateAccount(id, fields);
 * clearCacheEntry(`account:${id}`);
 *
 * // Or clear everything (e.g. on logout)
 * clearCache();
 */
export function useCachedAsyncData<T>(
	fetcher: () => Promise<T>,
	deps: React.DependencyList,
	options: CacheOptions,
): UseAsyncDataResult<T> {
	const ttl = options.ttl ?? 30_000;
	const maxSize = options.maxSize ?? 50;
	const cacheKey = options.key;

	// Synchronous cache check during state initialization so a cache hit
	// never triggers a loading → loaded transition (avoids UI flicker).
	const cached = getValidEntry(cacheKey, ttl);

	const [data, setData] = useState<T | null>((cached?.data as T) ?? null);
	const [loading, setLoading] = useState(!cached);
	const [error, setError] = useState<string | null>(null);

	// eslint-disable-next-line react-hooks/exhaustive-deps --- deps are explicitly managed by the caller
	const memoizedFetcher = useCallback(fetcher, deps);

	useEffect(() => {
		// Re-check the cache inside the effect because deps may have changed
		// since the initial render (e.g. StrictMode double-invoke).
		const entry = getValidEntry(cacheKey, ttl);
		if (entry) {
			setData(entry.data as T);
			setLoading(false);
			setError(null);
			return;
		}

		// No cache hit — fetch from the network.
		let cancelled = false;
		setLoading(true);
		setError(null);

		memoizedFetcher()
			.then((result) => {
				if (!cancelled) {
					setEntry(cacheKey, result, maxSize);
					setData(result);
				}
			})
			.catch((err) => {
				if (!cancelled) setError(err instanceof Error ? err.message : "An error occurred");
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});

		// Cleanup: if deps change or the component unmounts before the fetch
		// completes, the cancelled flag prevents stale state updates.
		return () => {
			cancelled = true;
		};
	}, [memoizedFetcher, cacheKey, ttl, maxSize]);

	return { data, loading, error };
}
