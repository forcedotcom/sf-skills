/**
 * Custom hook for countdown timer with accessibility features
 */

import { useState, useEffect, useRef, useCallback } from "react";

/**
 * Accessibility configuration for countdown timer
 */
export interface CountdownTimerA11yConfig {
	/** Announce time remaining at these specific second marks */
	ANNOUNCE_AT_SECONDS: readonly number[];
	/** Announce every N seconds (after initial period) */
	ANNOUNCE_INTERVAL_SECONDS: number;
	/** Minimum elapsed time before starting interval announcements */
	MIN_ELAPSED_FOR_INTERVAL: number;
}

/**
 * Return value from useCountdownTimer hook
 */
export interface CountdownTimerResult {
	/** Current time remaining in seconds */
	displayTime: number;
	/** Formatted time string (MM:SS) */
	formattedTime: string;
	/** ISO 8601 duration string (e.g., PT2M15S) */
	isoTime: string;
	/** Accessibility announcement text for screen readers */
	accessibilityAnnouncement: string;
	/** Start the countdown timer */
	start: () => void;
	/** Stop the countdown timer */
	stop: () => void;
	/** Reset the countdown timer to initial time */
	reset: () => void;
}

/**
 * Configuration for countdown timer hook
 */
export interface CountdownTimerConfig {
	/** Initial time in seconds */
	initialTime: number;
	/** Callback when countdown reaches 0 */
	onExpire: () => void;
	/** Optional accessibility configuration */
	a11yConfig?: CountdownTimerA11yConfig;
}

/**
 * Default accessibility configuration
 */
const DEFAULT_A11Y_CONFIG: CountdownTimerA11yConfig = {
	ANNOUNCE_AT_SECONDS: [5, 1],
	ANNOUNCE_INTERVAL_SECONDS: 10,
	MIN_ELAPSED_FOR_INTERVAL: 10,
};

/**
 * Format time remaining as MM:SS string
 * Uses Intl.NumberFormat for zero-padding and internationalization
 *
 * @param seconds - Total seconds remaining
 * @returns Formatted time string (e.g., "05:23")
 */
function formatTimeRemaining(seconds: number): string {
	const minutes = Math.floor(seconds / 60);
	const secs = seconds % 60;

	// Use Intl.NumberFormat for zero-padding with internationalization
	const formatter = new Intl.NumberFormat(navigator.language, {
		minimumIntegerDigits: 2,
		useGrouping: false,
	});

	return `${formatter.format(minutes)}:${formatter.format(secs)}`;
}

/**
 * Format time remaining as ISO 8601 duration for ARIA
 * Used in datetime attribute of <time> element
 *
 * @param seconds - Total seconds remaining
 * @returns ISO 8601 duration string (e.g., "PT2M15S")
 */
function formatISODuration(seconds: number): string {
	const minutes = Math.floor(seconds / 60);
	const secs = seconds % 60;
	return `PT${minutes}M${secs}S`;
}

/**
 * Format time remaining for screen reader announcement
 * Uses Intl.DurationFormat if available, falls back to manual formatting
 *
 * @param seconds - Total seconds remaining
 * @returns Formatted announcement text (e.g., "2 minutes 15 seconds")
 */
function formatAccessibilityAnnouncement(seconds: number): string {
	const minutes = Math.floor(seconds / 60);
	const secs = seconds % 60;

	// Try using Intl.DurationFormat (newer API, may not be available in all browsers)
	if (typeof Intl !== "undefined" && "DurationFormat" in Intl) {
		try {
			// @ts-expect-error - DurationFormat is not yet in TypeScript lib
			const formatter = new Intl.DurationFormat(navigator.language, { style: "long" });
			return formatter.format({ minutes, seconds: secs });
		} catch {
			// Fallback to manual formatting
		}
	}

	// Manual fallback
	const parts: string[] = [];
	if (minutes > 0) {
		parts.push(`${minutes} ${minutes === 1 ? "minute" : "minutes"}`);
	}
	if (secs > 0 || minutes === 0) {
		parts.push(`${secs} ${secs === 1 ? "second" : "seconds"}`);
	}
	return parts.join(" ");
}

