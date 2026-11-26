package com.example.newsapp

import android.content.Context

/**
 * Plain app code with NO SFMC SDK usage. It exists so the eval can assert the
 * migration leaves non-SDK business logic untouched (AnalyticsCache.lastUser,
 * AppState.sdkReady, NotificationRouter.show).
 */
object AnalyticsCache {
    @Volatile
    var lastUser: String? = null
}

object AppState {
    @Volatile
    var sdkReady: Boolean = false
}

object NotificationRouter {
    fun show(context: Context, title: String, body: String) {
        // Pretend to post a local notification. The eval only cares that this
        // method and its call site survive the migration unchanged.
    }
}
