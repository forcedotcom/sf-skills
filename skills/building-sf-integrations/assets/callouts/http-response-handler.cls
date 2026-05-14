/**
 * @description HTTP Response Handler Utility
 *
 * Use Case: Standardized response parsing and error handling
 * - Parse JSON responses to typed objects
 * - Handle different content types
 * - Extract error messages from various API formats
 * - Logging for debugging
 *
 * @author {{Author}}
 * @date {{Date}}
 */
public with sharing class HttpResponseHandler {

    /**
     * @description Parse HTTP response to Map
     * @param response HttpResponse to parse
     * @return Parsed response as Map<String, Object>
     * @throws HttpResponseException for error status codes
     */
    public static Map<String, Object> parseJsonResponse(HttpResponse response) {
        validateSuccessResponse(response);

        String body = response.getBody();
        if (String.isBlank(body) || response.getStatusCode() == 204) {
            return new Map<String, Object>();
        }

        try {
            return (Map<String, Object>) JSON.deserializeUntyped(body);
        } catch (JSONException e) {
            throw new HttpResponseException(
                'Failed to parse JSON response: ' + e.getMessage() +
                '. Body: ' + body.left(500)
            );
        }
    }

    /**
     * @description Parse HTTP response to List
     * @param response HttpResponse to parse
     * @return Parsed response as List<Object>
     * @throws HttpResponseException for error status codes
     */
    public static List<Object> parseJsonArrayResponse(HttpResponse response) {
        validateSuccessResponse(response);

        String body = response.getBody();
        if (String.isBlank(body)) {
            return new List<Object>();
        }

        try {
            return (List<Object>) JSON.deserializeUntyped(body);
        } catch (JSONException e) {
            throw new HttpResponseException(
                'Failed to parse JSON array response: ' + e.getMessage()
            );
        }
    }

    /**
     * @description Parse HTTP response to specific type
     * @param response HttpResponse to parse
     * @param targetType Apex type to deserialize to
     * @return Deserialized object
     * @throws HttpResponseException for error status codes
     */
    public static Object parseTypedResponse(HttpResponse response, Type targetType) {
        validateSuccessResponse(response);

        String body = response.getBody();
        if (String.isBlank(body)) {
            return null;
        }

        try {
            return JSON.deserialize(body, targetType);
        } catch (JSONException e) {
            throw new HttpResponseException(
                'Failed to deserialize response to ' + targetType.getName() + ': ' + e.getMessage()
            );
        }
    }

    /**
     * @description Validate response is successful (2xx)
     * @param response HttpResponse to validate
     * @throws HttpResponseException for non-2xx status codes
     */
    public static void validateSuccessResponse(HttpResponse response) {
        Integer statusCode = response.getStatusCode();

        // Log response for debugging
        logResponse(response);

        if (statusCode >= 200 && statusCode < 300) {
            return; // Success
        }

        String errorMessage = extractErrorMessage(response);

        if (statusCode >= 400 && statusCode < 500) {
            throw new ClientErrorException(
                'HTTP ' + statusCode + ': ' + errorMessage
            );
        }

        if (statusCode >= 500) {
            throw new ServerErrorException(
                'HTTP ' + statusCode + ': ' + errorMessage
            );
        }

        throw new HttpResponseException(
            'Unexpected HTTP status ' + statusCode + ': ' + errorMessage
        );
    }

    /**
     * @description Extract error message from response body
     * @param response HttpResponse containing error
     * @return Error message string
     */
    public static String extractErrorMessage(HttpResponse response) {
        String body = response.getBody();

        if (String.isBlank(body)) {
            return 'No response body';
        }

        // Try to parse as JSON error
        try {
            Map<String, Object> errorObj = (Map<String, Object>) JSON.deserializeUntyped(body);

            // Common error formats
            // Format 1: { "error": "message" }
            if (errorObj.containsKey('error')) {
                Object error = errorObj.get('error');
                if (error instanceof String) {
                    return (String) error;
                }
                if (error instanceof Map<String, Object>) {
                    Map<String, Object> errorMap = (Map<String, Object>) error;
                    if (errorMap.containsKey('message')) {
                        return (String) errorMap.get('message');
                    }
                }
            }

            // Format 2: { "message": "error message" }
            if (errorObj.containsKey('message')) {
                return (String) errorObj.get('message');
            }

            // Format 3: { "errors": [{ "message": "..." }] }
            if (errorObj.containsKey('errors')) {
                Object errors = errorObj.get('errors');
                if (errors instanceof List<Object>) {
                    List<Object> errorList = (List<Object>) errors;
                    if (!errorList.isEmpty()) {
                        Object firstError = errorList[0];
                        if (firstError instanceof Map<String, Object>) {
                            Map<String, Object> errMap = (Map<String, Object>) firstError;
                            if (errMap.containsKey('message')) {
                                return (String) errMap.get('message');
                            }
                        }
                        if (firstError instanceof String) {
                            return (String) firstError;
                        }
                    }
                }
            }

            // Format 4: { "detail": "error detail" }
            if (errorObj.containsKey('detail')) {
                return (String) errorObj.get('detail');
            }

            // Fallback: return serialized error object
            return JSON.serialize(errorObj);

        } catch (Exception e) {
            // Not JSON - return raw body (truncated)
            return body.left(1000);
        }
    }

    /**
     * @description Log HTTP response for debugging
     * @param response HttpResponse to log
     */
    private static void logResponse(HttpResponse response) {
        System.debug(LoggingLevel.DEBUG, '=== HTTP Response ===');
        System.debug(LoggingLevel.DEBUG, 'Status: ' + response.getStatusCode() + ' ' + response.getStatus());

        // Log important headers
        String[] headerKeys = new String[]{ 'Content-Type', 'X-Request-Id', 'Retry-After', 'X-RateLimit-Remaining' };
        for (String key : headerKeys) {
            String value = response.getHeader(key);
            if (String.isNotBlank(value)) {
                System.debug(LoggingLevel.DEBUG, key + ': ' + value);
            }
        }

        // Log body (truncated for large responses)
        String body = response.getBody();
        if (String.isNotBlank(body)) {
            System.debug(LoggingLevel.DEBUG, 'Body: ' + body.left(5000));
        }
    }

    /**
     * @description Get response header value
     * @param response HttpResponse
     * @param headerName Header name to retrieve
     * @return Header value or null
     */
    public static String getHeader(HttpResponse response, String headerName) {
        return response.getHeader(headerName);
    }

    /**
     * @description Check if response indicates success
     * @param response HttpResponse to check
     * @return True if status code is 2xx
     */
    public static Boolean isSuccess(HttpResponse response) {
        Integer statusCode = response.getStatusCode();
        return statusCode >= 200 && statusCode < 300;
    }

    /**
     * @description Check if response indicates rate limiting
     * @param response HttpResponse to check
     * @return True if status code is 429
     */
    public static Boolean isRateLimited(HttpResponse response) {
        return response.getStatusCode() == 429;
    }

    /**
     * @description Base exception for HTTP response errors
     */
    public virtual class HttpResponseException extends Exception {}

    /**
     * @description Exception for 4xx client errors
     */
    public class ClientErrorException extends HttpResponseException {}

    /**
     * @description Exception for 5xx server errors
     */
    public class ServerErrorException extends HttpResponseException {}
}
