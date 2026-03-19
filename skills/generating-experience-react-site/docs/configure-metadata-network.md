# Configure Metadata: Network

## Purpose
This configuration file creates a **net-new, default** Network metadata record for a Digital Experience React Site. It is not intended to edit or modify an existing Network record. Use this template only when provisioning a brand-new React site.

## File Location
```
networks/{siteName}.network-meta.xml
```

## Default Template
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Network xmlns="http://soap.sforce.com/2006/04/metadata">
    <allowInternalUserLogin>false</allowInternalUserLogin>
    <allowMembersToFlag>false</allowMembersToFlag>
    <changePasswordTemplate>unfiled$public/CommunityChangePasswordEmailTemplate</changePasswordTemplate>
    <disableReputationRecordConversations>true</disableReputationRecordConversations>
    <emailSenderAddress>admin@company.com</emailSenderAddress>
    <emailSenderName>{siteName}</emailSenderName>
    <embeddedLoginEnabled>false</embeddedLoginEnabled>
    <enableApexCDNCaching>true</enableApexCDNCaching>
    <enableCustomVFErrorPageOverrides>false</enableCustomVFErrorPageOverrides>
    <enableDirectMessages>true</enableDirectMessages>
    <enableExpFriendlyUrlsAsDefault>false</enableExpFriendlyUrlsAsDefault>
    <enableExperienceBundleBasedSnaOverrideEnabled>true</enableExperienceBundleBasedSnaOverrideEnabled>
    <enableGuestChatter>{enableGuestAccess}</enableGuestChatter>
    <enableGuestFileAccess>false</enableGuestFileAccess>
    <enableGuestMemberVisibility>false</enableGuestMemberVisibility>
    <enableImageOptimizationCDN>true</enableImageOptimizationCDN>
    <enableInvitation>false</enableInvitation>
    <enableKnowledgeable>false</enableKnowledgeable>
    <enableLWRExperienceConnectedApp>false</enableLWRExperienceConnectedApp>
    <enableMemberVisibility>false</enableMemberVisibility>
    <enableNicknameDisplay>true</enableNicknameDisplay>
    <enablePrivateMessages>false</enablePrivateMessages>
    <enableReputation>false</enableReputation>
    <enableShowAllNetworkSettings>false</enableShowAllNetworkSettings>
    <enableSiteAsContainer>true</enableSiteAsContainer>
    <enableTalkingAboutStats>true</enableTalkingAboutStats>
    <enableTopicAssignmentRules>true</enableTopicAssignmentRules>
    <enableTopicSuggestions>false</enableTopicSuggestions>
    <enableUpDownVote>false</enableUpDownVote>
    <forgotPasswordTemplate>unfiled$public/CommunityForgotPasswordEmailTemplate</forgotPasswordTemplate>
    <gatherCustomerSentimentData>false</gatherCustomerSentimentData>
    <headlessForgotPasswordTemplate>unfiled$public/CommunityHeadlessForgotPasswordTemplate</headlessForgotPasswordTemplate>
    <headlessRegistrationTemplate>unfiled$public/CommunityHeadlessRegistrationTemplate</headlessRegistrationTemplate>
    <networkMemberGroups>
        <profile>admin</profile>
    </networkMemberGroups>
    <networkPageOverrides>
        <changePasswordPageOverrideSetting>Standard</changePasswordPageOverrideSetting>
        <forgotPasswordPageOverrideSetting>Designer</forgotPasswordPageOverrideSetting>
        <homePageOverrideSetting>Designer</homePageOverrideSetting>
        <loginPageOverrideSetting>Designer</loginPageOverrideSetting>
        <selfRegProfilePageOverrideSetting>Designer</selfRegProfilePageOverrideSetting>
    </networkPageOverrides>
    <newSenderAddress>admin@company.com</newSenderAddress>
    <picassoSite>{siteName}1</picassoSite>
    <selfRegistration>false</selfRegistration>
    <sendWelcomeEmail>true</sendWelcomeEmail>
    <site>{siteName}</site>
    <siteArchiveStatus>NotArchived</siteArchiveStatus>
    <status>Live</status>
    <tabs>
        <defaultTab>home</defaultTab>
        <standardTab>Chatter</standardTab>
    </tabs>
    <urlPathPrefix>{siteUrlPathPrefix}vforcesite</urlPathPrefix>
    <welcomeTemplate>unfiled$public/CommunityWelcomeEmailTemplate</welcomeTemplate>
</Network>
```
