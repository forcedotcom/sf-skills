/** Default debounce delay for keystroke-driven inputs. */
export const FILTER_DEBOUNCE_MS = 300;

/**
 * Creates a debounced version of `fn`. Each call resets the internal timer;
 * `fn` runs only after the timer expires without being reset.
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