/**
 * Determine if an accessibility announcement should be made at this time
 *
 * @param currentTime - Current countdown time in seconds
 * @param initialTime - Initial countdown time in seconds
 * @param config - Accessibility configuration
 * @returns True if announcement should be made
 */
function shouldAnnounce(
	currentTime: number,
	initialTime: number,
	config: CountdownTimerA11yConfig,
): boolean {
	// Announce at specific second marks (5s, 1s)
	if (config.ANNOUNCE_AT_SECONDS.includes(currentTime)) {
		return true;
	}

	// Calculate elapsed time
	const elapsed = initialTime - currentTime;

	// Announce every N seconds after minimum elapsed time
	if (elapsed >= config.MIN_ELAPSED_FOR_INTERVAL) {
		return currentTime % config.ANNOUNCE_INTERVAL_SECONDS === 0;
	}

	return false;
}

/**
 * Custom hook for countdown timer with accessibility
 * Decrements from initial time to 0, provides formatted output for display and ARIA
 *
 * @param config - Timer configuration
 * @returns Timer state and control functions
 *
 * @example
 * const timer = useCountdownTimer({
 *   initialTime: 300, // 5 minutes
 *   onExpire: () => handleLogout()
 * });
 *
 * timer.start(); // Begin countdown
 *
 * <time dateTime={timer.isoTime} role="timer">
 *   {timer.formattedTime}
 * </time>
 * <div role="status" aria-live="polite" className="sr-only">
 *   {timer.accessibilityAnnouncement}
 * </div>
 */
export function useCountdownTimer({
	initialTime,
	onExpire,
	a11yConfig = DEFAULT_A11Y_CONFIG,
}: CountdownTimerConfig): CountdownTimerResult {
	const [displayTime, setDisplayTime] = useState(initialTime);
	const [accessibilityAnnouncement, setAccessibilityAnnouncement] = useState("");
	const [isActive, setIsActive] = useState(false);

	// Use refs to avoid stale closure issues
	const initialTimeRef = useRef(initialTime);
	const onExpireRef = useRef(onExpire);
	const a11yConfigRef = useRef(a11yConfig);
	const endTimeRef = useRef<number>(0);
	const previousTimeRef = useRef<number>(initialTime);

	// Update refs when props change
	useEffect(() => {
		initialTimeRef.current = initialTime;
	}, [initialTime]);

	useEffect(() => {
		onExpireRef.current = onExpire;
	}, [onExpire]);

	useEffect(() => {
		a11yConfigRef.current = a11yConfig;
	}, [a11yConfig]);

	// Countdown effect using Date.now() for accuracy
	useEffect(() => {
		if (!isActive) return;

		// Set the target end time when timer starts
		endTimeRef.current = Date.now() + initialTimeRef.current * 1000;
		previousTimeRef.current = initialTimeRef.current;

		const intervalId = setInterval(() => {
			const now = Date.now();
			const remainingMs = endTimeRef.current - now;
			const newTime = Math.max(0, Math.ceil(remainingMs / 1000));

			setDisplayTime(newTime);

			// Check if we should make an accessibility announcement
			// Only announce when the second value changes
			if (
				newTime !== previousTimeRef.current &&
				shouldAnnounce(newTime, initialTimeRef.current, a11yConfigRef.current)
			) {
				setAccessibilityAnnouncement(formatAccessibilityAnnouncement(newTime));
			}
			previousTimeRef.current = newTime;

			// Check if countdown expired
			if (newTime <= 0) {
				clearInterval(intervalId);
				setIsActive(false);
				onExpireRef.current();
			}
		}, 100); // Check more frequently for smoother updates

		return () => clearInterval(intervalId);
	}, [isActive]);

	// Control functions
	const start = useCallback(() => {
		setIsActive(true);
	}, []);

	const stop = useCallback(() => {
		setIsActive(false);
	}, []);

	const reset = useCallback(() => {
		setDisplayTime(initialTimeRef.current);
		setIsActive(false);
		setAccessibilityAnnouncement("");
	}, []);

	return {
		displayTime,
		formattedTime: formatTimeRemaining(displayTime),
		isoTime: formatISODuration(displayTime),
		accessibilityAnnouncement,
		start,
		stop,
		reset,
	};
}
