/**
 * REST endpoint for Web Applications for user self-registration.
 *
 * Endpoint: POST /services/apexrest/auth/register/
 *
 * Creates a new external user account, validates credentials against org password policy,
 * and returns a login URL for automatic session creation.
 *
 * Security: Uses 'without sharing' to allow guest users to check for duplicate usernames.
 */
@RestResource(urlMapping='/auth/register')
global without sharing class WebAppRegistration {

    /**
     * Registers a new external user and logs them in.
     * @param request The registration request containing user details.
     * @return SuccessResponse or ErrorResponse.
     */
    @HttpPost
    global static RegistrationResponse registerUser(RegistrationRequest request) {
        Savepoint sp = Database.setSavepoint();
        try {
            request.validate();

            User u = new User(
                Username = request.email,
                Email = request.email,
                FirstName = request.firstName,
                LastName = request.lastName,
                // Generate unique nickname: first initial + up to 20 chars of last name + 4 random digits
                CommunityNickname = request.firstName.left(1) + request.lastName.left(20) +
                    String.valueOf(Crypto.getRandomInteger()).left(4)
            );

            validatePassword(u, request.password);
            createUser(u, request.password);

            String startUrl = WebAppAuthUtils.getSanitizedStartUrl(request.startUrl, Site.getPathPrefix());
            PageReference pageRef = Site.login(request.email, request.password, startUrl);

            return new SuccessRegistrationResponse(pageRef?.getUrl());
        } catch (WebAppAuthUtils.AuthException ex) {
            Database.rollback(sp);
            RestContext.response.statusCode = ex.statusCode;
            return new ErrorRegistrationResponse(ex.messages);
        } catch (Exception ex) {
            Database.rollback(sp);
            RestContext.response.statusCode = 500;
            return new ErrorRegistrationResponse(ex.getMessage());
        }
    }

    /**
     * Base response class for registration.
     */
    global abstract class RegistrationResponse {
    }

    /**
     * Success response with redirect URL.
     */
    global class SuccessRegistrationResponse extends RegistrationResponse {
        global Boolean success = true;
        global String redirectUrl;

        global SuccessRegistrationResponse(String redirectUrl) {
            this.redirectUrl = redirectUrl;
        }
    }

    /**
     * Error response with error messages.
     */
    global class ErrorRegistrationResponse extends RegistrationResponse {
        global List<String> errors;

        global ErrorRegistrationResponse(List<String> errors) {
            this.errors = new List<String>(errors);
        }

        global ErrorRegistrationResponse(String error) {
            this.errors = new List<String>{ error };
        }
    }

    /**
     * Request payload for user registration.
     */
    global class RegistrationRequest {
        global String email;
        global String firstName;
        global String lastName;
        global String password;
        global String startUrl;

        /**
         * Trims fields and validates required fields and business rules.
         * @throws WebAppAuthUtils.AuthException if validation fails.
         */
        public void validate() {
            email = email?.trim()?.toLowerCase();
            firstName = firstName?.trim();
            lastName = lastName?.trim();
            startUrl = startUrl?.trim();

            List<String> errors = new List<String>();
            if (String.isBlank(firstName)) { errors.add('First name is required.'); }
            if (String.isBlank(lastName)) { errors.add('Last name is required.'); }
            if (String.isBlank(password)) { errors.add('Password is required.'); }
            if (!Site.isValidUserName(email)) { errors.add('Email is invalid.'); }
            else if (!isUserUnique(email)) {
                errors.add('A user with this email already exists.');
            }
            if (!errors.isEmpty()) {
                throw new WebAppAuthUtils.AuthException(400, errors);
            }
        }
    }

    /**
     * Validates password against org password policy.
     * @param user The user record.
     * @param password The password to validate.
     * @throws WebAppAuthUtils.AuthException if password does not meet requirements.
     */
    private static void validatePassword(User user, String password) {
        try {
            Site.validatePassword(user, password, password);
        } catch (System.SecurityException ex) {
            throw new WebAppAuthUtils.AuthException(400, ex.getMessage());
        }
    }

    /**
     * Creates the external user account.
     * @param u The user record.
     * @param password The password for the new user.
     * @return The new user's ID.
     * @throws WebAppAuthUtils.AuthException if user creation fails.
     */
    private static String createUser(User u, String password) {
        String userId;
        try {
            userId = Site.createExternalUser(u, null, password);
        } catch (Site.ExternalUserCreateException ex) {
            throw new WebAppAuthUtils.AuthException(500, ex.getDisplayMessages());
        }
        if (userId == null) {
            throw new WebAppAuthUtils.AuthException(500, 'Could not register new user.');
        }
        return userId;
    }

    /**
     * Checks if a username is unique (not already taken).
     * @param username The username to check.
     * @return {@code true} if unique, {@code false} if already exists.
     */
    private static Boolean isUserUnique(String username) {
        return [SELECT Id FROM User WHERE Username = :username LIMIT 1].isEmpty();
    }
}
