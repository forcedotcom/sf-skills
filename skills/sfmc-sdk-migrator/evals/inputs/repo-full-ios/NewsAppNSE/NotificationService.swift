import UserNotifications
import MarketingCloudSDK

// Notification Service Extension for rich-media push. Under the legacy SDK the
// NSE forwards the request to the shared MarketingCloudSDK instance so it can
// fetch image attachments and hand the receipt back to the main app via the
// shared App Group.
//
// Migration target: switch to MCExtensionSDK in the NSE target only (not the
// main app). Always flag for manual review because a wrong rewrite drops
// push-open reporting silently.
class NotificationService: UNNotificationServiceExtension {

    var contentHandler: ((UNNotificationContent) -> Void)?
    var bestAttemptContent: UNMutableNotificationContent?

    override func didReceive(_ request: UNNotificationRequest,
                             withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void) {
        self.contentHandler = contentHandler
        bestAttemptContent = (request.content.mutableCopy() as? UNMutableNotificationContent)

        MarketingCloudSDK.sharedInstance().sfmc_setNotificationRequest(request)

        if let content = bestAttemptContent {
            contentHandler(content)
        }
    }
}
