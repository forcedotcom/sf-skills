# iOS Refactoring Patterns: legacy MarketingCloudSDK → unified SFMCSDK (v11)

Canonical before/after shapes for each migration area on iOS. Read this before rewriting so you apply the right *shape* — especially the receiver change hidden behind the fact that the `MarketingCloudSDK` module name *survives* into v11 (as the engagement module), and the Notification Service Extension work that has no mechanical rewrite. These illustrate the transform; the authoritative symbol mappings live in `migration-matrix-ios.json` — if the two ever disagree, the matrix wins.

Every non-trivial section shows Swift AND Obj-C forms — real iOS apps mix both, and the scanner fires objcOnly / swiftOnly variants depending on the file extension.

## The v11 architecture in one paragraph

The unified iOS SDK is a set of feature modules sitting behind a unified core. **THREE eras**, not two:

1. **Legacy-pure 8.x** — `MarketingCloudSDK.sharedInstance().sfmc_configure(...)`, no `SFMCSdk` symbol.
2. **Legacy-transitional 9.x** — `SFMCSdk` façade **exists** as a wrapper over the monolithic MarketingCloudSDK: `SFMCSdk.requestPushSdk { mp in mp.sfmc_addTag(...) }`, `SFMCSdk.mp`, `SFMCSdkConfigBuilder()`, `PushConfigBuilder(appId:)`. Architecture is still monolithic under the hood.
3. **Unified v10+/v11** — the monolith is decomposed. `SFMCSdk.mp` is **REMOVED**. Engagement, push, IAM each live in their own module, each with their own `.requestSdk { ... }` async accessor.

In v11 specifically:

- Unified core (`SFMCSDK` module, pod `MarketingCloud-SFMCSdk 4.x`) owns `SFMCSdk.initializeSdk(_:)`, `SFMCSdk.identity`, `SFMCSdk.track(event:)`, `SFMCSdk.cdp`, `SFMCSdk.personalization`. It does **not** expose `.mp` / `.push` / `.iam` properties.
- Engagement module (`MarketingCloudSDK` module, pod `MarketingCloudSDK 11.x`) owns push token *storage* (behind `PushFeature`), inbox, region, tags, and analytics. The engagement class is now `MarketingCloudSdk` (**lowercase 'd'** — distinct from the module and from the legacy `MarketingCloudSDK` singleton). Reached via `MarketingCloudSdk.requestSdk { mp in ... }`.
- Push feature module (`PushFeatureSDK` module, pod `SFPushFeatureSDK 2.x`) owns push-token registration, notification response/user-info intake, and the URL handling delegate. Reached via `PushFeature.requestSdk { pf in ... }`.
- IAM module (`InAppMessagingFeatureSDK` module, pod `SFInAppMessagingFeatureSDK 1.x`) owns IAM. Reached by setting an `InAppMessageEventDelegate` via `InAppMessagingFeatureConfigBuilder().setEventDelegate(_:)` at init time, or by calling `InAppMessagingFeature`'s `setEventDelegate(_:)` after init.
- NSE / Content Extension helper (`MCExtensionSDK` module, pod `MarketingCloud-ExtensionSDK 3.x`) owns rich-media handling via **subclassing** `SFMCNotificationService` (NSE) or `SFMCNotificationViewController` (Content Extension). No `MCEExtension.handleNotificationRequest(...)` function — the integration is a subclass override, not a function call.

**Practical consequence:** every engagement call site — push token, addTag/removeTag, inbox, region — needs a **receiver change AND an async wrapper**. `[[MarketingCloudSDK sharedInstance] sfmc_addTag:@"Camping"]` becomes:

```swift
MarketingCloudSdk.requestSdk { mp in
    _ = mp?.addTag("Camping")
}
```

Note the lowercase 'd' in `MarketingCloudSdk` and the async closure — this is not a straight receiver rename. Do NOT remove the `MarketingCloudSDK` pod/package from the manifest believing it's legacy-only — that will break every push/inbox/tag/region call site because `SFMCSDK` does not provide replacements. Keep the pod, upgrade its version to 11.0.x.

**Sharp corner:** the module name `MarketingCloudSDK` (uppercase 'D') is unchanged across eras. Inside that module, however: legacy exposed the class `MarketingCloudSDK` (also uppercase 'D', reached via `.sharedInstance()`), while v11 exposes the class `MarketingCloudSdk` (**lowercase 'd'**, reached via `.requestSdk { mp in ... }`). Both classes are still declared in v11 for source-compat, but `.sharedInstance()` returns an uninitialized instance in unified — calls silently no-op. **The receiver change is load-bearing.**

## The recurring shape change: `sharedInstance` → module `requestSdk`

The legacy SDK gave you a singleton synchronously:

```swift
// Swift (legacy 8.x)
let sdk = MarketingCloudSDK.sharedInstance()
let token = sdk.sfmc_deviceToken()
```

```objc
// Obj-C (legacy)
MarketingCloudSDK *sdk = [MarketingCloudSDK sharedInstance];
NSString *token = [sdk sfmc_deviceToken];
```

In 9.x transitional, the same code plus a wrapper appeared:

```swift
// Swift (9.x transitional)
SFMCSdk.requestPushSdk { mp in
    mp.sfmc_addTag("Camping")   // mp is a MarketingCloudSDK — the monolith
}
```

In unified v11, `sharedInstance()` still exists but is stale; `SFMCSdk.mp` no longer exists at all. Access is split by module, each with its own async accessor:

