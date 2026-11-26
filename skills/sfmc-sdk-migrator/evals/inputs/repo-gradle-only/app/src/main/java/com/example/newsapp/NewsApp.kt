package com.example.newsapp

import android.app.Application
import com.salesforce.marketingcloud.MarketingCloudConfig
import com.salesforce.marketingcloud.MarketingCloudSdk

/**
 * Minimal legacy init. The gradle-only eval focuses on the build-file update,
 * but there is exactly one call site (this init) that must also migrate to
 * SFMCSdk.configure so the fixture isn't a pure dependency bump.
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
                .build(this)
        ) { initStatus ->
            AppState.initialized = initStatus.isUsable
        }
    }
}

object AppState {
    @Volatile
    var initialized: Boolean = false
}
