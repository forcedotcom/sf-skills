# Configure Metadata: CustomSite

## Purpose
This configuration file creates a **net-new, default** CustomSite metadata record for a Digital Experience React Site. It is not intended to edit or modify an existing CustomSite record. Use this template only when provisioning a brand-new React site.

## File Location
```
sites/{siteName}.site-meta.xml
```

## Default Template
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <active>true</active>
    <allowGuestPaymentsApi>false</allowGuestPaymentsApi>
    <allowHomePage>false</allowHomePage>
    <allowStandardAnswersPages>false</allowStandardAnswersPages>
    <allowStandardIdeasPages>false</allowStandardIdeasPages>
    <allowStandardLookups>false</allowStandardLookups>
    <allowStandardPortalPages>true</allowStandardPortalPages>
    <allowStandardSearch>false</allowStandardSearch>
    <authorizationRequiredPage>CommunitiesLogin</authorizationRequiredPage>
    <bandwidthExceededPage>BandwidthExceeded</bandwidthExceededPage>
    <browserXssProtection>true</browserXssProtection>
    <cachePublicVisualforcePagesInProxyServers>true</cachePublicVisualforcePagesInProxyServers>
    <clickjackProtectionLevel>SameOriginOnly</clickjackProtectionLevel>
    <contentSniffingProtection>true</contentSniffingProtection>
    <enableAuraRequests>true</enableAuraRequests>
    <fileNotFoundPage>FileNotFound</fileNotFoundPage>
    <genericErrorPage>Exception</genericErrorPage>
    <inMaintenancePage>InMaintenance</inMaintenancePage>
    <indexPage>CommunitiesLanding</indexPage>
    <masterLabel>{siteName}</masterLabel>
    <redirectToCustomDomain>false</redirectToCustomDomain>
    <referrerPolicyOriginWhenCrossOrigin>true</referrerPolicyOriginWhenCrossOrigin>
    <selfRegPage>CommunitiesSelfReg</selfRegPage>
    <siteType>ChatterNetwork</siteType>
    <urlPathPrefix>{siteUrlPathPrefix}vforcesite</urlPathPrefix>
</CustomSite>
```
