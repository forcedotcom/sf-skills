# Android Refactoring Patterns: legacy MarketingCloudSdk → unified SFMCSdk (v11)

Canonical before/after shapes for each migration area. Read this before rewriting so you apply the right *shape* — especially the async-callback wrapping, which is the single most common way a naive rename breaks the build. These illustrate the transform; the authoritative symbol mappings (and any version-specific caveats) live in `migration-matrix-android.json`.

## The v11 architecture in one paragraph

The unified SDK is **not** "sfmcsdk replaces marketingcloudsdk." It's a set of feature modules sitting behind a unified core. The unified core (`sfmcsdk:3.1.1`) owns `SFMCSdk.configure` / `SFMCSdk.requestSdk` / identity / events. The **engagement module** — still published as `marketingcloudsdk`, at version `11.0.1` — retains `MarketingCloudSdk`, `RegistrationManager`, `InboxMessageManager`, `AnalyticsManager`, `RegionMessageManager`, `sdkState`. The push module (`pushfeaturemodule:2.0.1`) owns `PushFeature` / `PushMessageManager` / notification classes. The IAM module (`inappmessagingfeaturemodule:1.0.1`) owns `InAppMessagingFeature` and the `InAppMessage` model.

**Practical consequence:** most engagement call sites (`sdk.analyticsManager.enableAnalytics()`, `sdk.inboxMessageManager.registerInboxResponseListener(...)`, `sdk.regionMessageManager.enableGeofenceMessaging()`, `sdk.sdkState.optJSONObject(...)`, `sdk.registrationManager.edit().addTag(...).commit()`) require **no rewrite at all** in v11 — the symbols still exist on the engagement module. The only shape change is that access is via `MarketingCloudSdk.requestSdk { sdk -> ... }` instead of the synchronous `MarketingCloudSdk.getInstance()`. This is a common source of over-migration: a prior pass at this skill removed `marketingcloudsdk` from Gradle believing it was legacy-only, which broke every Inbox/Region/Analytics call site with no replacement to point at. Don't repeat that.

## The recurring shape change: synchronous getInstance → async requestSdk

The legacy SDK gave you a singleton synchronously:

```java
MarketingCloudSdk sdk = MarketingCloudSdk.getInstance();   // available "now"
```

The unified SDK initializes asynchronously, so you ask for it via a callback. **There are FOUR entry points**, each rooted in a different module — pick the right one based on which manager you're reaching:

```kotlin
// Engagement APIs: RegistrationManager, InboxMessageManager, AnalyticsManager,
// RegionMessageManager, sdkState. Receiver is still MarketingCloudSdk.
MarketingCloudSdk.requestSdk { sdk -> /* engagement work */ }

// Unified core APIs: identity (setProfileId / attributes), Event tracking.
SFMCSdk.requestSdk { unifiedSdk -> /* identity / events */ }

// Push APIs: setPushToken, handleMessage, notification manager.
PushFeature.requestSdk { pushFeature -> /* push work */ }

// IAM APIs: the InAppMessage manager (rarely needed — most IAM config happens
// at init via InAppMessagingFeatureConfig).
InAppMessagingFeature.requestSdk { iamFeature -> /* iam work */ }
```

Prior drafts of this skill invented `SFMCSdk.requestSdk { sdk -> sdk.mp { it.pushMessageManager... } }` as a way to reach push. **That `.mp { }` block does not exist in the published v11 artifacts.** It came from an unpublished/internal API draft. Do not emit it. Use `PushFeature.requestSdk` for push.

Batch related work into one `requestSdk` block rather than opening a new callback per statement.

## Initialization

**Before** (legacy, typically in `Application.onCreate`):
```kotlin
MarketingCloudSdk.init(this,
    MarketingCloudConfig.builder()
        .setApplicationId(BuildConfig.MC_APP_ID)
        .setAccessToken(BuildConfig.MC_ACCESS_TOKEN)
        .setSenderId(BuildConfig.FCM_SENDER_ID)
        .setMarketingCloudServerUrl(BuildConfig.MC_SERVER_URL)
        .setMid(BuildConfig.MC_MID)
        .setInboxEnabled(true)
        .setAnalyticsEnabled(true)
        .setGeofencingEnabled(true)
        .setUrlHandler(this)
        .setNotificationCustomizationOptions(
            NotificationCustomizationOptions.create(R.drawable.ic_notification))
        .build(this)
) { initStatus ->
    if (initStatus.isUsable) { /* ... */ }
}
```

