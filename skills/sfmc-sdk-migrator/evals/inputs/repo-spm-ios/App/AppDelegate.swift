import UIKit
import MarketingCloudSDK

@main
class AppDelegate: UIResponder, UIApplicationDelegate {

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {

        let config: [String: Any] = [
            "appId": "spm-fixture-app-id",
            "accessToken": "spm-fixture-token",
            "marketingCloudServerUrl": "https://example.marketingcloudapis.com",
            "mid": "1234567890",
            "inboxEnabled": true,
            "analyticsEnabled": true,
        ]
        _ = MarketingCloudSDK.sharedInstance().sfmc_configure(with: config)
        _ = MarketingCloudSDK.sharedInstance().sfmc_setContactKey("spm-fixture@example.com")
        return true
    }
}