```swift
// Swift (unified v11)
MarketingCloudSdk.requestSdk { mp in          // engagement — tags, inbox, region, analytics
    _ = mp?.addTag("Camping")
}

PushFeature.requestSdk { pf in                // push — device token, URL handling
    pf?.setDeviceToken(deviceToken)
}

SFMCSdk.identity.edit { identity in                  // identity — synchronous, closure-based
    identity.profileId = "user@example.com"
    return identity
}
SFMCSdk.track(event: event)                          // event tracking — synchronous
```

```objc
// Obj-C (unified v11) — bridged names
[SFMarketingCloudSdk requestSdk:^(id<SFMarketingCloudSdkInterface> _Nullable mp) {
    [mp addTag:@"Camping"];
}];

[SFPushFeature requestSdk:^(id<SFPushFeatureApi> _Nullable pf) {
    [pf setDeviceToken:deviceToken];
}];

[[SFMCSdk identity] editWithIdentity:^id<SFIdentityModifier>(id<SFIdentityModifier> identity) {
    identity.profileId = @"user@example.com";
    return identity;
}];
```

The Obj-C class names carry the `SF` prefix (`@objc(SFMarketingCloudSdk)`, `@objc(SFPushFeature)`) — Swift is `MarketingCloudSdk` / `PushFeature`, Obj-C is `SFMarketingCloudSdk` / `SFPushFeature`. Both bracket forms compile in an Obj-C file.

The subtle traps:

1. **Lowercase 'd' in `MarketingCloudSdk`.** Xcode autocomplete will happily offer `MarketingCloudSDK` (uppercase — the legacy singleton class) and compile because the methods exist on the class. That singleton returns nil / no-ops in v11. Every call site must migrate to the lowercase-'d' class name reached via `requestSdk`.
2. **The `mp` inside the closure is `MarketingCloudSdkInterface?`, not `MarketingCloudSdk`.** It's optional — the closure may be called with `nil` if the SDK isn't initialized. Guard with `mp?.` or `guard let mp = mp else { return }`.
3. **`sfmc_`-prefixed selectors are gone in v11.** So `sfmc_deviceToken()` → `deviceToken()` (still on engagement, via `requestSdk`), `sfmc_setContactKey(_:)` → identity closure `edit { identity in identity.profileId = ...; return identity }`, `sfmc_setAttributeNamed(_:value:)` → identity closure `edit { identity in identity.addAttribute(key:value:); return identity }`, `sfmc_addTag(_:)` → `addTag(_:)` (still on engagement). Rename the selector AND fix the receiver AND wrap it in the right container (`requestSdk` closure for engagement/push; `edit` closure for identity).

## Initialization

**Before** (legacy 8.x, typically in `AppDelegate.application(_:didFinishLaunchingWithOptions:)`):

```swift
// Swift (legacy 8.x) — dictionary config
let config: [String: Any] = [
    "appId": Constants.mcAppId,
    "accessToken": Constants.mcAccessToken,
    "marketingCloudServerUrl": Constants.mcServerUrl,
    "mid": Constants.mcMid,
    "inboxEnabled": true,
    "analyticsEnabled": true,
    "delayRegistrationUntilContactKeyIsSet": true
]
let success = MarketingCloudSDK.sharedInstance().sfmc_configure(with: config)
```

```objc
// Obj-C (legacy)
NSDictionary *config = @{
    @"appId": kMCAppId,
    @"accessToken": kMCAccessToken,
    @"marketingCloudServerUrl": kMCServerUrl,
    @"mid": kMCMid,
    @"inboxEnabled": @YES,
    @"analyticsEnabled": @YES
};
BOOL success = [[MarketingCloudSDK sharedInstance] sfmc_configureWithDictionary:config];
```

**After** (unified v11, typed builder pattern — module configs composed onto `ConfigBuilder()`):

```swift
// Swift (unified v11)
import SFMCSDK
import MarketingCloudSDK
import PushFeatureSDK
import InAppMessagingFeatureSDK   // only if the app uses IAM

let engagementConfig = MarketingCloudSdkConfigBuilder(appId: Constants.mcAppId)
    .setAccessToken(Constants.mcAccessToken)
    .setMarketingCloudServerUrl(Constants.mcServerUrl)
    .setMid(Constants.mcMid)
    .setInboxEnabled(true)
    .setAnalyticsEnabled(true)
    .setDelayRegistrationUntilContactKeyIsSet(true)
    .build()

let pushConfig = PushFeatureConfigBuilder()
    .setApplicationControlsBadging(true)
    // .setURLHandlingDelegate(self)   // if the app handles CTA URLs
    .build()

let iamConfig = InAppMessagingFeatureConfigBuilder()
    .setEventDelegate(self)   // AppDelegate conforming to InAppMessageEventDelegate
    .build()

let config = ConfigBuilder()
    .setEngagement(config: engagementConfig)
    .setPushFeature(config: pushConfig)
    .setInAppMessagingFeature(config: iamConfig)   // omit if app doesn't use IAM
    .build()

SFMCSdk.initializeSdk(config) { moduleStatuses in
    // Each module reports init success/failure. Log or branch; do NOT block on this.
}
```

```objc
// Obj-C (unified v11)
@import SFMCSDK;
@import MarketingCloudSDK;
@import PushFeatureSDK;

SFMarketingCloudSdkConfigBuilder *engagementBuilder =
    [[SFMarketingCloudSdkConfigBuilder alloc] initWithAppId:kMCAppId];
[engagementBuilder setAccessToken:kMCAccessToken];
[engagementBuilder setMarketingCloudServerUrl:kMCServerUrl];
[engagementBuilder setMid:kMCMid];
[engagementBuilder setInboxEnabled:YES];
[engagementBuilder setAnalyticsEnabled:YES];
[engagementBuilder setDelayRegistrationUntilContactKeyIsSet:YES];
SFMarketingCloudSdkConfig *engagementConfig = [engagementBuilder build];

SFPushFeatureConfigBuilder *pushBuilder = [SFPushFeatureConfigBuilder new];
SFPushFeatureConfig *pushConfig = [pushBuilder build];

SFMCSdkConfigBuilder *configBuilder = [SFMCSdkConfigBuilder new];
[configBuilder setEngagementWithConfig:engagementConfig];
[configBuilder setPushFeatureWithConfig:pushConfig];
[SFMCSdk initializeSdk:[configBuilder build] completion:^(NSArray *statuses) {
    // log or branch on module init statuses
}];
```

