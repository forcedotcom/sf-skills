import { useCallback, useEffect, useRef } from "react";
import { debounce, FILTER_DEBOUNCE_MS } from "../utils/debounce";

/**
 * Returns a stable debounced wrapper around the provided callback.
 *
 * The wrapper always invokes the *latest* version of `fn` (via a ref),
 * so the debounce timer is never reset when `fn` changes — only when
 * the caller invokes the returned function again.
 *
 * @param fn - The callback to debounce.
 * @param delay - Debounce delay in ms. Defaults to `FILTER_DEBOUNCE_MS`.
 */
export function useDebouncedCallback<T extends (...args: any[]) => void>(
	fn: T,
	delay: number = FILTER_DEBOUNCE_MS,
): (...args: Parameters<T>) => void {
	const fnRef = useRef(fn);
	const debouncedRef = useRef<((...args: any[]) => void) | null>(null);

	useEffect(() => {
		fnRef.current = fn;
	});

	useEffect(() => {
		debouncedRef.current = debounce((...args: any[]) => {
			fnRef.current(...(args as Parameters<T>));
		}, delay);
	}, [delay]);

	return useCallback((...args: Parameters<T>) => {
		debouncedRef.current?.(...args);
	}, []);
}
