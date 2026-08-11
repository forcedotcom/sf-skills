/**
 * REST endpoint for Social Login configuration on React Experience Cloud sites.
 *
 * Endpoint: GET /services/apexrest/auth/social-login-config?startURL=/
 *
 * This replicates the behavior of the OOTB community_login/socialLogin LWC:
 *   - applauncher.SocialLoginController.getAuthProviders()
 *   - applauncher.SocialLoginController.getSamlProviders()
 *   - applauncher.SocialLoginController.getCommunityDomainSsoUrl()
 *   - applauncher.SocialLoginController.getSamlSsoUrl()
 *   - applauncher.SocialLoginController.handleIdp()
 *
 * The OOTB LWC does not render on React (Site Container) sites due to a platform
 * restriction (isSiteContainer check in node-loginsettings.ftl).
 * This endpoint enables a custom React component to achieve the same functionality.
 *
 * @see https://developer.salesforce.com/docs/atlas.en-us.apexref.meta/apexref/apex_class_Auth_AuthConfiguration.htm
 */
@RestResource(urlMapping='/auth/social-login-config')
global with sharing class UIBundleSocialLoginConfig {

    @HttpGet
    global static SocialLoginConfigResponse getConfig() {
        try {
            String startUrl = RestContext.request.params.get('startURL');
            if (String.isBlank(startUrl)) {
                startUrl = '/';
            }

            // Ensure startURL includes the community path prefix so post-auth
            // redirect lands on the correct community (not the org default).
            String pathPrefix = Site.getPathPrefix();
            if (String.isNotBlank(pathPrefix) && !startUrl.startsWith(pathPrefix)) {
                startUrl = pathPrefix + startUrl;
            }

            String communityUrl = Site.getBaseUrl();
            Auth.AuthConfiguration authConfig = new Auth.AuthConfiguration(communityUrl, startUrl);

            List<AuthProviderInfo> authProviders = new List<AuthProviderInfo>();
            List<SamlProviderInfo> samlProviders = new List<SamlProviderInfo>();
            String autoRedirectUrl = null;

            // Fetch OAuth Auth Providers (Google, Facebook, etc.)
            List<AuthProvider> rawAuthProviders = authConfig.getAuthProviders();
            for (AuthProvider ap : rawAuthProviders) {
                String ssoUrl = Auth.AuthConfiguration.getAuthProviderSsoDomainUrl(
                    communityUrl, startUrl, ap.DeveloperName
                );
                authProviders.add(new AuthProviderInfo(
                    ap.DeveloperName,
                    ap.FriendlyName,
                    ap.IconUrl,
                    ssoUrl
                ));
            }

            // Fetch SAML SSO Providers
            List<SamlSsoConfig> rawSamlProviders = authConfig.getSamlProviders();
            for (SamlSsoConfig saml : rawSamlProviders) {
                String ssoUrl = Auth.AuthConfiguration.getSamlSsoUrl(
                    communityUrl, startUrl, saml.Id
                );
                samlProviders.add(new SamlProviderInfo(
                    saml.Id,
                    saml.MasterLabel,
                    ssoUrl
                ));
            }

            // handleIdp behavior: auto-redirect if exactly one IDP and no username/password login
            Integer totalProviders = rawAuthProviders.size() + rawSamlProviders.size();
            if (totalProviders == 1 && !authConfig.getUsernamePasswordEnabled()) {
                if (!authProviders.isEmpty()) {
                    autoRedirectUrl = authProviders[0].ssoUrl;
                } else if (!samlProviders.isEmpty()) {
                    autoRedirectUrl = samlProviders[0].ssoUrl;
                }
            }

            return new SocialLoginConfigResponse(authProviders, samlProviders, autoRedirectUrl);
        } catch (Exception ex) {
            System.debug(LoggingLevel.ERROR, 'UIBundleSocialLoginConfig error: ' + ex.getMessage());
            return new SocialLoginConfigResponse(
                new List<AuthProviderInfo>(),
                new List<SamlProviderInfo>(),
                null
            );
        }
    }

    global class SocialLoginConfigResponse {
        global List<AuthProviderInfo> authProviders;
        global List<SamlProviderInfo> samlProviders;
        global String autoRedirectUrl;

        global SocialLoginConfigResponse(
            List<AuthProviderInfo> authProviders,
            List<SamlProviderInfo> samlProviders,
            String autoRedirectUrl
        ) {
            this.authProviders = authProviders;
            this.samlProviders = samlProviders;
            this.autoRedirectUrl = autoRedirectUrl;
        }
    }

    global class AuthProviderInfo {
        global String developerName;
        global String friendlyName;
        global String iconUrl;
        global String ssoUrl;

        global AuthProviderInfo(String developerName, String friendlyName, String iconUrl, String ssoUrl) {
            this.developerName = developerName;
            this.friendlyName = friendlyName;
            this.iconUrl = iconUrl;
            this.ssoUrl = ssoUrl;
        }
    }

    global class SamlProviderInfo {
        global String id;
        global String masterLabel;
        global String ssoUrl;

        global SamlProviderInfo(String id, String masterLabel, String ssoUrl) {
            this.id = id;
            this.masterLabel = masterLabel;
            this.ssoUrl = ssoUrl;
        }
    }
}