**After** (unified, v11):
```kotlin
SFMCSdk.configure(applicationContext as Application, SFMCSdkModuleConfig.build {
    // ENGAGEMENT — keeps the legacy MarketingCloudConfig.Builder;
    // most setters (mid, analytics, PI, inbox, geofencing, proximity, urlHandler) survive here.
    engagementModuleConfig = MarketingCloudConfig.Builder()
        .setApplicationId(BuildConfig.MC_APP_ID)
        .setAccessToken(BuildConfig.MC_ACCESS_TOKEN)
        .setMarketingCloudServerUrl(BuildConfig.MC_SERVER_URL)
        .setMid(BuildConfig.MC_MID)
        .setAnalyticsEnabled(true)
        .setPiAnalyticsEnabled(true)
        .setInboxEnabled(true)
        .setGeofencingEnabled(true)
        .setProximityEnabled(true)
        .setUrlHandler(this@BaseLearningApplication)
        .build(this)

    // PUSH — separate config. In legacy SDK, setSenderId was a public setter on
    // MarketingCloudConfig.Builder; in v11 it is private there (@suppress), and the sender id
    // now belongs on PushFeatureConfig. So a legacy .setSenderId(...) call must be MIGRATED
    // into this block, not simply deleted.
    // PushFeatureConfig.builder() is a static factory; the Builder constructor is internal
    // (PushFeatureConfig.Builder() would compile-error).
    pushFeatureModuleConfig = PushFeatureConfig.builder()
        .setSenderId(BuildConfig.FCM_SENDER_ID)
        .setNotificationCustomizationOptions(
            NotificationCustomizationOptions.create(R.drawable.ic_notification))
        .setUrlHandler(this@BaseLearningApplication)
        .build()

    // IAM — only when the scan reports iam in featuresInUse.
    // Same story: InAppMessagingFeatureConfig.builder() is a static factory; its Builder
    // constructor is internal (InAppMessagingFeatureConfig.Builder() will not compile).
    // On the CONFIG BUILDER, setTypeface(typeface: Typeface) is NON-NULL, and
    // ResourcesCompat.getFont returns Typeface? — so the ?.let(::setTypeface) guard is required
    // here. (The runtime InAppMessageManager.setTypeface(typeface: Typeface?) DOES accept null,
    // so the guard is not load-bearing there — but init config is the common case.)
    inAppMessagingFeatureModuleConfig = InAppMessagingFeatureConfig.builder()
        .setEventListener(inAppMessageListener)
        .apply {
            ResourcesCompat.getFont(this@BaseLearningApplication, R.font.brand)
                ?.let(::setTypeface)
        }
        .setStatusBarColor(
            ContextCompat.getColor(this@BaseLearningApplication, R.color.primary))
        .build()
}) { initStatus -> /* same status handling */ }
```

Things that will bite you if you don't already know:

- **Slot names on `SFMCSdkModuleConfig.build {}`** are `engagementModuleConfig`, `pushFeatureModuleConfig`, `inAppMessagingFeatureModuleConfig`, `cdpModuleConfig`, `mamModuleConfig`, `personalizationModuleConfig`. Names like `pushModuleConfig` or `inAppMessagingModuleConfig` (dropping the `Feature`) do **not** exist in the v11 artifacts. Prior drafts of this skill used those short names and produced code that didn't compile.
- **`MarketingCloudConfig.Builder`** still exposes `setMid`, `setInboxEnabled`, `setAnalyticsEnabled`, `setPiAnalyticsEnabled`, `setGeofencingEnabled`, `setProximityEnabled`, `setUrlHandler`, `setApplicationId`, `setAccessToken`, `setMarketingCloudServerUrl`. Do **not** drop them in the migration — the customer's feature flags need to keep flowing. The **only** setter that moved is `setSenderId`: it is now `private` (`@suppress`) on `MarketingCloudConfig.Builder` and lives on `PushFeatureConfig.builder().setSenderId(...)`. Move the legacy call there — don't just delete it, or the app loses its FCM sender id and push registration breaks.
- **`PushFeatureConfig` and `InAppMessagingFeatureConfig`** are Java-style: call the static `.builder()` factory. Trying `PushFeatureConfig.Builder()` or `InAppMessagingFeatureConfig.Builder()` fails — those constructors are `internal`.
- **The IAM `EventListener` interface grew a parameter.** `didCloseMessage(message: InAppMessage)` is now `didCloseMessage(message: InAppMessage, closeAction: InAppMessageCloseAction)`. A one-arg override compiles but doesn't actually override — you'll get "overrides nothing" or the listener will silently never fire. Add the second param and import `com.salesforce.marketingcloud.inappmessagingfeature.InAppMessageCloseAction`.
- **Init config must cover every feature the scan reported.** `SFMCSdkModuleConfig` is additive — if `iam` is in `featuresInUse`, `inAppMessagingFeatureModuleConfig` **must** be wired here, or IAM silently never initializes despite the artifact being on the classpath.

## Push / token registration

