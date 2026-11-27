import Foundation
import MarketingCloudSDK

// Handles user-level identity handoff to the marketing SDK when the user signs
// in. Every call here must be preserved after migration; only the SDK receivers
// and selectors change.
final class UserSession {

    static let shared = UserSession()

    func setActiveUser(email: String, firstName: String, lastName: String) {
        _ = MarketingCloudSDK.sharedInstance().sfmc_setContactKey(email)
        _ = MarketingCloudSDK.sharedInstance().sfmc_setAttributeNamed("firstName", value: firstName)
        _ = MarketingCloudSDK.sharedInstance().sfmc_setAttributeNamed("lastName", value: lastName)

        // Business logic to PRESERVE: local cache does not go through the SDK.
        AnalyticsCache.lastUserEmail = email
    }

    func trackDetail(id: String, title: String) {
        _ = MarketingCloudSDK.sharedInstance()
            .sfmc_trackPageView(withURL: "data://ProductDetail/\(id)",
                                title: title,
                                item: nil,
                                search: nil)
    }
}
