/**
 * Test class for UIBundleSocialLoginConfig REST endpoint.
 *
 * Auth.AuthConfiguration requires a valid community URL so these tests
 * exercise the error-handling path and verify the response wrapper structure.
 * Integration-level testing of actual Auth Provider/SAML discovery happens
 * in the target org via the React component E2E flow.
 */
@isTest
private class UIBundleSocialLoginConfig_Test {

    /**
     * Test that the endpoint returns an empty config when no community context
     * is available (covers the catch block graceful fallback).
     */
    @isTest
    static void testGetConfigNoSiteContext() {
        RestRequest req = new RestRequest();
        req.requestURI = '/services/apexrest/auth/social-login-config';
        req.httpMethod = 'GET';
        req.params.put('startURL', '/');
        RestContext.request = req;
        RestContext.response = new RestResponse();

        Test.startTest();
        UIBundleSocialLoginConfig.SocialLoginConfigResponse result =
            UIBundleSocialLoginConfig.getConfig();
        Test.stopTest();

        // Should return empty lists (graceful fallback), not null
        System.assertNotEquals(null, result, 'Response should not be null');
        System.assertNotEquals(null, result.authProviders, 'authProviders list should not be null');
        System.assertNotEquals(null, result.samlProviders, 'samlProviders list should not be null');
        System.assertEquals(0, result.authProviders.size(), 'authProviders should be empty without community context');
        System.assertEquals(0, result.samlProviders.size(), 'samlProviders should be empty without community context');
        System.assertEquals(null, result.autoRedirectUrl, 'autoRedirectUrl should be null without providers');
    }

    /**
     * Test that the endpoint handles a missing startURL parameter gracefully
     * (defaults to "/").
     */
    @isTest
    static void testGetConfigNoStartUrl() {
        RestRequest req = new RestRequest();
        req.requestURI = '/services/apexrest/auth/social-login-config';
        req.httpMethod = 'GET';
        // Intentionally not setting startURL param
        RestContext.request = req;
        RestContext.response = new RestResponse();

        Test.startTest();
        UIBundleSocialLoginConfig.SocialLoginConfigResponse result =
            UIBundleSocialLoginConfig.getConfig();
        Test.stopTest();

        System.assertNotEquals(null, result, 'Response should not be null even without startURL');
        System.assertNotEquals(null, result.authProviders, 'authProviders should not be null');
        System.assertNotEquals(null, result.samlProviders, 'samlProviders should not be null');
    }

    /**
     * Test the inner class constructors for code coverage.
     */
    @isTest
    static void testInnerClassConstructors() {
        Test.startTest();

        UIBundleSocialLoginConfig.AuthProviderInfo authInfo =
            new UIBundleSocialLoginConfig.AuthProviderInfo(
                'TestProvider', 'Test Provider', 'https://example.com/icon.png', 'https://example.com/sso'
            );
        System.assertEquals('TestProvider', authInfo.developerName);
        System.assertEquals('Test Provider', authInfo.friendlyName);
        System.assertEquals('https://example.com/icon.png', authInfo.iconUrl);
        System.assertEquals('https://example.com/sso', authInfo.ssoUrl);

        UIBundleSocialLoginConfig.SamlProviderInfo samlInfo =
            new UIBundleSocialLoginConfig.SamlProviderInfo(
                '001000000000001', 'Test SAML', 'https://example.com/saml/sso'
            );
        System.assertEquals('001000000000001', samlInfo.id);
        System.assertEquals('Test SAML', samlInfo.masterLabel);
        System.assertEquals('https://example.com/saml/sso', samlInfo.ssoUrl);

        List<UIBundleSocialLoginConfig.AuthProviderInfo> authList =
            new List<UIBundleSocialLoginConfig.AuthProviderInfo>{ authInfo };
        List<UIBundleSocialLoginConfig.SamlProviderInfo> samlList =
            new List<UIBundleSocialLoginConfig.SamlProviderInfo>{ samlInfo };

        UIBundleSocialLoginConfig.SocialLoginConfigResponse resp =
            new UIBundleSocialLoginConfig.SocialLoginConfigResponse(
                authList, samlList, 'https://example.com/redirect'
            );
        System.assertEquals(1, resp.authProviders.size());
        System.assertEquals(1, resp.samlProviders.size());
        System.assertEquals('https://example.com/redirect', resp.autoRedirectUrl);

        Test.stopTest();
    }

