import { useCallback, useEffect, useState } from "react";

interface UseAsyncDataResult<T> {
	data: T | null;
	loading: boolean;
	error: string | null;
}

/**
 * Runs an async fetcher on mount and whenever `deps` change.
 * Returns the loading/error/data state. Does not cache — every call
 * to the fetcher hits the source directly.
 *
 * A cleanup flag prevents state updates if the component unmounts
 * or deps change before the fetch completes (avoids React warnings
 * and stale updates from out-of-order responses).
 */
export function useAsyncData<T>(
	fetcher: () => Promise<T>,
	deps: React.DependencyList,
): UseAsyncDataResult<T> {
	const [data, setData] = useState<T | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	// Re-create the fetcher reference only when deps change.
	// eslint-disable-next-line react-hooks/exhaustive-deps --- deps are explicitly managed by the caller
	const memoizedFetcher = useCallback(fetcher, deps);

	useEffect(() => {
		// Guard against setting state after unmount or dep change.
		let cancelled = false;
		setLoading(true);
		setError(null);

		memoizedFetcher()
			.then((result) => {
				if (!cancelled) setData(result);
			})
			.catch((err) => {
				if (!cancelled) setError(err instanceof Error ? err.message : "An error occurred");
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});

		return () => {
			cancelled = true;
		};
	}, [memoizedFetcher]);

	return { data, loading, error };
}
