package com.example.newsapp

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.salesforce.marketingcloud.MarketingCloudSdk
import com.salesforce.marketingcloud.messages.push.PushMessageManager

/**
 * App-owned FirebaseMessagingService. This class STAYS app-owned across the
 * migration (manual-review flag): only the two SDK calls inside it get rewritten
 * (PushMessageManager import moves; handleMessage / setPushToken go through
 * PushFeature.requestSdk). handleOwnPush is the customer's own logic to PRESERVE.
 */
class NewsMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        MarketingCloudSdk.getInstance().pushMessageManager.setPushToken(token)
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        if (PushMessageManager.isMarketingCloudPush(remoteMessage)) {
            MarketingCloudSdk.getInstance().pushMessageManager.handleMessage(remoteMessage)
        } else {
            handleOwnPush(remoteMessage)
        }
    }

    // Business logic to PRESERVE: our non-SFMC push path.
    private fun handleOwnPush(remoteMessage: RemoteMessage) {
        val title = remoteMessage.data["title"] ?: "News"
        NotificationRouter.show(applicationContext, title, remoteMessage.data["body"].orEmpty())
    }
}