```kotlin
import com.salesforce.marketingcloud.pushfeature.PushFeature
import com.salesforce.marketingcloud.pushfeature.push.PushMessageManager  // <-- new package

class MyFcmMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        if (PushMessageManager.isMarketingCloudPush(message)) {          // static, unchanged
            PushFeature.requestSdk { pushFeature ->
                pushFeature.getPushMessageManager().handleMessage(message)
            }
        }
    }

    override fun onNewToken(token: String) {
        PushFeature.requestSdk { pushFeature ->
            pushFeature.getPushMessageManager().setPushToken(token)
        }
    }
}
```

Two things prior drafts got wrong:

1. **Entry point** is `PushFeature.requestSdk`, not `SFMCSdk.requestSdk { sdk.mp { ... } }`. There is no `mp` receiver in the published v11 push module.
2. **Accessor name**: use `getPushMessageManager()`, not the property form `pushMessageManager`. Kotlin does not synthesize a property for this getter in `pushfeaturemodule:2.0.1` — the property-style access fails to resolve. This is a Kotlin-metadata quirk; the JVM class exposes only the Java-style getter.

## Identity / contact key

```kotlin
SFMCSdk.requestSdk { unifiedSdk ->
    unifiedSdk.identity.edit {
        profileId = "user@example.com"       // property, not setProfileId(...)
        attributes.set("firstName", "Ada")   // attributes.set / .put / .clear
    }
}
```

The `Identity.edit` lambda has an **extension receiver** type `IdentityEditor.() -> Unit`. That means:

- **Do NOT** name an explicit parameter: `identity.edit { editor -> editor.profileId = ... }` compiles to a `Function2` and fails with `"Function2 expected, Function1 found"`. Just assign on the implicit receiver.
- **Property access, not setters**: `IdentityEditor` exposes `profileId` as a **var** (assign with `=`), not a `setProfileId(...)` method. Attributes are on `IdentityEditor.attributes` (an `AttributesEditor`), which exposes `set(k, v)`, `put(k, v)`, `set(map)`, `putAll(map)`, `clear(key)`, `clearAll()`. Prior drafts of this skill emitted `setProfileId(...)` and `putAttribute(...)` directly on the SDK — those symbols do not exist.
- **No `.commit()`.** The edit block commits on close.

Tags are **not** removed in v11 — `sdk.registrationManager.edit().addTag(...).commit()` still works on the engagement module. Flag `addTag`/`removeTag` for manual review only if the customer wants to move them onto profile attributes for the unified surface; the shortest correct rewrite keeps them.

## Event tracking

The typed Event model is available:

```kotlin
EventManager.customEvent(
    "ProductDetail",
    mapOf("description" to "Product viewed")
)?.let { SFMCSdk.track(it) }
```

The `?.let` is **load-bearing, not stylistic**: `EventManager.customEvent` returns `Event?` and hands back `null` when the name or attributes fail validation. v11 enforces validation rules (source: `EventUtil`, the `MCET_232` contract) and drops invalid input **silently** — a WARN log, nothing thrown:

- **Event names and attribute keys** are rejected if they are blank, start with `$`, or contain a line break (`\n`/`\r`).
- **Attribute keys only** are *additionally* rejected if they contain a `.` (dot).
- Allowed: letters, digits, `_`, `-`.
- **Nested attributes** must be passed as a nested `Map<String, Any>` — the SDK flattens them to dot-notation internally. A pre-flattened key is dropped:

```kotlin
// ✅ SDK flattens to "user.id" internally
EventManager.customEvent("View", mapOf("user" to mapOf("id" to "123")))
// ❌ "user.id" contains a dot as a key → silently dropped
EventManager.customEvent("View", mapOf("user.id" to "123"))
```

The legacy SDK was more permissive, so this is a real migration trap: **audit any event name or attribute key built dynamically** (string concatenation, string templates, reflection, `enum.toString()`) for dots, a leading `$`, or line breaks. If you can't statically prove a dynamic key is clean, flag it for manual review rather than assuming the rewrite is safe.

**But** in v11 the engagement module still ships `AnalyticsManager` with the legacy verbs (`trackPageView`, `trackInboxOpenEvent`, `enableAnalytics`/`disableAnalytics`, `enablePiAnalytics`/`disablePiAnalytics`, `areAnalyticsEnabled`/`arePiAnalyticsEnabled`). Runtime toggle usage — `sdk.analyticsManager.enableAnalytics()`, `sdk.inboxMessageManager.enableInbox()`, `sdk.analyticsManager.enablePiAnalytics()` — is not deleted; those call sites need **no rewrite** in v11 beyond wrapping in `MarketingCloudSdk.requestSdk`. Only migrate to the typed Event model if the customer specifically wants the unified telemetry surface.

## In-app messaging

Register the listener **at init**, inside `InAppMessagingFeatureConfig` — this is the recommended shape because it guarantees the listener is in place before the first message can fire:

