import UIKit
import MarketingCloudSDK

@main
class AppDelegate: UIResponder, UIApplicationDelegate {

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {

        let config: [String: Any] = [
            "appId": "cocoapods-fixture-app-id",
            "accessToken": "cocoapods-fixture-token",
            "marketingCloudServerUrl": "https://example.marketingcloudapis.com",
            "mid": "1234567890",
            "inboxEnabled": false,
            "analyticsEnabled": true,
        ]
        return MarketingCloudSDK.sharedInstance().sfmc_configure(with: config)
    }
}