Things that will bite you if you don't already know:

- **Root builder renamed.** The v11 Swift root is `ConfigBuilder()` (in module `SFMCSDK`) — NOT `SFMCSdkConfigBuilder()`. The `SFMCSdkConfigBuilder` name exists in Obj-C (it's the Obj-C bridge name for `ConfigBuilder`, via `@objc(SFMCSdkConfigBuilder)`) but not in Swift. Migration from Swift `SFMCSdkConfigBuilder()` (era 2) → `ConfigBuilder()` (era 3) is a rename, not a keep.
- **Module setters renamed.** 9.x transitional used `.setPush(config: onCompletion:)`; v11 uses `.setEngagement(config:)` + `.setPushFeature(config:)` + `.setInAppMessagingFeature(config:)`. These are DIFFERENT methods, not aliases — a mechanical `setPush → setPushFeature` search-and-replace will drop the engagement config. Split the old push config into an engagement config + a push-feature config.
- **`PushConfigBuilder` → `MarketingCloudSdkConfigBuilder` + `PushFeatureConfigBuilder`.** In 9.x transitional the single `PushConfigBuilder(appId:)` covered everything push-related. In v11, engagement settings (appId, accessToken, serverUrl, mid, inbox/analytics enabled) move to `MarketingCloudSdkConfigBuilder(appId:)`; push-only settings (URL handling delegate, badging) move to `PushFeatureConfigBuilder()` (which has no `appId` — the engagement module owns the app identity).
- **`onCompletion` is on `initializeSdk`, not on `.setPush`.** In 9.x transitional the completion closure hung off `.setPush(config:onCompletion:)`. In v11 it's a per-module callback array returned from `SFMCSdk.initializeSdk(_:completion:)`. Callers that used the 9.x `onCompletion` for post-init work must move that work into the top-level completion.
- **`setDelayRegistrationUntilContactKeyIsSet` lives on the engagement builder.** Easy to miss because it doesn't look engagement-related.
- **`sfmc_configure` returned `Bool`; `SFMCSdk.initializeSdk` returns Void.** Legacy code that branched on the return value must be reworked.
- **Every configured feature must appear.** If the app uses IAM, `ConfigBuilder` must call `.setInAppMessagingFeature(config:)` — otherwise IAM silently never initializes despite the module being linked.

## Push / token registration

The AppDelegate glue that hands the APNs token to the SDK:

```swift
// Swift (unified v11)
import PushFeatureSDK

func application(_ application: UIApplication,
                 didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    PushFeature.requestSdk { pf in
        pf?.setDeviceToken(deviceToken)
    }
}
```

```objc
// Obj-C (unified v11)
@import PushFeatureSDK;

- (void)application:(UIApplication *)application
    didRegisterForRemoteNotificationsWithDeviceToken:(NSData *)deviceToken {
    [SFPushFeature requestSdk:^(id<SFPushFeatureApi> _Nullable pf) {
        [pf setDeviceToken:deviceToken];
    }];
}
```

Three things prior drafts of this skill got wrong:

1. **`sfmc_registerForRemoteNotifications` is not a receiver rename** — it is *removed*. Unified 10+ does not wrap `UNUserNotificationCenter`; the app owns registration. See §UNUserNotificationCenter delegate wiring below.
2. **Don't rename the AppDelegate method.** `application(_:didRegisterForRemoteNotificationsWithDeviceToken:)` is a UIApplicationDelegate contract. Only the SDK call *inside* it changes.
3. **`SFMCSdk.mp.setDeviceToken(_:)` does not exist in v11.** The push token accessor moved from the engagement module (in 9.x) to the push-feature module (in v11). Use `PushFeature.requestSdk { pf in pf?.setDeviceToken(_:) }`, not `SFMCSdk.mp.setDeviceToken(...)`.

## Identity / contact key

`SFMCSdk.identity` is synchronous but its shape **changed at v10**. Prior drafts of this doc (and 9.x transitional code) used `setProfileId(_:)` and `setProfileAttributes(_:)` directly on `identity` — those methods **do not exist** in v11. The v11 API is a single closure-based mutator:

```swift
// Swift (unified v11)
SFMCSdk.identity.edit { identity in
    identity.profileId = "user@example.com"
    identity.addAttribute(key: "firstName", value: "Ada")
    identity.addAttributes(attributes: [
        "lastName": "Lovelace",
        "segment": "Camping"
    ])
    identity.clearAttribute(key: "obsoleteKey")
    identity.clearAttributes(keys: ["k1", "k2"])
    return identity
}
```

```objc
// Obj-C (unified v11) — protocol name is SFIdentityModifier
[[SFMCSdk identity] editWithIdentity:^id<SFIdentityModifier>(id<SFIdentityModifier> identity) {
    identity.profileId = @"user@example.com";
    [identity addAttributeWithKey:@"firstName" value:@"Ada"];
    [identity addAttributesWithAttributes:@{ @"lastName": @"Lovelace" }];
    return identity;
}];
```

Sharp edges:

- **`.edit { identity in … }` is the ONLY mutator.** `SFMCSdk.identity.setProfileId(_:)`, `setProfileAttribute(_:value:)`, `setProfileAttributes(_:)`, `clearProfileAttribute(_:)`, `clearProfileAttributes(withKeys:)` are all removed. Every era-2 call site that used them must be rewritten to the closure form. The block **must return the mutated `identity`** — Swift's compiler will catch a missing return; Obj-C won't.
- **Inside the block the receiver is `IdentityModifier` (`SFIdentityModifier` in Obj-C).** Its `profileId` is `String` (non-optional in Swift, `NSString *` in Obj-C — different from the read-only `profileId` on `Identity` itself which is optional). Its attribute methods are `addAttribute(key:value:)`, `addAttributes(attributes:)`, `clearAttribute(key:)`, `clearAttributes(keys:)` — note **`key:` / `value:`** labels (not `name:` / `value:` and not `_:value:`).
- **`sfmc_setContactKey:` returned `BOOL`.** The new form returns Void. Callers that branched on the return value must be reworked — usually the branch wasn't load-bearing (it only failed if the SDK wasn't configured), but never silently drop it.
- **Attribute values are `String` on unified.** Legacy Obj-C accepted `NSNumber` / `NSDate` inside the setter's `NSDictionary`. Unified enforces `[String: String]`; numeric/date values must be stringified at the migration site.
- **The old `ModuleName.push` overload is gone.** 9.x transitional Swift code often wrote `SFMCSdk.identity.setProfileAttributes([.push: [name: value]])` to route attributes to the push module. In v11 the identity module is unified — attributes go through the closure directly, no `.push` key. The scanner flags every `[.push:` pattern for manual review because the intent may have been module-scoped and needs a human call.
- **Identity is `let`, not `var`.** `SFMCSdk.identity` is a `@objc public static let`; it's never nil, no need to guard.

