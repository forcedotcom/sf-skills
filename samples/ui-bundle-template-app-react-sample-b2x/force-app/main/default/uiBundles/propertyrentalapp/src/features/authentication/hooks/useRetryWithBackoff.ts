/**
 * Custom hook for retry logic with exponential backoff
 */

import { useState, useCallback } from "react";

export interface UseRetryWithBackoffOptions {
	/** Initial delay in milliseconds */
	initialDelay: number;
	/** Maximum number of retry attempts */
	maxAttempts: number;
	/** Maximum delay in milliseconds */
	maxDelay: number;
}

export interface UseRetryWithBackoffResult {
	/** Current number of retry attempts */
	retryAttempts: number;
	/** Current retry delay in milliseconds */
	currentRetryDelay: number;
	/** Whether max retry attempts have been reached */
	maxRetriesReached: boolean;
	/** Schedule a retry with exponential backoff, returns timeout ID for cancellation */
	scheduleRetry: (callback: () => void) => ReturnType<typeof setTimeout> | undefined;
	/** Reset retry state after successful operation */
	resetRetry: () => void;
}

/**
 * Hook for managing retry logic with exponential backoff
 *
 * @param options - Configuration for retry behavior
 * @returns Retry state and control functions
 *
 * @example
 * const retry = useRetryWithBackoff({
 *   initialDelay: 2000,
 *   maxAttempts: 10,
 *   maxDelay: 1800000
 * });
 *
 * async function fetchData() {
 *   try {
 *     const data = await apiCall();
 *     retry.resetRetry();
 *     return data;
 *   } catch (error) {
 *     if (retry.maxRetriesReached) {
 *       console.error('Max retries reached');
 *       return;
 *     }
 *     retry.scheduleRetry(() => fetchData());
 *   }
 * }
 */
export function useRetryWithBackoff(
	options: UseRetryWithBackoffOptions,
): UseRetryWithBackoffResult {
	const { initialDelay, maxAttempts, maxDelay } = options;

	const [retryAttempts, setRetryAttempts] = useState<number>(0);
	const [currentRetryDelay, setCurrentRetryDelay] = useState<number>(initialDelay);

	const maxRetriesReached = retryAttempts >= maxAttempts;

	/**
	 * Reset retry state after successful operation
	 */
	const resetRetry = useCallback(() => {
		setRetryAttempts(0);
		setCurrentRetryDelay(initialDelay);
	}, [initialDelay]);

	/**
	 * Schedule a retry with exponential backoff
	 * Returns the timeout ID which can be used to cancel the retry if needed
	 */
	const scheduleRetry = useCallback(
		(callback: () => void) => {
			if (retryAttempts >= maxAttempts) {
				console.error("[useRetryWithBackoff] Max retry attempts reached");
				return undefined;
			}

			console.warn(
				`[useRetryWithBackoff] Retry attempt ${retryAttempts + 1}/${maxAttempts} in ${currentRetryDelay}ms`,
			);

			const timeoutId = setTimeout(() => {
				callback();
			}, currentRetryDelay);

			setRetryAttempts((prev) => prev + 1);
			// Double the delay for next retry, capped at maxDelay
			setCurrentRetryDelay((prev) => Math.min(prev * 2, maxDelay));

			return timeoutId;
		},
		[retryAttempts, currentRetryDelay, maxAttempts, maxDelay],
	);

	return {
		retryAttempts,
		currentRetryDelay,
		maxRetriesReached,
		scheduleRetry,
		resetRetry,
	};
}
