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
}
