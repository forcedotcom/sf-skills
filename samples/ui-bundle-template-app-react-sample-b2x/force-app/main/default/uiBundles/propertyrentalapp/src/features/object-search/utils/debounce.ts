/** Default debounce delay for keystroke-driven filter inputs (search, text, numeric). */
export const FILTER_DEBOUNCE_MS = 300;

/** Creates a debounced version of a function; each call resets the timer so only the last call within `ms` fires. */
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
