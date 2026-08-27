/**
 * @description Synchronous REST Callout Service for {{ServiceName}}
 *
 * Use Case: Real-time API calls where immediate response is needed
 * - User-initiated actions requiring feedback
 * - API calls NOT triggered from DML operations
 *
 * IMPORTANT: Do NOT use synchronous callouts from triggers or DML contexts.
 *            Use rest-queueable-callout.cls template instead.
 *
 * @author {{Author}}
 * @date {{Date}}
 */
public with sharing class {{ServiceName}}Callout {

    // Named Credential reference (configured in Setup)
    private static final String NAMED_CREDENTIAL = 'callout:{{NamedCredentialName}}';

    // Default timeout (max 120000 ms = 120 seconds)
    private static final Integer DEFAULT_TIMEOUT = 120000;

    /**
     * @description Make HTTP request to external API
     * @param method HTTP method (GET, POST, PUT, PATCH, DELETE)
     * @param endpoint API endpoint path (appended to Named Credential base URL)
     * @param body Request body (null for GET/DELETE)
     * @return HttpResponse from external API
     */
    public static HttpResponse makeRequest(String method, String endpoint, String body) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(NAMED_CREDENTIAL + endpoint);
        req.setMethod(method);
        req.setHeader('Content-Type', 'application/json');
        req.setHeader('Accept', 'application/json');
        req.setTimeout(DEFAULT_TIMEOUT);

        if (String.isNotBlank(body) && (method == 'POST' || method == 'PUT' || method == 'PATCH')) {
            req.setBody(body);
        }

        Http http = new Http();
        return http.send(req);
    }

    /**
     * @description GET request
     * @param endpoint API endpoint path
     * @return Parsed response as Map
     */
    public static Map<String, Object> get(String endpoint) {
        HttpResponse res = makeRequest('GET', endpoint, null);
        return handleResponse(res);
    }

    /**
     * @description GET request with query parameters
     * @param endpoint API endpoint path
     * @param params Query parameters
     * @return Parsed response as Map
     */
    public static Map<String, Object> get(String endpoint, Map<String, String> params) {
        String queryString = buildQueryString(params);
        String fullEndpoint = String.isNotBlank(queryString)
            ? endpoint + '?' + queryString
            : endpoint;
        return get(fullEndpoint);
    }

    /**
     * @description POST request
     * @param endpoint API endpoint path
     * @param payload Request body as Map
     * @return Parsed response as Map
     */
    public static Map<String, Object> post(String endpoint, Map<String, Object> payload) {
        HttpResponse res = makeRequest('POST', endpoint, JSON.serialize(payload));
        return handleResponse(res);
    }

    /**
     * @description PUT request (full resource update)
     * @param endpoint API endpoint path
     * @param payload Request body as Map
     * @return Parsed response as Map
     */
    public static Map<String, Object> put(String endpoint, Map<String, Object> payload) {
        HttpResponse res = makeRequest('PUT', endpoint, JSON.serialize(payload));
        return handleResponse(res);
    }

    /**
     * @description PATCH request (partial resource update)
     * @param endpoint API endpoint path
     * @param payload Request body as Map
     * @return Parsed response as Map
     */
    public static Map<String, Object> patch(String endpoint, Map<String, Object> payload) {
        HttpResponse res = makeRequest('PATCH', endpoint, JSON.serialize(payload));
        return handleResponse(res);
    }

    /**
     * @description DELETE request
     * @param endpoint API endpoint path
     * @return Parsed response as Map (may be empty for 204)
     */
    public static Map<String, Object> del(String endpoint) {
        HttpResponse res = makeRequest('DELETE', endpoint, null);
        return handleResponse(res);
    }

    /**
     * @description Handle HTTP response and parse JSON
     * @param res HttpResponse from callout
     * @return Parsed response as Map
     * @throws CalloutException for error status codes
     */
    private static Map<String, Object> handleResponse(HttpResponse res) {
        Integer statusCode = res.getStatusCode();
        String responseBody = res.getBody();

        // Log for debugging (consider removing in production or use custom logging)
        System.debug(LoggingLevel.DEBUG, 'Response Status: ' + statusCode);
        System.debug(LoggingLevel.DEBUG, 'Response Body: ' + responseBody);

        // Success (2xx)
        if (statusCode >= 200 && statusCode < 300) {
            if (String.isBlank(responseBody) || statusCode == 204) {
                return new Map<String, Object>();
            }
            return (Map<String, Object>) JSON.deserializeUntyped(responseBody);
        }

        // Client Error (4xx)
        if (statusCode >= 400 && statusCode < 500) {
            String errorMessage = parseErrorMessage(responseBody);
            throw new ClientException('Client Error (' + statusCode + '): ' + errorMessage);
        }

        // Server Error (5xx)
        if (statusCode >= 500) {
            throw new ServerException('Server Error (' + statusCode + '): ' + responseBody);
        }

        // Unexpected status
        throw new CalloutException('Unexpected status code: ' + statusCode);
    }

    /**
     * @description Parse error message from response body
     * @param responseBody Raw response body
     * @return Error message string
     */
    private static String parseErrorMessage(String responseBody) {
        try {
            Map<String, Object> errorResponse = (Map<String, Object>) JSON.deserializeUntyped(responseBody);

            // Common error message field names
            if (errorResponse.containsKey('error')) {
                Object error = errorResponse.get('error');
                if (error instanceof String) {
                    return (String) error;
                } else if (error instanceof Map<String, Object>) {
                    Map<String, Object> errorObj = (Map<String, Object>) error;
                    return (String) errorObj.get('message');
                }
            }
            if (errorResponse.containsKey('message')) {
                return (String) errorResponse.get('message');
            }
            if (errorResponse.containsKey('errors')) {
                return JSON.serialize(errorResponse.get('errors'));
            }

            return responseBody;
        } catch (Exception e) {
            return responseBody;
        }
    }

    /**
     * @description Build URL query string from parameters
     * @param params Map of query parameters
     * @return Encoded query string
     */
    private static String buildQueryString(Map<String, String> params) {
        if (params == null || params.isEmpty()) {
            return '';
        }

        List<String> pairs = new List<String>();
        for (String key : params.keySet()) {
            String value = params.get(key);
            if (String.isNotBlank(value)) {
                pairs.add(EncodingUtil.urlEncode(key, 'UTF-8') + '=' +
                          EncodingUtil.urlEncode(value, 'UTF-8'));
            }
        }
        return String.join(pairs, '&');
    }

    /**
     * @description Client error (4xx) exception
     */
    public class ClientException extends Exception {}

    /**
     * @description Server error (5xx) exception
     */
    public class ServerException extends Exception {}
}
