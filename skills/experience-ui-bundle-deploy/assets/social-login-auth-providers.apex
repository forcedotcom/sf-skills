/*
 * Anonymous Apex — link Auth Providers (OAuth + SAML) to a site's AuthConfig
 * by creating AuthConfigProviders junction records (idempotent, all-or-nothing).
 *
 * Ported VERBATIM from reference org-setup.mjs enableAuthProvidersForSite
 * (the generated `apex` template, lines 650-772). Apply this template as-is; do
 * NOT invent your own AuthConfigProviders Apex — DML is not allowed on
 * AuthConfigProviders, the linking must be an HTTP callout to the REST API, and
 * the all-or-nothing failure check must run BEFORE any junction is created. These
 * are easy to get wrong by hand.
 *
 * This is sub-step 2 of SKILL.md step 6b. It runs as a SINGLE `sf apex run`
 * invocation. See references/social-login.md for how to read the |DEBUG| output
 * lines this emits (AUTHCONFIG_FOUND / MISSING_PROVIDERS / INSERTED / etc.).
 *
 * Why programmatic: React (Site Container) sites hide the SSO admin UI, so
 * providers cannot be linked via Setup -> Digital Experiences -> Login &
 * Registration. AuthConfig.AuthOptionsAuthProvider auto-flips to true when the
 * junctions are inserted — no separate update needed.
 *
 * PLACEHOLDERS — substitute before running:
 *   <siteName>            = the derived site name (base name of the single
 *                          networks/<siteName>.network-meta.xml). Used in the
 *                          AuthConfig.Url LIKE match and the log header.
 *   <ProviderNamesList>   = the socialLogin.authProviderNames values as a
 *                          comma-separated Apex string-literal list, e.g.
 *                          'Google', 'My_SAML_Provider'. Each name MUST be
 *                          validated against the SOQL-name whitelist first
 *                          (reject any value containing ' \ or a control char —
 *                          same guard the permset/self-reg paths use) and then
 *                          single-quoted. This exact literal is used in BOTH the
 *                          `DeveloperName IN (...)` clauses AND the requested-name
 *                          loop below; keep them identical.
 *   <ApiVersion>         = REST API version for the callout endpoint (e.g. 62.0).
 */

// Enable Auth Providers (OAuth + SAML) for community "<siteName>"
Http http = new Http();
String baseUrl = Url.getOrgDomainUrl().toExternalForm();
String token = UserInfo.getSessionId();

// Step 1: Find the AuthConfig for this site
List<AuthConfig> authConfigs = [
    SELECT Id, Url
    FROM AuthConfig
    WHERE Url LIKE '%<siteName>%'
    LIMIT 1
];
if (authConfigs.isEmpty()) {
    System.debug('ERROR_NO_AUTHCONFIG');
    return;
}
AuthConfig ac = authConfigs[0];
System.debug('AUTHCONFIG_FOUND:' + ac.Id + ':' + ac.Url);

// Step 2: Query AuthProvider records by DeveloperName (OAuth providers)
List<AuthProvider> oauthProviders = [
    SELECT Id, DeveloperName, FriendlyName
    FROM AuthProvider
    WHERE DeveloperName IN (<ProviderNamesList>)
];
System.debug('OAUTH_PROVIDERS_FOUND:' + oauthProviders.size());

// Step 3: Query SamlSsoConfig records by DeveloperName (SAML providers)
List<SamlSsoConfig> samlProviders = [
    SELECT Id, DeveloperName
    FROM SamlSsoConfig
    WHERE DeveloperName IN (<ProviderNamesList>)
];
System.debug('SAML_PROVIDERS_FOUND:' + samlProviders.size());

// Combine both into a unified list with (Id, DeveloperName, Type)
List<Map<String, String>> allProviders = new List<Map<String, String>>();
for (AuthProvider ap : oauthProviders) {
    allProviders.add(new Map<String, String>{
        'Id' => ap.Id,
        'DeveloperName' => ap.DeveloperName,
        'Type' => 'OAuth'
    });
}
for (SamlSsoConfig sp : samlProviders) {
    allProviders.add(new Map<String, String>{
        'Id' => sp.Id,
        'DeveloperName' => sp.DeveloperName,
        'Type' => 'SAML'
    });
}

if (allProviders.isEmpty()) {
    System.debug('ERROR_NO_PROVIDERS');
    return;
}
System.debug('TOTAL_PROVIDERS_FOUND:' + allProviders.size());

// Fail fast if any requested provider name did not resolve to an AuthProvider
// (OAuth) or SamlSsoConfig (SAML) record. The isEmpty() check above only catches
// the case where NONE resolve; comparing the found DeveloperNames against the
// requested list also catches the strict-subset case (e.g. ["Google","Typo"]
// links Google but must not silently drop "Typo"). This runs BEFORE any junction
// record is created, so linking is all-or-nothing. Case-insensitive because SOQL
// "DeveloperName IN (...)" matches case-insensitively, so a stored DeveloperName
// may differ in case from the configured value and must not read as "missing".
Set<String> foundProviderNames = new Set<String>();
for (AuthProvider ap : oauthProviders) {
    foundProviderNames.add(ap.DeveloperName.toLowerCase());
}
for (SamlSsoConfig sp : samlProviders) {
    foundProviderNames.add(sp.DeveloperName.toLowerCase());
}
List<String> missingProviderNames = new List<String>();
for (String requestedName : new List<String>{<ProviderNamesList>}) {
    if (!foundProviderNames.contains(requestedName.toLowerCase())) {
        missingProviderNames.add(requestedName);
    }
}
if (!missingProviderNames.isEmpty()) {
    System.debug('MISSING_PROVIDERS:' + String.join(missingProviderNames, ','));
    return;
}

// Step 4: Check existing AuthConfigProviders to avoid duplicates
Set<Id> existingProviderIds = new Set<Id>();
for (AuthConfigProviders acp : [
    SELECT AuthProviderId FROM AuthConfigProviders WHERE AuthConfigId = :ac.Id
]) {
    existingProviderIds.add(acp.AuthProviderId);
}

// Step 5: Create missing junction records via REST API
Integer inserted = 0;
for (Map<String, String> provider : allProviders) {
    String providerId = provider.get('Id');
    String providerName = provider.get('DeveloperName');
    String providerType = provider.get('Type');

    if (existingProviderIds.contains(providerId)) {
        System.debug('ALREADY_LINKED:' + providerName + ':' + providerType);
        continue;
    }
    HttpRequest req = new HttpRequest();
    req.setEndpoint(baseUrl + '/services/data/v<ApiVersion>/sobjects/AuthConfigProviders');
    req.setMethod('POST');
    req.setHeader('Authorization', 'Bearer ' + token);
    req.setHeader('Content-Type', 'application/json');
    req.setBody('{"AuthConfigId":"' + ac.Id + '","AuthProviderId":"' + providerId + '"}');
    HttpResponse res = http.send(req);
    if (res.getStatusCode() == 201 || res.getStatusCode() == 200) {
        System.debug('INSERTED:' + providerName + ':' + providerType);
        inserted++;
    } else {
        System.debug('INSERT_FAILED:' + providerName + ':' + providerType + ':' + res.getStatusCode() + ':' + res.getBody());
    }
}
if (inserted == 0 && existingProviderIds.size() >= allProviders.size()) {
    System.debug('ALL_ALREADY_LINKED');
} else {
    System.debug('TOTAL_INSERTED:' + inserted);
}
