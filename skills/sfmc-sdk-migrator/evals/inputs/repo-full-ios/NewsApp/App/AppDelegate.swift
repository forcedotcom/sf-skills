import UIKit
import UserNotifications
import MarketingCloudSDK

// Application delegate that boots the legacy Marketing Cloud iOS SDK.
//
// Migration target: replace sfmc_configure with SFMCSdk.initializeSdk driven by
// SFMCSdkConfigBuilder.setPush(config:). Preserve AppState.sdkReady and the
// AnalyticsCache updates below when rewriting.
@main
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {

        let config: [String: Any] = [
            "appId": Constants.mcAppId,
            "accessToken": Constants.mcAccessToken,
            "marketingCloudServerUrl": Constants.mcServerUrl,
            "mid": Constants.mcMid,
            "inboxEnabled": true,
            "analyticsEnabled": true,
            "delayRegistrationUntilContactKeyIsSet": true,
        ]
        let success = MarketingCloudSDK.sharedInstance().sfmc_configure(with: config)

        // Business logic to PRESERVE: readiness gate for the rest of the app.
        AppState.sdkReady = success
        AnalyticsCache.lastConfigureSucceeded = success

        _ = MarketingCloudSDK.sharedInstance().sfmc_addTag("news-app-launched")
        UNUserNotificationCenter.current().delegate = self

        return success
    }

    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        MarketingCloudSDK.sharedInstance().sfmc_setDeviceToken(deviceToken)
    }
}

extension AppDelegate: UNUserNotificationCenterDelegate {

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        // Business logic to PRESERVE: forward local notifications to the app router.
        AppState.lastNotificationIdentifier = response.notification.request.identifier

        MarketingCloudSDK.sharedInstance().sfmc_setNotificationRequest(response.notification.request)
        completionHandler()
    }
}
