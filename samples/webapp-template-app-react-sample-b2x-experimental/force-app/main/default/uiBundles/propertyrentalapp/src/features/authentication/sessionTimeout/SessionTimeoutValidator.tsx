/**
 * Session timeout validator component
 * Main orchestrator for session monitoring and timeout warnings
 */

import { useEffect, useState, useCallback, useRef } from "react";
import { useLocation } from "react-router";
import { X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { pollSessionTimeServlet, extendSessionTime } from "./sessionTimeService";
import { useCountdownTimer } from "../hooks/useCountdownTimer";
import { useRetryWithBackoff } from "../hooks/useRetryWithBackoff";
import { Alert, AlertTitle, AlertDescription } from "../../../components/ui/alert";
import { Button } from "../../../components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogDescription,
	DialogFooter,
} from "../../../components/ui/dialog";
import {
	STORAGE_KEYS,
	LABELS,
	INITIAL_RETRY_DELAY,
	MAX_RETRY_ATTEMPTS,
	MAX_RETRY_DELAY,
	SESSION_WARNING_TIME,
} from "./sessionTimeoutConfig";
import { ROUTES } from "../authenticationConfig";

/**
 * Configuration for session timeout monitoring
 */
interface SessionTimeoutConfig {
	/** Community base path (e.g., "/sfsites/c/") */
	basePath: string;
	/** Whether current user is a guest user */
	isGuest: boolean;
}

/**
 * Return value from useSessionTimeout hook
 */
interface SessionTimeoutResult {
	/** Seconds remaining in current session (null if no response received yet) */
	timeLeftInSession: number | null;
	/** Whether warning modal should be displayed */
	showWarningModal: boolean;
	/** Function to extend the session */
	extendSession: () => Promise<void>;
	/** Function to logout the user */
	logout: () => void;
	/** Function to check session status via API */
	checkSession: () => Promise<void>;
	/** Number of failed retry attempts */
	retryAttempts: number;
	/** Whether currently polling the session API */
	isPolling: boolean;
}

/**
 * Props for SessionTimeoutValidator component
 */
export interface SessionTimeoutValidatorProps {
	/** Community base path */
	basePath: string;

	// Optional callbacks
	/** Called when session expires and user is logged out */
	onSessionExpired?: () => void;
	/** Called when session is extended with new time remaining */
	onSessionExtended?: (newTimeRemaining: number) => void;
}

/**
 * Props for SessionWarningModal component
 */
interface SessionWarningModalProps {
	/** Whether modal is visible */
	isOpen: boolean;
	/** Seconds remaining until session expires */
	timeRemaining: number;
	/** Called when user clicks "Continue Working" button */
	onExtendSession: () => void;
	/** Called when user clicks "Log Out" button */
	onLogout: () => void;
	/** Called when countdown timer reaches 0 (before logout) */
	onCountdownExpire: () => void;
}

/**
 * Props for SessionExpiredAlert component
 */
interface SessionExpiredAlertProps {
	/** Whether alert should be shown */
	show: boolean;
	/** Called when user dismisses the alert */
	onDismiss: () => void;
	/** Custom message to display (optional) */
	message?: string;
}

/**
 * Custom hook for session timeout monitoring
 * Polls SessionTimeServlet at calculated intervals, handles retry with exponential backoff
 *
 * @internal
 */
