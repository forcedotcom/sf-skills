package com.example.newsapp

import android.app.Application
import android.util.Log
import com.salesforce.marketingcloud.MarketingCloudConfig
import com.salesforce.marketingcloud.MarketingCloudSdk
import com.salesforce.marketingcloud.notifications.NotificationCustomizationOptions

/**
 * Application subclass that boots the LEGACY Marketing Cloud SDK.
 *
 * Migration target: the legacy init call below becomes SFMCSdk.configure(...)
 * with a SFMCSdkModuleConfig.build { } block. setSenderId must move onto the
 * push feature config; every other setter stays on the engagement config.
 */
class NewsApp : Application() {

    override fun onCreate() {
        super.onCreate()

        MarketingCloudSdk.init(
            this,
            MarketingCloudConfig.builder()
                .setApplicationId(BuildConfig.MC_APP_ID)
                .setAccessToken(BuildConfig.MC_ACCESS_TOKEN)
                .setSenderId(BuildConfig.FCM_SENDER_ID)
                .setMarketingCloudServerUrl(BuildConfig.MC_SERVER_URL)
                .setMid(BuildConfig.MC_MID)
                .setInboxEnabled(true)
                .setAnalyticsEnabled(true)
                .setNotificationCustomizationOptions(
                    NotificationCustomizationOptions.create(R.drawable.ic_notification)
                )
                .build(this)
        ) { initStatus ->
            // Business logic to PRESERVE: our own readiness bookkeeping.
            AppState.sdkReady = initStatus.isUsable
            Log.i("NewsApp", "SFMC init usable=${initStatus.isUsable}")
        }
    }
}
