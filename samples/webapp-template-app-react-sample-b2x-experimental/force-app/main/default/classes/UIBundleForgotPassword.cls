/**
 * REST endpoint for Web Applications forgot password functionality.
 *
 * Endpoint: POST /services/apexrest/auth/forgot-password
 *
 * Sends a password reset email to the user's registered email address.
 */
@RestResource(urlMapping='/auth/forgot-password')
global with sharing class UIBundleForgotPassword {

    /**
     * Initiates the forgot password process by sending a reset email.
     * @param email User's email address (used as username).
     * @return ForgotPasswordResponse with success status or error message.
     */
    @HttpPost
    global static ForgotPasswordResponse forgotPassword(String username) {
        try {
            username = username.trim().toLowerCase();

            if (String.isBlank(username)) {
                RestContext.response.statusCode = 400;
                return new ErrorForgotPasswordResponse('Username is required.');
            }
            
            // [Dev Note] This will send a password reset link to the user's email address
            // if the username exists.
            Site.forgotPassword(username);

            return new SuccessForgotPasswordResponse();
        } catch (Exception ex) {
            // Logs are only captured if a Trace Flag is active for the user
            UIBundleAuthUtils.debugLog(ex, LoggingLevel.ERROR);

            RestContext.response.statusCode = 500;
            return new ErrorForgotPasswordResponse('Could not send password reset link.');
        }
    }

    /** Base response class for forgot password operations. */
    global abstract class ForgotPasswordResponse {
    
        /** Success or failure of the forgot password operation */
        protected final Boolean success;
    }

    /** Success response for forgot password. */
    global class SuccessForgotPasswordResponse extends ForgotPasswordResponse {

        /** Constructs a success response. */
        private SuccessForgotPasswordResponse() {
            this.success = true;
        }
    }

    /** Error response for forgot password. */
    global class ErrorForgotPasswordResponse extends ForgotPasswordResponse {

        /** Error message describing the failure reason */
        private final String error;
        
        /**
         * Constructs an error response with the specified error message.
         * @param error The error message to return to the client.
         */
        private ErrorForgotPasswordResponse(String error) {
            this.success = false;
            this.error = error;
        }
    }
}