```kotlin
inAppMessagingFeatureModuleConfig = InAppMessagingFeatureConfig.builder()
    .setEventListener(object : InAppMessageManager.EventListener {
        override fun shouldShowMessage(message: InAppMessage) = true
        override fun didShowMessage(message: InAppMessage) { /* ... */ }
        override fun didCloseMessage(
            message: InAppMessage,
            closeAction: InAppMessageCloseAction   // NEW second param in v11
        ) { /* ... */ }
    })
    .build()
```

The new `closeAction` parameter is a **data class** — `InAppMessageCloseAction(val actionType: InAppMessageDismissReason, val id: String?)`, where `id` is the button id when the message was closed via a button (null otherwise). `InAppMessageDismissReason` is a nested enum: `AUTO(1)`, `BUTTON(2)`, `CLOSED(3)`, `UNKNOWN(4)`. An existing one-arg override needs the second param added (or Kotlin reports "overrides nothing" and the callback silently never fires); a body that only *logged* the close needs no further change, but code that wants to branch on how the message closed can now read it:

```kotlin
override fun didCloseMessage(message: InAppMessage, closeAction: InAppMessageCloseAction) {
    when (closeAction.actionType) {
        InAppMessageCloseAction.InAppMessageDismissReason.BUTTON ->
            Log.d(TAG, "${message.id} closed via button ${closeAction.id}")
        InAppMessageCloseAction.InAppMessageDismissReason.AUTO ->
            Log.d(TAG, "${message.id} auto-dismissed")
        else -> Log.d(TAG, "${message.id} closed (${closeAction.actionType})")
    }
}
```

A runtime `setInAppMessageListener` **does** still exist — `InAppMessageManager.setInAppMessageListener(listener: EventListener?)` (nullable, so `null` clears it). What changed is the *receiver*: it's no longer reached off the engagement `MarketingCloudSdk`. Get the manager from the IAM feature module instead:

```kotlin
InAppMessagingFeature.requestSdk { iamFeature ->
    iamFeature.getInAppMessageManager().setInAppMessageListener(myListener)
}
```

So the migration for a legacy `MarketingCloudSdk.getInstance().getInAppMessageManager().setInAppMessageListener(...)` call has two correct landing spots: fold the listener into the init `InAppMessagingFeatureConfig` (preferred), or keep it as a runtime call rewritten onto `InAppMessagingFeature.requestSdk { it.getInAppMessageManager()... }`. The one shape that does **not** exist is reaching `getInAppMessageManager()` off the engagement `MarketingCloudSdk`/`SFMCSdk` receiver — that's the prior-draft mistake, not the method itself.

## Imports & package moves

Every rewritten file needs import surgery. **Keep** `com.salesforce.marketingcloud.MarketingCloudSdk` (engagement receiver — still needed). **Add** as used: `com.salesforce.marketingcloud.sfmcsdk.SFMCSdk`, `com.salesforce.marketingcloud.sfmcsdk.SFMCSdkModuleConfig`. **Update** these — the classes moved packages between the legacy monolith and the v11 feature modules:

| Class | New package |
| --- | --- |
| `NotificationCustomizationOptions` | `com.salesforce.marketingcloud.pushfeature.notifications` |
| `PushMessageManager` | `com.salesforce.marketingcloud.pushfeature.push` |
| `NotificationManager` (with `NotificationLaunchIntentProvider`, `NotificationChannelIdProvider`, `NotificationBuilder`) | `com.salesforce.marketingcloud.pushfeature.notifications` |
| `NotificationMessage` | `com.salesforce.marketingcloud.pushmodels` |
| `InAppMessage` | `com.salesforce.marketingcloud.inappmessaging.models` |
| `InAppMessageCloseAction` | `com.salesforce.marketingcloud.inappmessagingfeature` |

The Inbox/Region models on the engagement module (`InboxMessage`, `InboxMessageManager`, `RegionMessageManager`) did **not** move — their packages under `com.salesforce.marketingcloud.messages.*` are unchanged.

**Nullability sharp edge:** `InboxMessage.url` is now `String?`. Downstream code that fed it into a non-null `String` API (a Navigation Safe-Args action, for example) needs a `.orEmpty()` or explicit null-handling.

## What to always flag, never auto-rewrite

- Custom subclasses or interface implementations of SDK types (custom receivers, custom `NotificationBuilder`).
- Reflection or string-based access to SDK class/method names.
- Tag handling — **when** the customer wants to move to unified profile attributes. If they want continuity, tags still work; don't force the change.
- Any symbol with no matrix entry.
- Commerce/analytics calls where the original field population is non-obvious.
- `POST_NOTIFICATIONS` runtime permission on Android 13+ — v11 usually bumps `targetSdk` to 33+, which trips this. Add the permission and a runtime request; flag if not already handled.
