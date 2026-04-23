import { useEffect, useRef, useState } from "react";

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

	const fetcherRef = useRef(fetcher);
	useEffect(() => {
		fetcherRef.current = fetcher;
	});

	useEffect(() => {
		let cancelled = false;
		setLoading(true);
		setError(null);

		fetcherRef
			.current()
			.then((result) => {
				if (!cancelled) setData(result);
			})
			.catch((err) => {
				console.error(err);
				if (!cancelled) setError(err instanceof Error ? err.message : "An error occurred");
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});

		return () => {
			cancelled = true;
		};
		// eslint-disable-next-line react-hooks/exhaustive-deps --- deps are explicitly managed by the caller
	}, deps);

	return { data, loading, error };
}
