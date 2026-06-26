/**
 * @description Retry Handler with Exponential Backoff for HTTP Callouts
 *
 * Use Case: Handle transient failures with intelligent retry
 * - Network timeouts
 * - 5xx server errors
 * - Rate limiting (429)
 *
 * Features:
 * - Exponential backoff between retries
 * - Configurable retry count
 * - Jitter to prevent thundering herd
 * - Distinguishes retryable vs non-retryable errors
 *
 * IMPORTANT: Apex doesn't have Thread.sleep(), so retry with backoff
 *            is implemented via Queueable job scheduling for async contexts.
 *            For sync contexts, this provides immediate retry without delay.
 *
 * @author {{Author}}
 * @date {{Date}}
 */
public with sharing class CalloutRetryHandler {

    // Configuration
    private static final Integer MAX_RETRIES = 3;
    private static final Integer BASE_DELAY_MS = 1000; // 1 second
    private static final Integer MAX_DELAY_MS = 30000; // 30 seconds

    // Retryable status codes
    private static final Set<Integer> RETRYABLE_STATUS_CODES = new Set<Integer>{
        408, // Request Timeout
        429, // Too Many Requests (Rate Limited)
        500, // Internal Server Error
        502, // Bad Gateway
        503, // Service Unavailable
        504  // Gateway Timeout
    };

    /**
     * @description Execute HTTP request with retry logic (immediate retries)
     * @param request HttpRequest to execute
     * @return HttpResponse from successful call
     * @throws CalloutException if all retries exhausted
     */
    public static HttpResponse executeWithRetry(HttpRequest request) {
        return executeWithRetry(request, MAX_RETRIES);
    }

    /**
     * @description Execute HTTP request with configurable retry count
     * @param request HttpRequest to execute
     * @param maxRetries Maximum retry attempts
     * @return HttpResponse from successful call
     * @throws CalloutException if all retries exhausted
     */
    public static HttpResponse executeWithRetry(HttpRequest request, Integer maxRetries) {
        Integer retryCount = 0;
        HttpResponse response;
        Exception lastException;

        while (retryCount <= maxRetries) {
            try {
                Http http = new Http();
                response = http.send(request);

                Integer statusCode = response.getStatusCode();

                // Success - return immediately
                if (statusCode >= 200 && statusCode < 300) {
                    return response;
                }

                // Client error (4xx except 408, 429) - don't retry
                if (statusCode >= 400 && statusCode < 500 &&
                    !RETRYABLE_STATUS_CODES.contains(statusCode)) {
                    throw new NonRetryableException(
                        'Client Error (' + statusCode + '): ' + response.getBody()
                    );
                }

                // Retryable error - check if we should retry
                if (RETRYABLE_STATUS_CODES.contains(statusCode)) {
                    retryCount++;
                    if (retryCount > maxRetries) {
                        throw new RetryExhaustedException(
                            'Max retries exhausted. Last status: ' + statusCode +
                            ', Body: ' + response.getBody()
                        );
                    }

                    // Log retry attempt
                    System.debug(LoggingLevel.WARN,
                        'Retryable error (' + statusCode + '). Attempt ' + retryCount +
                        ' of ' + maxRetries);

                    // For 429, check Retry-After header
                    if (statusCode == 429) {
                        String retryAfter = response.getHeader('Retry-After');
                        if (String.isNotBlank(retryAfter)) {
                            System.debug(LoggingLevel.WARN, 'Rate limited. Retry-After: ' + retryAfter);
                        }
                    }

                    // Continue to next retry (no delay in sync Apex)
                    continue;
                }

                // Other status codes - don't retry
                return response;

            } catch (CalloutException e) {
                // Network/connection error
                lastException = e;
                retryCount++;

                if (retryCount > maxRetries) {
                    throw new RetryExhaustedException(
                        'Max retries exhausted after CalloutException: ' + e.getMessage()
                    );
                }

                System.debug(LoggingLevel.WARN,
                    'CalloutException on attempt ' + retryCount + ': ' + e.getMessage());
            }
        }

        // Should not reach here, but handle edge case
        throw new RetryExhaustedException('Unexpected retry loop exit');
    }

    /**
     * @description Calculate delay with exponential backoff and jitter
     *              (Useful for scheduled retry jobs)
     * @param retryAttempt Current retry attempt (1-based)
     * @return Delay in milliseconds
     */
    public static Integer calculateBackoffDelay(Integer retryAttempt) {
        // Exponential backoff: baseDelay * 2^(attempt-1)
        Integer exponentialDelay = BASE_DELAY_MS * (Integer) Math.pow(2, retryAttempt - 1);

        // Add jitter (random 0-25% of delay)
        Double jitter = Math.random() * 0.25 * exponentialDelay;
        Integer delayWithJitter = exponentialDelay + (Integer) jitter;

        // Cap at max delay
        return Math.min(delayWithJitter, MAX_DELAY_MS);
    }

    /**
     * @description Check if HTTP status code is retryable
     * @param statusCode HTTP status code
     * @return True if request should be retried
     */
    public static Boolean isRetryable(Integer statusCode) {
        return RETRYABLE_STATUS_CODES.contains(statusCode);
    }

    /**
     * @description Exception for non-retryable errors (4xx client errors)
     */
    public class NonRetryableException extends Exception {}

    /**
     * @description Exception when all retry attempts exhausted
     */
    public class RetryExhaustedException extends Exception {}
}
