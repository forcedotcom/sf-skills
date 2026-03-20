/**
 * REST endpoint for Web Applications user login.
 *
 * Endpoint: POST /services/apexrest/auth/login
 *
 * Authenticates a user and returns a redirect URL for session creation.
 *
 * @see https://developer.salesforce.com/docs/atlas.en-us.apexref.meta/apexref/apex_classes_sites.htm#apex_System_Site_login
 */
@RestResource(urlMapping='/auth/login')
global with sharing class WebAppLogin {

    /**
     * Authenticates a user and returns a redirect URL.
     * @param email User's email address (used as username).
     * @param password User's password.
     * @param startUrl Optional URL to redirect to after login.
     * @return LoginResponse with redirectUrl on success, or error message on failure.
     */
    @HttpPost
    global static LoginResponse doLogin(String email, String password, String startUrl) {
        try {
            validateInput(email, password);

            String username = email.trim().toLowerCase();
            String sanitizedStartUrl = WebAppAuthUtils.getSanitizedStartUrl(startUrl, Site.getPathPrefix());

            PageReference loginResult;
            try {
                loginResult = Site.login(username, password, sanitizedStartUrl);
            } catch (Exception loginEx) {
                RestContext.response.statusCode = 400;
                return new ErrorLoginResponse('Invalid username or password.');
            }

            if (loginResult != null) {
                return new SuccessLoginResponse(loginResult.getUrl());
            } else {
                RestContext.response.statusCode = 401;
                return new ErrorLoginResponse(
                    'Your login attempt has failed. Make sure the username and password are correct.'
                );
            }
        } catch (WebAppAuthUtils.AuthException ex) {
            RestContext.response.statusCode = ex.statusCode;
            return new ErrorLoginResponse(ex.messages);
        } catch (Exception ex) {
            WebAppAuthUtils.debugLog(ex, LoggingLevel.ERROR);
            RestContext.response.statusCode = 500;
            return new ErrorLoginResponse('An unexpected error occurred. Please contact your administrator.');
        }
    }

    /**
     * Validates login input fields.
     * @param email The email to validate.
     * @param password The password to validate.
     * @throws WebAppAuthUtils.AuthException if validation fails.
     */
    private static void validateInput(String email, String password) {
        List<String> errors = new List<String>();
        if (String.isBlank(email)) {
            errors.add('Email is required.');
        }
        if (String.isBlank(password)) {
            errors.add('Password is required.');
        }
        if (!errors.isEmpty()) {
            throw new WebAppAuthUtils.AuthException(400, errors);
        }
    }

    /**
     * Base response class for login.
     */
    global abstract class LoginResponse {
    }

    /**
     * Success response with redirect URL.
     */
    global class SuccessLoginResponse extends LoginResponse {
        global Boolean success = true;
        global String redirectUrl;

        global SuccessLoginResponse(String redirectUrl) {
            this.redirectUrl = redirectUrl;
        }
    }

    /**
     * Error response with error messages.
     */
    global class ErrorLoginResponse extends LoginResponse {
        global List<String> errors;

        global ErrorLoginResponse(List<String> errors) {
            this.errors = new List<String>(errors);
        }

        global ErrorLoginResponse(String error) {
            this.errors = new List<String>{ error };
        }
    }
}