Tags are **not** removed in v11 — the engagement module retains `addTag` / `removeTag`, but they're now reached inside `MarketingCloudSdk.requestSdk { mp in mp?.addTag(...) }`, not on `SFMCSdk.mp`. `mappings.add-tag` flags them for review only if the customer wants to migrate to profile attributes for the unified segmentation surface; the shortest correct rewrite keeps them via `requestSdk`.

## Event tracking

The typed Event model is the unified path:

```swift
// Swift (unified)
if let event = CustomEvent(
    name: "ProductDetail",
    attributes: ["description": "Product viewed"]
) {
    SFMCSdk.track(event: event)
}
```

```objc
// Obj-C (unified)
CustomEvent *event = [[CustomEvent alloc]
    initWithName:@"ProductDetail"
      attributes:@{ @"description": @"Product viewed" }];
if (event != nil) {
    [SFMCSdk trackWithEvent:event];
}
```

**The `if let` / nil-check is load-bearing, not stylistic.** `CustomEvent(name:attributes:)` is a *failable initializer* — it returns `nil` when the name or an attribute key fails validation, and the validation contract on iOS mirrors Android's:

- **Event names and attribute keys** are rejected if they are blank, start with `$`, or contain a line break.
- **Attribute keys only** are additionally rejected if they contain a `.` (dot).
- **Nested attributes** should be passed as a nested `[String: Any]`; the SDK flattens to dot-notation internally. A pre-flattened `"user.id"` key is dropped.

Legacy `sfmc_trackPageView(withURL:title:item:search:)` was permissive; unified is strict. **Audit any event name or attribute key built dynamically** (concatenation, string interpolation, `String(describing:)` on an enum) for dots, a leading `$`, or newlines. If a dynamic key can't be proven clean, flag for manual review.

Legacy Obj-C's `initWithName:attributes:` selector is bridged from Swift's `init?(name:attributes:)`.

## In-app messaging

IAM is a v11+ module — it does not exist in legacy 8.x/9.x. The delegate is set on the `InAppMessagingFeatureConfigBuilder` at init time (preferred), or via `InAppMessagingFeature.setEventDelegate(_:)` after init. There is **no `InAppMessagePublisher` type** in v11 — the earlier draft of this file invented one.

```swift
// Swift (unified v11)
import SFMCSDK
import InAppMessagingFeatureSDK

// At init (preferred):
let iamConfig = InAppMessagingFeatureConfigBuilder()
    .setEventDelegate(self)   // AppDelegate conforming to InAppMessageEventDelegate
    .build()

// Post-init (or to swap delegates later):
InAppMessagingFeature.shared.setEventDelegate(self)   // pass nil to clear

// Delegate protocol lives in SFMCSDK, not InAppMessagingFeatureSDK:
extension AppDelegate: InAppMessageEventDelegate {
    func shouldShow(inAppMessage message: InAppMessageDetails) -> Bool {
        return true
    }
    func didShow(inAppMessage message: InAppMessageDetails) {
        Log.iam.debug("shown: \(message.id)")
    }
    func didClose(inAppMessage message: InAppMessageDetails,
                  action: InAppMessageCloseAction) {
        Log.iam.debug("closed: \(message.id) via \(action)")
    }
}
```

```objc
// Obj-C (unified v11)
@import SFMCSDK;
@import InAppMessagingFeatureSDK;

// Delegate method signatures (protocol name in Obj-C: SFMCSdkInAppMessageEventDelegate):
- (BOOL)shouldShowWithInAppMessage:(id<SFMCSdkInAppMessageDetails>)message { return YES; }
- (void)didShowWithInAppMessage:(id<SFMCSdkInAppMessageDetails>)message { /* ... */ }
- (void)didCloseWithInAppMessage:(id<SFMCSdkInAppMessageDetails>)message
                          action:(SFMCSdkInAppMessageCloseAction *)action { /* ... */ }
```

Sharp edges:

- **The delegate protocol is `InAppMessageEventDelegate`, declared in `SFMCSDK`** (Obj-C: `SFMCSdkInAppMessageEventDelegate`). The `InAppMessagingFeatureSDK` module re-exports it. Files that only conform to the delegate don't strictly need to import `InAppMessagingFeatureSDK`, but files that call `InAppMessagingFeatureConfigBuilder` or `InAppMessagingFeature` do.
- **Message payload is `InAppMessageDetails`, not `InAppMessage`.** Prior drafts of this file used `InAppMessage`; the v11 type is `InAppMessageDetails`.
- **`didClose` signature: `didClose(inAppMessage:action:)`.** The parameter labels are `inAppMessage:` and `action:` — not `message:` and `closeAction:` as an earlier draft claimed. A one-arg override compiles but doesn't override anything and the callback never fires. Explicit `InAppMessageEventDelegate` conformance surfaces the mismatch at build time.
- **Single delegate, not a publisher.** Legacy 8.x/9.x had `sfmc_setInAppMessageDelegate:` (one slot); v11 has `setEventDelegate(_:)` on the feature module (still one slot). Migration is a straight receiver rename — there is no v11 pub-sub API.
- **Known shipping bug in v11.0.1 IAM module — verify before warning.** `SFInAppMessagingFeatureSDK 1.0.0` shipped with a swiftinterface bug (`extension InAppMessagingFeature : SFMCSDK.InAppMessagingFeatureProtocol` referencing a `:nodoc: + SWIFT_UNAVAILABLE` protocol) that prevents Xcode 26.2 / Swift 6.2.3 from loading the module. Do NOT warn unconditionally — Salesforce may have silently republished the 1.0.0 xcframework with the offending declaration removed. Run `python3 scripts/verify_known_issue.py --project <project> --issue-id iam-1.0.0-swiftinterface-nodoc` AFTER `pod install --repo-update` / `xcodebuild -resolvePackageDependencies` and gate the warning on the verdict: `reproduces` → emit the fallback (drop pod + import + `.setInAppMessagingFeature(config:)` if IAM unused; HALT if IAM used); `patched` → suppress and record the observation; `not-materialized` → run the resolver and re-verify; `inconclusive` → emit tagged unverified. See `migration-matrix-ios.json → SFInAppMessagingFeatureSDK.shippedArtifactBug.verify` and Phase 5 in SKILL.md.

## Imports & package moves

Every rewritten file needs import surgery.

**Keep** `import MarketingCloudSDK` — it's still the module of the engagement class (`MarketingCloudSdk`) and the `MarketingCloudSdkConfigBuilder`. **Add** `import SFMCSDK` (Swift) or `@import SFMCSDK;` / `#import <SFMCSDK/SFMCSDK.h>` (Obj-C) in every file that touches unified core, identity, or event tracking. **Add** `import PushFeatureSDK` in every file that touches device tokens, URL handling, or notification response intake. **Add** `import InAppMessagingFeatureSDK` in files that configure IAM (files that only conform to the delegate can import `SFMCSDK` alone).

| Legacy symbol | Unified v11 location |
| --- | --- |
| `MarketingCloudSDK.sharedInstance()` (Swift) / `[MarketingCloudSDK sharedInstance]` (Obj-C) | `MarketingCloudSdk.requestSdk { mp in ... }` (engagement) — note lowercase 'd' |
| `SFMCSdk.mp.<X>` (9.x transitional) | `MarketingCloudSdk.requestSdk { mp in mp?.<X> }` — `SFMCSdk.mp` is REMOVED in v11 |
| `SFMCSdk.requestPushSdk { mp in ... }` (9.x transitional) | Split by concern: `MarketingCloudSdk.requestSdk` for engagement, `PushFeature.requestSdk` for push token |
| `sfmc_configure(with:)` | `SFMCSdk.initializeSdk(_:completion:)` with a `ConfigBuilder()` composed from module configs |
| `sfmc_setContactKey(_:)` | `SFMCSdk.identity.edit { identity in identity.profileId = ...; return identity }` |
| `sfmc_setAttributeNamed(_:value:)` | `SFMCSdk.identity.edit { identity in identity.addAttribute(key:value:) / addAttributes(attributes:); return identity }` |
| `sfmc_clearAttributeNamed(_:)` | `SFMCSdk.identity.edit { identity in identity.clearAttribute(key:) / clearAttributes(keys:); return identity }` |
| `sfmc_addTag(_:)` / `sfmc_removeTag(_:)` | Inside `MarketingCloudSdk.requestSdk { mp in mp?.addTag(_:) / .removeTag(_:) }` — engagement retains these |
| `sfmc_setDeviceToken(_:)` | Inside `PushFeature.requestSdk { pf in pf?.setDeviceToken(_:) }` — moved from engagement to push module |
| `sfmc_deviceToken()` | Inside `MarketingCloudSdk.requestSdk { mp in mp?.deviceToken() }` — read still on engagement |
| `sfmc_registerForRemoteNotifications()` | **Removed.** App owns `UNUserNotificationCenter.current().requestAuthorization`. |
| `sfmc_setInAppMessageDelegate(_:)` | `InAppMessagingFeatureConfigBuilder().setEventDelegate(_:)` at init, or `InAppMessagingFeature.shared.setEventDelegate(_:)` after |
| `sfmc_trackPageView(withURL:title:...)` | `SFMCSdk.track(event: CustomEvent(...))` (failable init — nil-check required) |
| `sfmc_setNotificationRequest(_:)` | Inside `PushFeature.requestSdk { pf in pf?.setNotificationRequest(_:) }` (inside UNUserNotificationCenterDelegate) |
| `MCEInAppMessage` (legacy type name) | `InAppMessageDetails` (declared in `SFMCSDK`) |
| `SFMCSdkConfigBuilder()` (Swift, 9.x) | `ConfigBuilder()` (Swift, v11) — module `SFMCSDK`. In Obj-C, `SFMCSdkConfigBuilder` still bridges. |
| `.setPush(config:onCompletion:)` | `.setEngagement(config:)` + `.setPushFeature(config:)` split, plus module callback on `initializeSdk` |
| `PushConfigBuilder(appId:)` | `MarketingCloudSdkConfigBuilder(appId:)` (engagement settings) + `PushFeatureConfigBuilder()` (push-only settings) |

