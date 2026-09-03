/**
 * Test class for UIBundleAuthUtils.
 *
 * Focuses on getSanitizedStartUrl, the shared open-redirect (CWE-601) guard
 * used by UIBundleLogin, UIBundleRegistration and UIBundleSocialLoginConfig.
 * Every rejection path and the safe-path prefixing
 * behavior are asserted deterministically with an explicit path prefix.
 */
@isTest
private class UIBundleAuthUtils_Test {

    // Explicit, non-null community path prefix so behavior is deterministic
    // (Site.getPathPrefix() is null/blank in a plain unit-test context).
    private static final String PREFIX = '/community';

    // ---- Safe / allowed inputs ----------------------------------------------

    @isTest
    static void allowsSafeRelativePath() {
        System.assertEquals(
            '/community/dashboard',
            UIBundleAuthUtils.getSanitizedStartUrl('/dashboard', PREFIX),
            'A safe community-relative path should be prefixed and preserved'
        );
    }

    @isTest
    static void allowsNestedRelativePath() {
        System.assertEquals(
            '/community/safe/relative/path',
            UIBundleAuthUtils.getSanitizedStartUrl('/safe/relative/path', PREFIX),
            'A nested relative path should be prefixed and preserved'
        );
    }

    @isTest
    static void blankAndRootFallBackToDefault() {
        System.assertEquals(PREFIX, UIBundleAuthUtils.getSanitizedStartUrl(null, PREFIX), 'null -> default');
        System.assertEquals(PREFIX, UIBundleAuthUtils.getSanitizedStartUrl('', PREFIX), 'empty -> default');
        System.assertEquals(PREFIX, UIBundleAuthUtils.getSanitizedStartUrl('   ', PREFIX), 'whitespace -> default');
        System.assertEquals(PREFIX, UIBundleAuthUtils.getSanitizedStartUrl('/', PREFIX), '"/" -> default');
    }

    // ---- Rejected / malicious inputs (all fall back to the default) ----------

    @isTest
    static void rejectsAbsoluteHttpUrl() {
        System.assertEquals(
            PREFIX,
            UIBundleAuthUtils.getSanitizedStartUrl('https://evil-attacker.com', PREFIX),
            'Absolute http(s) URL must be rejected'
        );
    }

    @isTest
    static void rejectsProtocolRelativeUrl() {
        System.assertEquals(
            PREFIX,
            UIBundleAuthUtils.getSanitizedStartUrl('//evil-attacker.com', PREFIX),
            'Protocol-relative URL must be rejected'
        );
    }

    @isTest
    static void rejectsAmbiguousScheme() {
        System.assertEquals(
            PREFIX,
            UIBundleAuthUtils.getSanitizedStartUrl('https:evil-attacker.com', PREFIX),
            'Malformed/ambiguous scheme must be rejected'
        );
    }

    @isTest
    static void rejectsBackslashVariant() {
        System.assertEquals(
            PREFIX,
            UIBundleAuthUtils.getSanitizedStartUrl('/\\evil-attacker.com', PREFIX),
            'Backslash normalization trick must be rejected'
        );
    }

    @isTest
    static void rejectsAtSign() {
        System.assertEquals(
            PREFIX,
            UIBundleAuthUtils.getSanitizedStartUrl('/x@evil-attacker.com', PREFIX),
            'User-info "@" must be rejected'
        );
    }

    @isTest
    static void rejectsColon() {
        System.assertEquals(
            PREFIX,
            UIBundleAuthUtils.getSanitizedStartUrl('/path:8080', PREFIX),
            'Colon (port/scheme manipulation) must be rejected'
        );
    }

    @isTest
    static void rejectsEncodedProtocolRelativeBypass() {
        // %2f%2f decodes to // — the decode step must catch this.
        System.assertEquals(
            PREFIX,
            UIBundleAuthUtils.getSanitizedStartUrl('%2f%2fevil-attacker.com', PREFIX),
            'URL-encoded protocol-relative bypass must be rejected'
        );
    }

    @isTest
    static void rejectsControlCharacters() {
        String withNewline = '/foo' + String.fromCharArray(new List<Integer>{ 10 }) + 'bar';
        System.assertEquals(
            PREFIX,
            UIBundleAuthUtils.getSanitizedStartUrl(withNewline, PREFIX),
            'Embedded control characters must be rejected'
        );
    }

    // ---- Supporting API coverage --------------------------------------------

    @isTest
    static void authExceptionCarriesStatusAndMessages() {
        UIBundleAuthUtils.AuthException single = new UIBundleAuthUtils.AuthException(400, 'bad request');
        System.assertEquals(400, single.statusCode, 'statusCode should round-trip');
        System.assertEquals(1, single.messages.size(), 'single-message constructor');

        UIBundleAuthUtils.AuthException multi =
            new UIBundleAuthUtils.AuthException(500, new List<String>{ 'a', 'b' });
        System.assertEquals(500, multi.statusCode, 'statusCode should round-trip');
        System.assertEquals(2, multi.messages.size(), 'multi-message constructor');
    }

    @isTest
    static void debugLogCompletesWithoutError() {
        Test.startTest();
        UIBundleAuthUtils.debugLog(new IllegalArgumentException('boom'), LoggingLevel.ERROR);
        Test.stopTest();
        System.assert(true, 'debugLog should complete without throwing');
    }
}
