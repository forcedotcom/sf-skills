/** Default debounce delay for keystroke-driven filter inputs (search, text, numeric). */
export const FILTER_DEBOUNCE_MS = 300;

/**
 * Creates a debounced version of the provided function.
 *
 * Each call to the returned function resets the internal timer. The wrapped
 * function is only invoked once the timer expires without being reset. This
 * makes it ideal for rate-limiting high-frequency events like input changes.
 *
 * @typeParam T - The function signature to debounce.
 * @param fn - The function to debounce.
 * @param ms - The debounce delay in milliseconds.
 * @returns A new function with the same signature that delays execution.
 */
export function debounce<T extends (...args: any[]) => void>(
	fn: T,
	ms: number,
): (...args: Parameters<T>) => void {
	let timer: ReturnType<typeof setTimeout> | undefined;
	return (...args: Parameters<T>) => {
		clearTimeout(timer);
		timer = setTimeout(() => fn(...args), ms);
	};
}