**Notification Service Extension** is the exception to "keep `import MarketingCloudSDK`" — see §Notification Service Extension migration below.

---

Sections below are iOS-specific — they have no direct Android analog.

## Notification Service Extension migration

The Notification Service Extension is a **separate build target**. It has its own Podfile / SPM entry, its own `Info.plist`, and its own `.entitlements`. The SDK integration inside the NSE handles rich-media (image, video, audio) downloads, notification button configuration, and — critically — hands push-receipt telemetry back to the main app so open-analytics fire.

In v11, the integration is **subclassing** `SFMCNotificationService` and overriding `sfmcProvideConfig()` — NOT calling a function.

**Before** (legacy 8.x, NSE target):

```swift
// Swift (legacy) — NSE target
import UserNotifications
import MarketingCloudSDK

class NotificationService: UNNotificationServiceExtension {
    var contentHandler: ((UNNotificationContent) -> Void)?
    var bestAttemptContent: UNMutableNotificationContent?

    override func didReceive(
        _ request: UNNotificationRequest,
        withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
    ) {
        self.contentHandler = contentHandler
        bestAttemptContent = (request.content.mutableCopy() as? UNMutableNotificationContent)
        MarketingCloudSDK.sharedInstance().sfmc_setNotificationRequest(request)
        if let content = bestAttemptContent {
            contentHandler(content)
        }
    }
}
```

**After** (unified v11, NSE target subclasses `SFMCNotificationService`):

```swift
// Swift (unified v11) — NSE target
import UserNotifications
import MCExtensionSDK           // swap import in NSE files only

class NotificationService: SFMCNotificationService {
    override func sfmcProvideConfig() -> SFMCNotificationServiceConfig {
        let config = SFMCNotificationServiceConfig()
        config.appId = "<your-app-id>"
        config.accessToken = "<your-access-token>"
        config.marketingCloudServerUrl = "<your-server-url>"
        config.appGroupIdentifier = "group.com.<your-bundle-id>"
        return config
    }
}
```

```objc
// Obj-C (unified v11) — NSE target
@import UserNotifications;
@import MCExtensionSDK;

@interface NotificationService : SFMCNotificationService
@end

@implementation NotificationService
- (SFMCNotificationServiceConfig *)sfmcProvideConfig {
    SFMCNotificationServiceConfig *config = [SFMCNotificationServiceConfig new];
    config.appId = @"<your-app-id>";
    config.accessToken = @"<your-access-token>";
    config.marketingCloudServerUrl = @"<your-server-url>";
    config.appGroupIdentifier = @"group.com.<your-bundle-id>";
    return config;
}
@end
```

**This is `manualReview: true` always.** A wrong rewrite here does not fail the build but drops push-open reporting in production — the highest-impact silent-failure mode iOS has. Four things must line up:

1. **NSE target imports `MCExtensionSDK`, not `MarketingCloudSDK`.** In the NSE file only, swap `import MarketingCloudSDK` → `import MCExtensionSDK`. The main app's other files keep `MarketingCloudSDK`.
2. **NSE target base class changes from `UNNotificationServiceExtension` to `SFMCNotificationService`.** Do NOT call the legacy `sfmc_setNotificationRequest` from `didReceive` — delete `didReceive` entirely and override `sfmcProvideConfig()` instead. `SFMCNotificationService` inherits from `UNNotificationServiceExtension` and does its own `didReceive` internally.
3. **NSE target has `MarketingCloud-ExtensionSDK` as a dependency.** In `Podfile`, add `pod 'MarketingCloud-ExtensionSDK', '~> 3.0.0'` INSIDE the `target 'YourAppNSE' do ... end` block, not the main app's block. In SPM, add `MCExtensionSDK` to the NSE target's `dependencies:`, not the main app target's.
4. **Both targets share the same App Group entitlement.** The main app and the NSE must carry `com.apple.security.application-groups` = `["group.<yourBundle>"]` in their `.entitlements`, and the App Group must be enabled in the developer portal. Without this, `SFMCNotificationService` cannot hand the push-receipt back to the main app, and open-analytics silently drop. The `appGroupIdentifier` in `sfmcProvideConfig()` must match the entitlement value exactly.

**Content Extension** is a fifth target with the same shape but a different base class: subclass `SFMCNotificationViewController` (from `MCExtensionSDK`) and override `sfmcProvideConfig()` returning `SFContentExtensionConfig`. See `migration-matrix-ios.json → MCExtensionSDK.note`.

Never mass-migrate NSE or Content Extension code. Even when the rewrite looks mechanical, verify all four lineups.

## UNUserNotificationCenter delegate wiring

Legacy 8.x/9.x auto-hooked the `UNUserNotificationCenter` delegate. Unified 10+ requires the app to set the delegate explicitly:

