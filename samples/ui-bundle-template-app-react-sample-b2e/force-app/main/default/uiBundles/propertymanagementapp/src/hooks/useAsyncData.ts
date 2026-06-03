import { useEffect, useRef, useState } from 'react';

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
  deps: React.DependencyList
): UseAsyncDataResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generation, setGeneration] = useState(0);

  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  // Detect dep changes during render to reset loading state and bump generation
  const [prevDeps, setPrevDeps] = useState(deps);
  if (
    deps.length !== prevDeps.length ||
    deps.some((d, i) => d !== prevDeps[i])
  ) {
    setPrevDeps(deps);
    setGeneration(g => g + 1);
    if (!loading) setLoading(true);
    if (error !== null) setError(null);
  }

  useEffect(() => {
    let cancelled = false;

    fetcherRef
      .current()
      .then(result => {
        if (!cancelled) setData(result);
      })
      .catch(err => {
        console.error(err);
        if (!cancelled)
          setError(err instanceof Error ? err.message : 'An error occurred');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [generation]);

  return { data, loading, error };
}