function useSessionTimeout(config: SessionTimeoutConfig): SessionTimeoutResult {
	const { basePath, isGuest } = config;

	// Session state
	const [timeLeftInSession, setTimeLeftInSession] = useState<number | null>(null);
	const [showWarningModal, setShowWarningModal] = useState<boolean>(false);
	const [isPolling, setIsPolling] = useState<boolean>(false);

	// Retry logic with exponential backoff
	const retry = useRetryWithBackoff({
		initialDelay: INITIAL_RETRY_DELAY,
		maxAttempts: MAX_RETRY_ATTEMPTS,
		maxDelay: MAX_RETRY_DELAY,
	});

	// Refs for timer management (prevents closure issues)
	const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const isPollingRef = useRef<boolean>(false);
	const checkSessionRef = useRef<(() => Promise<void>) | null>(null);
	const extendSessionRef = useRef<(() => Promise<void>) | null>(null);

	/**
	 * Clear the current polling timeout
	 */
	const clearPollTimeout = useCallback(() => {
		if (pollTimeoutRef.current) {
			clearTimeout(pollTimeoutRef.current);
			pollTimeoutRef.current = null;
		}
	}, []);

	/**
	 * Clear the current retry timeout
	 */
	const clearRetryTimeout = useCallback(() => {
		if (retryTimeoutRef.current) {
			clearTimeout(retryTimeoutRef.current);
			retryTimeoutRef.current = null;
		}
	}, []);

	/**
	 * Schedule the next session check
	 * Clears any existing poll or retry timeouts to prevent concurrent polling
	 *
	 * @param delay - Milliseconds to wait before next check
	 */
	const scheduleCheck = useCallback(
		(delay: number) => {
			clearPollTimeout();
			clearRetryTimeout();
			pollTimeoutRef.current = setTimeout(() => {
				checkSessionRef.current?.();
			}, delay);
		},
		[clearPollTimeout, clearRetryTimeout],
	);

	/**
	 * Handle retry with exponential backoff
	 * Prevents concurrent retries by checking if a poll is already in progress
	 */
	const handleRetryWithBackoff = useCallback(
		(retryAction: () => void) => {
			// Don't schedule retry if max attempts reached
			if (retry.maxRetriesReached) {
				console.error("[useSessionTimeout] Max retry attempts reached. Stopping polling.");
				setIsPolling(false);
				isPollingRef.current = false;
				return;
			}

			// Don't schedule retry if a poll is already in progress
			if (isPollingRef.current) {
				console.warn("[useSessionTimeout] Poll already in progress, skipping retry scheduling");
				return;
			}

			// Clear any existing retry timeout before scheduling new one
			clearRetryTimeout();

			// Calculate delay and schedule retry
			const delay = retry.currentRetryDelay;
			console.warn(
				`[useSessionTimeout] Scheduling retry attempt ${retry.retryAttempts + 1}/${MAX_RETRY_ATTEMPTS} in ${delay}ms`,
			);

			// Let retry.scheduleRetry handle both the timeout and counter increment
			const timeoutId = retry.scheduleRetry(() => {
				retryTimeoutRef.current = null;
				retryAction();
			});

			if (timeoutId) {
				retryTimeoutRef.current = timeoutId;
			}
		},
		[retry, clearRetryTimeout],
	);

	/**
	 * Process the session timeout response and schedule next check
	 *
	 * @param secondsRemaining - Seconds remaining in session
	 */
	const processTimeoutResponse = useCallback(
		(secondsRemaining: number) => {
			setTimeLeftInSession(secondsRemaining);

			// Session expired
			if (secondsRemaining <= 0) {
				setShowWarningModal(false);
				// Note: logout() will be called by the component
				return;
			}

			const shouldShowWarning = secondsRemaining <= SESSION_WARNING_TIME;

			if (shouldShowWarning) {
				// Show warning modal and schedule check for when session expires
				setShowWarningModal(true);
				scheduleCheck(secondsRemaining * 1000);
			} else {
				// Schedule check for when warning should appear
				const timeUntilWarning = (secondsRemaining - SESSION_WARNING_TIME) * 1000;
				setShowWarningModal(false);
				scheduleCheck(timeUntilWarning);
			}
		},
		[scheduleCheck],
	);

	/**
	 * Check session status via API
	 */
	const checkSession = useCallback(async () => {
		// Prevent concurrent polling
		if (isPollingRef.current) {
			return;
		}

		isPollingRef.current = true;
		setIsPolling(true);

		const response = await pollSessionTimeServlet(basePath);
		isPollingRef.current = false;
		setIsPolling(false);

		if (response) {
			retry.resetRetry();
			processTimeoutResponse(response.sr);
		} else {
			handleRetryWithBackoff(() => checkSessionRef.current?.());
		}
	}, [basePath, retry, processTimeoutResponse, handleRetryWithBackoff]);

	/**
	 * Extend the session (called when user clicks "Continue Working")
	 */
	const extendSession = useCallback(async () => {
		const response = await extendSessionTime(basePath);

		if (response) {
			retry.resetRetry();
			processTimeoutResponse(response.sr);
		} else {
			handleRetryWithBackoff(() => extendSessionRef.current?.());
		}
	}, [basePath, retry, processTimeoutResponse, handleRetryWithBackoff]);

	// Update refs to always point to latest functions
	useEffect(() => {
		checkSessionRef.current = checkSession;
	}, [checkSession]);

	useEffect(() => {
		extendSessionRef.current = extendSession;
	}, [extendSession]);

	/**
	 * Logout the user
	 * Note: Navigation is handled by the component, not this hook
	 */
	const logout = useCallback(() => {
		clearPollTimeout();
		clearRetryTimeout();
		setShowWarningModal(false);
		setTimeLeftInSession(null);
		setIsPolling(false);
		isPollingRef.current = false;
	}, [clearPollTimeout, clearRetryTimeout]);

	// Initialize polling on mount (if authenticated)
	useEffect(() => {
		if (isGuest) {
			return;
		}

		checkSessionRef.current?.();

		// Cleanup on unmount
		return () => {
			clearPollTimeout();
			clearRetryTimeout();
			isPollingRef.current = false;
		};
	}, [isGuest, clearPollTimeout, clearRetryTimeout]);

	return {
		timeLeftInSession,
		showWarningModal,
		extendSession,
		logout,
		checkSession,
		retryAttempts: retry.retryAttempts,
		isPolling,
	};
}

