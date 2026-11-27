package com.example.newsapp

import com.salesforce.marketingcloud.MarketingCloudSdk

/**
 * Wraps identity + analytics call sites against the legacy SDK.
 *
 * Migration targets:
 *  - setContactKey / setAttribute -> SFMCSdk.requestSdk { identity.edit { ... } }
 *  - addTag -> MANUAL REVIEW (still legal on the engagement module; marketing
 *    team decides whether to keep tags or move to a profile attribute)
 *  - trackPageView -> EventManager.customEvent + SFMCSdk.track (or keep on
 *    engagement analyticsManager)
 */
object UserSession {

    fun signIn(email: String, firstName: String, segment: String) {
        // Business logic to PRESERVE: remember who signed in last.
        AnalyticsCache.lastUser = email

        MarketingCloudSdk.getInstance().registrationManager
            .edit()
            .setContactKey(email)
            .setAttribute("firstName", firstName)
            .addTag(segment)
            .commit()
    }

    fun trackProductView(productId: String) {
        MarketingCloudSdk.getInstance().analyticsManager
            .trackPageView("data://ProductDetail/$productId", "Product viewed")
    }

    fun currentPushToken(): String {
        return MarketingCloudSdk.getInstance().pushMessageManager.pushToken.orEmpty()
    }
}
