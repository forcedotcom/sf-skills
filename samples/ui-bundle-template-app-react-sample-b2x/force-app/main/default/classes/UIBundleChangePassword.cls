/**
 * Web Applications REST endpoint for authenticated user password changes.
 * 
 * Endpoint: POST /services/apexrest/auth/change-password
 * 
 * Allows authenticated users to change their password by providing their current password
 * and a new password. The new password is validated against org password policies.
 * 
 * Security: Uses 'with sharing' to enforce user-level security. Only authenticated users
 * can change their own password.
 */
@RestResource(urlMapping='/auth/change-password')
global with sharing class UIBundleChangePassword {

    /**
     * Changes the password for the currently authenticated user.
     * 
     * @param newPassword The new password to set.
     * @param currentPassword The user's current password for verification.
     * @return SuccessPasswordChangeResponse on success, ErrorPasswordChangeResponse on failure.
     */
    @HttpPost
    global static PasswordChangeResponse changePassword(String newPassword, String currentPassword) {
        Savepoint sp = Database.setSavepoint();
        try {
            // newPassword and confirmPassword should be validated to be the same value on the client
            Site.changePassword(newPassword, newPassword, currentPassword);
            return new SuccessPasswordChangeResponse();
        } catch (Exception ex) {
            Database.rollback(sp);

            // System.SecurityException is a user error but treat others as system errors
            if (ex instanceof System.SecurityException) {
                RestContext.response.statusCode = 400;
                return new ErrorPasswordChangeResponse(ex.getMessage());
            }

            // Logs are only captured if a Trace Flag is active for the user
            UIBundleAuthUtils.debugLog(ex, LoggingLevel.ERROR);

            RestContext.response.statusCode = 500;
            return new ErrorPasswordChangeResponse('Password change failed');
        }
    }

    /** Base response class for password change operations. */
    global abstract class PasswordChangeResponse {
        
        /** Success or failure of the password change operation */
        protected final Boolean success;
    }

    /** Success response for password change. */
    global class SuccessPasswordChangeResponse extends PasswordChangeResponse {

        /** Constructs a success response. */
        private SuccessPasswordChangeResponse() {
            this.success = true;
        }
    }

    /** Error response for password change. */
    global class ErrorPasswordChangeResponse extends PasswordChangeResponse {

        /** Error message describing the failure reason */
        private final String error;
        
        /**
         * Constructs an error response with the specified error message.
         * @param error The error message to return to the client.
         */
        private ErrorPasswordChangeResponse(String error) {
            this.success = false;
            this.error = error;
        }
    }
}