/**
 * Session Expired Alert
 * Toast-like alert shown on login page after user is redirected due to session expiration
 *
 * @internal
 */
function SessionExpiredAlert({
	show,
	onDismiss,
	message = LABELS.invalidSessionMessage,
}: SessionExpiredAlertProps) {
	if (!show) {
		return null;
	}

	return (
		<div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-md px-4">
			<Alert variant="destructive" role="alert">
				<AlertTitle className="flex items-center justify-between">
					<span>{LABELS.sessionWarningTitle}</span>
					<Button
						variant="ghost"
						size="sm"
						onClick={onDismiss}
						aria-label={LABELS.closeLabel}
						className="h-auto p-1 hover:bg-destructive/10"
					>
						<X className="h-4 w-4" />
					</Button>
				</AlertTitle>
				<AlertDescription>{message}</AlertDescription>
			</Alert>
		</div>
	);
}

/**
 * Session Warning Modal
 * Modal dialog with countdown timer shown when session is near expiration
 *
 * @internal
 */
function SessionWarningModal({
	isOpen,
	timeRemaining,
	onExtendSession,
	onLogout,
	onCountdownExpire,
}: SessionWarningModalProps) {
	const continueButtonRef = useRef<HTMLButtonElement>(null);

	// Countdown timer with accessibility
	const timer = useCountdownTimer({
		initialTime: timeRemaining,
		onExpire: onCountdownExpire,
	});

	const { start, stop, reset, formattedTime, isoTime, accessibilityAnnouncement } = timer;

	// Consolidated timer management: handle both open/close and timeRemaining changes
	useEffect(() => {
		if (!isOpen) {
			stop();
			return;
		}

		// Modal is open: reset and start timer
		reset();
		start();
	}, [isOpen, timeRemaining, start, stop, reset]);

	// Focus the continue button when dialog opens
	useEffect(() => {
		if (isOpen) {
			continueButtonRef.current?.focus();
		}
	}, [isOpen]);

	// Handle "Continue Working" button click
	const handleContinue = useCallback(() => {
		stop();
		onExtendSession();
	}, [stop, onExtendSession]);

	// Handle "Log Out" button click
	const handleLogoutClick = useCallback(() => {
		stop();
		onLogout();
	}, [stop, onLogout]);

	return (
		<Dialog open={isOpen} onOpenChange={() => {}}>
			<DialogContent
				showCloseButton={false}
				onEscapeKeyDown={(e) => e.preventDefault()}
				onPointerDownOutside={(e) => e.preventDefault()}
				onInteractOutside={(e) => e.preventDefault()}
				className="max-w-md"
			>
				<DialogHeader>
					<DialogTitle id="session-warning-title">{LABELS.sessionWarningTitle}</DialogTitle>
					<DialogDescription id="session-warning-description">
						{LABELS.sessionWarningMessage}
					</DialogDescription>
				</DialogHeader>

				<div className="flex flex-col items-center gap-4 py-6">
					{/* Countdown Timer Display */}
					<time
						dateTime={isoTime}
						role="timer"
						aria-live="off"
						aria-atomic="true"
						aria-describedby="session-warning-description"
						className="text-5xl font-bold text-center tabular-nums text-destructive"
					>
						{formattedTime}
					</time>

					{/* Accessibility Announcement Region */}
					<div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
						{accessibilityAnnouncement}
					</div>
				</div>

				<DialogFooter className="flex gap-4 justify-end">
					<Button variant="outline" onClick={handleLogoutClick} tabIndex={2}>
						{LABELS.logoutButton}
					</Button>
					<Button variant="default" onClick={handleContinue} tabIndex={1} ref={continueButtonRef}>
						{LABELS.continueButton}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

/**
 * Session Timeout Validator
 * Main component that monitors user session and displays warnings before expiration
 *
 * Features:
 * - Polls SessionTimeServlet to monitor session status
 * - Shows warning modal when session nears expiration
 * - Handles session extension when user clicks "Continue Working"
 * - Uses AuthContext.logout() for centralized logout handling
 * - Shows expired message on login page after timeout redirect
 * - Implements exponential backoff retry for failed API calls
 * - Skips monitoring for guest users
 *
 * @example
 * <SessionTimeoutValidator
 *   basePath={basePath}
 * />
 */
export default function SessionTimeoutValidator({
	basePath,
	onSessionExpired,
	onSessionExtended,
}: SessionTimeoutValidatorProps) {
	// Get authentication state and logout method
	const { isAuthenticated, logout } = useAuth();
	const isGuest = !isAuthenticated;

	// Get current location from React Router
	const location = useLocation();

	// Session expired alert — checked once at mount via lazy initializer.
	// The session timeout handler triggers a hard navigation (window.location.replace),
	// so the component always mounts fresh on the login page after expiry.
	const [showExpiredAlert, setShowExpiredAlert] = useState(() => {
		const isLoginPage = location.pathname === ROUTES.LOGIN.PATH;
		const shouldShow =
			isLoginPage && sessionStorage.getItem(STORAGE_KEYS.SHOW_SESSION_MESSAGE) === "true";
		if (shouldShow) {
			sessionStorage.removeItem(STORAGE_KEYS.SHOW_SESSION_MESSAGE);
		}
		return shouldShow;
	});

	// Session timeout monitoring hook
	const sessionTimeout = useSessionTimeout({
		basePath,
		isGuest,
	});

	/**
	 * Handle session extension
	 * Called when user clicks "Continue Working" in warning modal
	 */
	const handleExtendSession = useCallback(async () => {
		await sessionTimeout.extendSession();

		// Call optional callback
		if (onSessionExtended && sessionTimeout.timeLeftInSession !== null) {
			onSessionExtended(sessionTimeout.timeLeftInSession);
		}
	}, [sessionTimeout, onSessionExtended]);

	/**
	 * Handle countdown expiration
	 * Checks session status with server before logging out to prevent premature logout
	 */
	const handleCountdownExpired = useCallback(async () => {
		await sessionTimeout.checkSession();
	}, [sessionTimeout]);

	/**
	 * Handle logout
	 * Called when session expires or user clicks "Log Out"
	 */
	const handleLogout = useCallback(() => {
		// Set flag in sessionStorage to show message on login page
		sessionStorage.setItem(STORAGE_KEYS.SHOW_SESSION_MESSAGE, "true");

		// Stop session monitoring (clears timeouts, resets hook state)
		sessionTimeout.logout();

		// Call optional callback
		if (onSessionExpired) {
			onSessionExpired();
		}

		// Use centralized logout from AuthContext
		// This clears auth state and redirects to logout URL
		// Pass current location as retUrl to redirect back after logout
		// Use window.location.pathname to include the base path
		logout(window.location.pathname);
	}, [sessionTimeout, logout, onSessionExpired]);

	/**
	 * Handle session timeout (automatic logout when countdown reaches 0)
	 * Only trigger logout if we've received a response (not null) and session is expired
	 */
	useEffect(() => {
		if (
			sessionTimeout.timeLeftInSession !== null &&
			sessionTimeout.timeLeftInSession <= 0 &&
			!isGuest
		) {
			handleLogout();
		}
	}, [sessionTimeout.timeLeftInSession, isGuest, handleLogout]);

	/**
	 * Dismiss expired session alert
	 */
	const handleDismissAlert = useCallback(() => {
		setShowExpiredAlert(false);
	}, []);

	return (
		<>
			{/* Session Warning Modal - only render when open */}
			{sessionTimeout.showWarningModal && (
				<SessionWarningModal
					isOpen={sessionTimeout.showWarningModal}
					timeRemaining={sessionTimeout.timeLeftInSession ?? 0}
					onExtendSession={handleExtendSession}
					onLogout={handleLogout}
					onCountdownExpire={handleCountdownExpired}
				/>
			)}

			{/* Session Expired Alert (shown on login page) - only render when showExpiredAlert is true */}
			{showExpiredAlert && (
				<SessionExpiredAlert show={showExpiredAlert} onDismiss={handleDismissAlert} />
			)}
		</>
	);
}
