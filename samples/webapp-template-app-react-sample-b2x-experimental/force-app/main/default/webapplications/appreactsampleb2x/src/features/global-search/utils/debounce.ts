/**
 * Debounce Utility
 *
 * Provides debouncing functionality for functions with React-safe cleanup methods.
 */

/**
 * Interface for the debounced function, exposing utility methods.
 */
export interface DebouncedFunc<T extends (...args: any[]) => any> {
	/**
	 * Call the original function, but delayed.
	 */
	(...args: Parameters<T>): void;
	/**
	 * Cancel any pending execution.
	 */
	cancel: () => void;
	/**
	 * Immediately execute the pending function (if any) and clear the timer.
	 * Useful for saving data before unmounting.
	 */
	flush: () => void;
}

/**
 * Creates a debounced function that delays invoking func until after wait milliseconds
 * have elapsed since the last time the debounced function was invoked.
 *
 * @param func - The function to debounce
 * @param wait - The number of milliseconds to delay
 * @returns A debounced function with .cancel() and .flush() methods
 *
 * @remarks
 * - Includes .cancel() method for cleanup in React useEffects
 * - Includes .flush() method to immediately execute pending calls
 * - Preserves function context (this binding)
 * - Type-safe with TypeScript generics
 *
 * @example
 * ```tsx
 * const debouncedSearch = debounce((query: string) => {
 *   performSearch(query);
 * }, 300);
 *
 * // In useEffect cleanup
 * return () => debouncedSearch.cancel();
 * ```
 */
export function debounce<T extends (...args: any[]) => any>(
	func: T,
	wait: number,
): DebouncedFunc<T> {
	// 1. Type Safety: Use a generic return type compatible with Browser and Node
	let timeoutId: ReturnType<typeof setTimeout> | null = null;
	let lastContext: ThisParameterType<T> | null = null;
	let lastArgs: Parameters<T> | null = null;
	function debounced(this: ThisParameterType<T>, ...args: Parameters<T>) {
		// 2. Context Safety: Capture 'this' to support class methods
		// eslint-disable-next-line @typescript-eslint/no-this-alias -- required for debouncing class methods
		lastContext = this;
		lastArgs = args;
		if (timeoutId) {
			clearTimeout(timeoutId);
		}
		timeoutId = setTimeout(() => {
			func.apply(lastContext, lastArgs as Parameters<T>);
			timeoutId = null;
			lastArgs = null;
			lastContext = null;
		}, wait);
	}
	// 3. React Safety: Add a cancel method to clear pending timers
	debounced.cancel = () => {
		if (timeoutId) {
			clearTimeout(timeoutId);
			timeoutId = null;
		}
		lastArgs = null;
		lastContext = null;
	};

	debounced.flush = () => {
		if (timeoutId && lastArgs) {
			func.apply(lastContext, lastArgs);
			debounced.cancel();
		}
	};
	return debounced;
}
