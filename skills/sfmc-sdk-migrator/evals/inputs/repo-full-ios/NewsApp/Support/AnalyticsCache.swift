import Foundation

// Non-SDK business logic. Migration MUST NOT touch these files — they are the
// fixture's guardrail for "don't rewrite unrelated code".
enum AnalyticsCache {
    static var lastUserEmail: String?
    static var lastConfigureSucceeded: Bool = false
}

enum AppState {
    static var sdkReady: Bool = false
    static var lastNotificationIdentifier: String?
}

enum Constants {
    static let mcAppId = "REPLACE_ME_APP_ID"
    static let mcAccessToken = "REPLACE_ME_TOKEN"
    static let mcServerUrl = "https://example.marketingcloudapis.com"
    static let mcMid = "REPLACE_ME_MID"
}