```swift
// Swift (unified v11) — AppDelegate.application(_:didFinishLaunchingWithOptions:)
import PushFeatureSDK

UNUserNotificationCenter.current().delegate = self

UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, error in
    guard granted, error == nil else { return }
    DispatchQueue.main.async {
        UIApplication.shared.registerForRemoteNotifications()
    }
}

// UNUserNotificationCenterDelegate methods:
extension AppDelegate: UNUserNotificationCenterDelegate {
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.list, .banner, .sound])
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        // The SDK's open-analytics need the raw request — now on the push feature module.
        PushFeature.requestSdk { pf in
            pf?.setNotificationRequest(response.notification.request)
            completionHandler()
        }
    }
}
```

**Sharp edge:** if the app *already* has its own `UNUserNotificationCenterDelegate` for local notifications, do NOT replace it. Thread the SDK call *inside* the existing delegate methods, preserving the app's own logic. An over-aggressive rewrite that swaps the entire delegate body for the `PushFeature.requestSdk` call deletes the app's local-notification handling. Flag the file for manual review whenever the delegate methods contain any code the SDK didn't put there.

## Swift `async` / completion-handler lifting

Some unified APIs that were synchronous or callback-per-argument in legacy became completion-handler or `async` in unified. Two shapes to translate:

```swift
// Legacy: fire-and-forget setter
MarketingCloudSDK.sharedInstance().sfmc_configure(with: dict)   // Bool return, blocking

// Unified v11: module-status completion at the top-level init
let config = ConfigBuilder()
    .setEngagement(config: engagementConfig)
    .setPushFeature(config: pushConfig)
    .build()

SFMCSdk.initializeSdk(config) { moduleStatuses in
    // `moduleStatuses` is [ModuleInitStatus] — one entry per configured module.
    // Post-init work goes here.
}
```

For a legacy caller that ran code *after* the sync return:

```swift
SFMCSdk.initializeSdk(config) { [weak self] _ in
    self?.startPostInitWork()
}
```

Every mapping in `migration-matrix-ios.json` with `async: true` needs this treatment. Do NOT auto-rewrite an async mapping: if the legacy code depended on synchronous ordering, the caller must be reworked, not the SDK call.

## Obj-C bridging edge cases (`@objc` visibility)

