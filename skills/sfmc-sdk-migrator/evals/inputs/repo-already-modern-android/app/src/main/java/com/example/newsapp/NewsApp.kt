package com.example.newsapp

import android.app.Application
import android.util.Log
import com.salesforce.marketingcloud.MarketingCloudConfig
import com.salesforce.marketingcloud.sfmcsdk.SFMCSdk
import com.salesforce.marketingcloud.sfmcsdk.SFMCSdkModuleConfig
import com.salesforce.marketingcloud.pushfeature.PushFeatureConfig

/**
 * ALREADY MIGRATED. Boots the unified SDK via SFMCSdk.configure with module
 * configs. There is NO MarketingCloudSdk.init / getInstance here, so the scanner
 * must report migrationStatus=already-modern and the skill must NOT rewrite this.
 */
class NewsApp : Application() {

    override fun onCreate() {
        super.onCreate()

        SFMCSdk.configure(this, SFMCSdkModuleConfig.build {
            engagementModuleConfig = MarketingCloudConfig.Builder()
                .setApplicationId(BuildConfig.MC_APP_ID)
                .setAccessToken(BuildConfig.MC_ACCESS_TOKEN)
                .setMarketingCloudServerUrl(BuildConfig.MC_SERVER_URL)
                .setInboxEnabled(true)
                .setAnalyticsEnabled(true)
                .build(this)

            pushFeatureModuleConfig = PushFeatureConfig.builder()
                .setSenderId(BuildConfig.FCM_SENDER_ID)
                .build()
        }) { initStatus ->
            AppState.sdkReady = initStatus.isUsable
            Log.i("NewsApp", "SFMC init usable=${initStatus.isUsable}")
        }
    }
}

object AppState {
    @Volatile
    var sdkReady: Boolean = false
}
