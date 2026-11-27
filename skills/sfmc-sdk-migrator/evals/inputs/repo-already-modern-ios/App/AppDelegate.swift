import UIKit
import UserNotifications
import SFMCSDK
import MarketingCloudSDK
import PushFeatureSDK

@main
class AppDelegate: UIResponder, UIApplicationDelegate {

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {

        var configBuilder = ConfigBuilder()

        let engagementConfig = MarketingCloudSdkConfigBuilder(appId: "modern-app-id")
            .setAccessToken("modern-token")
            .setMarketingCloudServerUrl(URL(string: "https://example.marketingcloudapis.com")!)
            .setMid("1234567890")
            .setInboxEnabled(true)
            .setAnalyticsEnabled(true)
            .build()
        configBuilder = configBuilder.setEngagement(config: engagementConfig)

        let pushConfig = PushFeatureConfigBuilder()
            .setApplicationControlsBadging(true)
            .build()
        configBuilder = configBuilder.setPushFeature(config: pushConfig)

        SFMCSdk.initializeSdk(configBuilder.build()) { _ in }

        UNUserNotificationCenter.current().delegate = self
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, _ in
            guard granted else { return }
            DispatchQueue.main.async {
                UIApplication.shared.registerForRemoteNotifications()
            }
        }

        return true
    }

    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        PushFeature.requestSdk { pfSdk in
            pfSdk?.setDeviceToken(deviceToken)
        }
    }
}

extension AppDelegate: UNUserNotificationCenterDelegate {
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        PushFeature.requestSdk { pfSdk in
            pfSdk?.setNotificationResponse(response)
        }
        completionHandler()
    }
}