Real iOS apps often have a Swift-and-Obj-C mix. Unified SDK APIs that are Swift-only (no `@objc` annotation on the declaration in the framework's `.swiftinterface`) are **invisible** to Obj-C callers — the Obj-C code gets a link error at build time.

Common cases in v11:

- **`SFMCSdk.track(event:)`** — bridged to Obj-C as `+[SFMCSdk trackWithEvent:]`. Callable from Obj-C.
- **`MarketingCloudSdk.requestSdk`** — bridged to Obj-C as `+[SFMarketingCloudSdk requestSdk:]` (note the `SF` prefix in Obj-C). Callable from Obj-C.
- **`PushFeature.requestSdk`** — bridged as `+[SFPushFeature requestSdk:]`.
- **`ConfigBuilder`** — the Swift class `ConfigBuilder` in module `SFMCSDK` is bridged to Obj-C as `SFMCSdkConfigBuilder` (via `@objc(SFMCSdkConfigBuilder)`). Obj-C callers still write `SFMCSdkConfigBuilder`; Swift callers must switch to the v11 name `ConfigBuilder`.
- **`InAppMessagingFeatureConfigBuilder.setEventDelegate(_:)`** — depending on release, may be Swift-only. If your Obj-C file needs this, either (a) add a thin Swift shim exposed with `@objc` to the shared header, or (b) migrate the caller to Swift.

**When to flag:** any `.m` / `.h` / `.mm` file calling a unified `SFMCSdk` / `MarketingCloudSdk` / `PushFeature` method should be reviewed against the framework's actual `.swiftinterface` (find it inside the `.xcframework`, or run `xcrun swift-frontend -print-module -module-name SFMCSDK` against the compiled binary). The scanner's `objcOnly: true` matchers flag every Obj-C call site that touches these classes; that surfaces the review point.

## App Transport Security / SDK-level HTTP

Legacy SDKs used a handful of HTTP endpoints that some apps had added `NSAppTransportSecurity` / `NSExceptionDomains` entries for. Unified 10+ is HTTPS end-to-end.

**If** the app added an ATS exception for a specific SFMC hostname and NOTHING ELSE uses it, the exception can be removed. **But**: apps often add ATS exceptions for reasons that have nothing to do with SFMC (a payment gateway, an analytics vendor). Flag as manual review (`manifest.removeLegacy` marks this) — the migrator should never delete an ATS entry without a human confirming what put it there.

## Package manager version pinning: three forms in SPM

SPM's `Package.swift` supports three pin forms, and the customer's app may use any of them:

```swift
// 1. Exact
.package(url: "https://...", .exact("11.0.0"))

// 2. Range (major-bounded)
.package(url: "https://...", .upToNextMajor(from: "11.0.0"))

// 3. Branch or revision (SEMI-broken — a git branch pin dodges version resolution)
.package(url: "https://...", branch: "main")
```

The scanner reads all three shapes but the migration report must state which form was found so the human reviewer knows what to expect. An exact pin is a straight version bump; an `.upToNextMajor` pin may already resolve to the new version on the next `swift package resolve` — check `Package.resolved` to see what version is actually installed. A branch pin is a red flag: it dodges the resolver entirely, and the customer needs to move to a versioned pin before the migration is meaningful.

## Removed v9 legacy headers: inline what the caller actually uses

A few headers that older versions of `MarketingCloudSDK` (≤ 9.x) exposed were removed from v11 pods. If a customer's code was templated from an older example project, it may `#import` these headers directly; those imports become file-not-found errors on v11.

**The two we've hit in the wild:**

- `SFMCNotificationConstants.h` — vends app-level `NSNotificationName` string constants used to bridge view-controller events within an app (e.g. `SFMCIAMInsertMessageNotification`, `SFMCIAMShowMessageNotification`, `SFMCControlChannelControlChannelUpdatedNotification`). These are NSNotificationCenter channel names between an app's own view controllers — no SDK contract on their values.
- `SFMCDateNumberFormatters.h` — vends shared `+dateFormatter` and `+numberFormatter` factories (POSIX locale, UTC, ISO-8601 `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'`).

Do NOT confuse these with the v11 shipped `SFMCFoundation*` constants (e.g. `SFMCFoundationUNNotificationReceivedNotification`) exported from `MarketingCloudSDK+Constants.h` — those still exist and stay imported as before.

**The trap that makes this hard to see:** Xcode silently skips any `.m` file whose `#import` doesn't resolve. There is no CompileC line in the build log for the file — so the error surfaces as `Undefined symbols for architecture arm64: _OBJC_CLASS_$_<ClassInDroppedFile>` referenced from some *other* .m that used the class. This reads as if the .m isn't in the target's Sources build phase, which sends you editing pbxproj for no reason. Before touching pbxproj, grep the failing class's implementation file for `#import`s that don't resolve — a removed legacy header is usually the actual cause.

**Rewrite pattern — notification-name constants:**

```objc
// v9 (dropped)
#import "SFMCNotificationConstants.h"

// v11 — inline only the constants this file posts/observes.
static NSNotificationName const SFMCIAMInsertMessageNotification = @"SFMCIAMInsertMessageNotification";
static NSNotificationName const SFMCIAMShowMessageNotification = @"SFMCIAMShowMessageNotification";
```

Values must be the same literal strings the app was using pre-migration — these are the on-the-wire keys the app's own posters/observers agree on. If two files inline the same constant with different values, `NSNotificationCenter` will silently fail to deliver.

**Rewrite pattern — date formatter:**

```objc
// v9 (dropped)
#import "SFMCDateNumberFormatters.h"
NSString *iso = [[SFMCDateNumberFormatters dateFormatter] stringFromDate:[NSDate date]];

// v11 — file-local factory, dispatch_once for thread-safety.
static NSDateFormatter *ProjectPrefixIAMDateFormatter(void) {
    static NSDateFormatter *formatter;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        formatter = [[NSDateFormatter alloc] init];
        formatter.locale = [NSLocale localeWithLocaleIdentifier:@"en_US_POSIX"];
        formatter.timeZone = [NSTimeZone timeZoneForSecondsFromGMT:0];
        formatter.dateFormat = @"yyyy-MM-dd'T'HH:mm:ss.SSS'Z'";
    });
    return formatter;
}
```

If the formatted string is ever compared server-side (message-envelope `modifiedDateUtc`, analytics timestamps, etc.), verify the format-string against the customer's v9 checkout — a subtle drift in fractional-second precision or timezone marker silently changes payloads that dashboards parse.

## Removed enums that never lived on the SDK: `AuthEventType`

v9 shipped `NS_ENUM(NSInteger, AuthEventType)` in `SFMCEvent.h` under MarketingCloudSDK, wired to a shortcut selector `sfmc_trackAuthenticationEvent(...)`. In v11 both the enum and the shortcut are gone — authentication events collapse into the generic `CustomEvent(name:attributes:)` pipeline reached through `SFMCSdk.track(event:)`.

Rewrite by declaring a *local* Swift enum in the calling file with the cases the app was previously using, then constructing a `CustomEvent`:

```swift
// v11 — file-local enum + generic CustomEvent
enum AuthEvent: String, CaseIterable {
    case Login
    // add other cases the app previously exercised
}

let row = picker.selectedRow(inComponent: 0)
guard AuthEvent.allCases.indices.contains(row),
      let event = CustomEvent(name: "AuthenticationEvent",
                              attributes: ["AuthEventType": AuthEvent.allCases[row].rawValue]) else {
    return
}
SFMCSdk.track(event: event)
```

`CustomEvent(name:attributes:)` is failable — v11 rejects invalid names/keys (blank, leading `$`, dots, newlines) where the v9 selector silently accepted them. `if let` / `guard let`; never force-unwrap.

If the marketing team relied on the legacy `sfmc_trackAuthenticationEvent` event name landing in a specific dashboard, coordinate the new `CustomEvent` name with them — the string used above (`"AuthenticationEvent"`) is a sensible default but the dashboard query may need updating.

## What to always flag, never auto-rewrite

- **Notification Service Extension code** — always manual review, regardless of how mechanical the rewrite looks.
- **Notification Content Extension code** — separate target with its own base class (`SFMCNotificationViewController`); same manual-review rule.
- **`UNUserNotificationCenterDelegate` methods that contain non-SDK code.** Preserve the app's own local-notification handling.
- **`sfmc_registerForRemoteNotifications` call sites** — the removal means the app must own registration, and the *when* (during onboarding, after login, on demand) is a UX decision.
- **Subclasses or protocol conformances of legacy SDK types** — no mechanical rewrite.
- **Obj-C call sites of Swift-only unified APIs** — need a Swift shim or a caller migration.
- **`NSAppTransportSecurity` exceptions** — may be for non-SFMC reasons; never auto-delete.
- **Tag handling** (`sfmc_addTag` / `sfmc_removeTag`) — tags still work on the engagement module reached via `MarketingCloudSdk.requestSdk`; only move to profile attributes if the marketing team chose to.
- **Any symbol with no matrix entry.**
- **SPM branch pins** — a branch pin (as opposed to `.exact` or `.upToNextMajor`) means the resolver isn't in play. Flag and ask the customer to move to a versioned pin.
- **Deployment target below iOS 12** — v10+ requires iOS 12; a project on a lower target needs a business call before the migration can proceed.
