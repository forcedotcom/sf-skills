package com.example.newsapp

import com.salesforce.marketingcloud.sfmcsdk.SFMCSdk

/**
 * Already-unified identity call site. Uses SFMCSdk.requestSdk + identity.edit
 * with the extension-receiver lambda (profileId property, attributes editor).
 * This is the correct modern shape — the skill must leave it alone.
 */
object UserSession {

    fun signIn(email: String, firstName: String) {
        SFMCSdk.requestSdk { sdk ->
            sdk.identity.edit {
                profileId = email
                attributes.set("firstName", firstName)
            }
        }
    }
}
