/**
 * Utility class for Web Application authentication REST endpoints.
 */
public without sharing class UIBundleAuthUtils {

    /**
     * Exception for authentication errors with HTTP status code support.
     */
    public class AuthException extends Exception {
        public Integer statusCode { get; private set; } // HTTP status code (e.g. 400, 500)
        public List<String> messages { get; private set; } // List of error messages

        public AuthException(Integer statusCode, String message) {
            this.statusCode = statusCode;
            this.messages = new List<String>{ message };
        }

        public AuthException(Integer statusCode, List<String> messages) {
            this.statusCode = statusCode;
            this.messages = new List<String>(messages);
        }
    }

    /**
     * Validates and sanitizes redirect URL to prevent open redirect vulnerabilities.
     * @param url The URL to validate.
     * @param defaultUrl Fallback URL if validation fails.
     * @return Sanitized URL or defaultUrl if invalid.
     */
    public static String getSanitizedStartUrl(String url, String defaultUrl) {
        if (String.isBlank(url) || url.equals('/')) { return defaultUrl; }
        
        String decoded; // Decode URL to catch encoded bypasses (%2f%2f -> //)
        try {
            decoded = EncodingUtil.urlDecode(url, 'UTF-8');
        } catch (Exception e) {
            return defaultUrl;
        }
        
        // Must start with / but not // (protocol-relative)
        if (!decoded.startsWith('/') || decoded.startsWith('//')) { return defaultUrl; }
        // Reject backslashes (some browsers treat \ as /)
        if (decoded.contains('\\')) { return defaultUrl; }
        // Reject @ which can indicate user info in URL (//user@evil.com)
        if (decoded.contains('@')) { return defaultUrl; }
        // Reject : which could indicate protocol or port manipulation
        if (decoded.contains(':')) { return defaultUrl; }
        // Reject control characters (ASCII < 32) and DEL (127)
        for (Integer i = 0; i < decoded.length(); i++) {
            Integer charCode = decoded.charAt(i);
            if (charCode < 32 || charCode == 127) { return defaultUrl; }
        }
        
        return defaultUrl + url;
    }

    /**
     * Logs an error message and stack trace to the system debug log.
     * It is only captured if a Trace Flag is active for the user.
     * 
     * @param ex The exception to log.
     * @param level The logging level to use.
     */
    public static void debugLog(Exception ex, LoggingLevel level) {
        System.debug(level, 'Message: ' + ex.getMessage());
        System.debug(level, 'Stack Trace: ' + ex.getStackTraceString());
    }
}