    // ---- Open-redirect sanitization (CWE-601) -------------------------------
    // resolveStartUrl() is the boundary where the endpoint sanitizes the
    // caller-supplied startURL before it is embedded in the SSO redirect URL.
    // These tests assert malicious values never survive that boundary and that
    // legitimate relative paths do.

    @isTest
    static void resolveStartUrlRejectsAbsoluteUrl() {
        assertNotReflected('https://evil-attacker.com');
    }

    @isTest
    static void resolveStartUrlRejectsProtocolRelativeUrl() {
        assertNotReflected('//evil-attacker.com');
    }

    @isTest
    static void resolveStartUrlRejectsBackslashVariant() {
        assertNotReflected('/\\evil-attacker.com');
    }

    @isTest
    static void resolveStartUrlRejectsEncodedBypass() {
        assertNotReflected('%2f%2fevil-attacker.com');
    }

    @isTest
    static void resolveStartUrlAllowsRelativePath() {
        setRequest('/dashboard');
        String resolved = UIBundleSocialLoginConfig.resolveStartUrl();
        System.assertNotEquals(null, resolved, 'A valid relative path should resolve to a non-null value');
        System.assert(
            resolved.endsWith('/dashboard'),
            'A valid relative path must be preserved (optionally prefixed): ' + resolved
        );
        System.assert(!resolved.startsWith('http'), 'Result must not be absolute: ' + resolved);
    }

    @isTest
    static void getConfigWithMaliciousStartUrlReturnsGracefulEmpty() {
        // End-to-end: a malicious startURL must not crash the endpoint; without
        // a real site context it returns the graceful empty response (unchanged).
        setRequest('https://evil-attacker.com');

        Test.startTest();
        UIBundleSocialLoginConfig.SocialLoginConfigResponse result =
            UIBundleSocialLoginConfig.getConfig();
        Test.stopTest();

        System.assertNotEquals(null, result, 'Response should not be null');
        System.assertEquals(0, result.authProviders.size(), 'No providers without site context');
        System.assertEquals(0, result.samlProviders.size(), 'No SAML providers without site context');
        System.assertEquals(null, result.autoRedirectUrl, 'No auto-redirect without providers');
    }

    // ---- helpers ------------------------------------------------------------

    /** Asserts a malicious startURL value is not reflected by resolveStartUrl(). */
    private static void assertNotReflected(String maliciousStartUrl) {
        setRequest(maliciousStartUrl);
        String resolved = UIBundleSocialLoginConfig.resolveStartUrl();
        String safe = resolved == null ? '' : resolved;
        System.assert(!safe.contains('evil-attacker'), 'Malicious host must not be reflected: ' + safe);
        System.assert(!safe.startsWith('http'), 'Result must not be an absolute URL: ' + safe);
        System.assert(!safe.startsWith('//'), 'Result must not be protocol-relative: ' + safe);
        System.assert(!safe.contains('\\'), 'Result must not contain a backslash: ' + safe);
    }

    /** Builds a GET RestContext with the given startURL param (null => param omitted). */
    private static void setRequest(String startUrlValue) {
        RestRequest req = new RestRequest();
        req.requestURI = '/services/apexrest/auth/social-login-config';
        req.httpMethod = 'GET';
        if (startUrlValue != null) {
            req.params.put('startURL', startUrlValue);
        }
        RestContext.request = req;
        RestContext.response = new RestResponse();
    }
}
