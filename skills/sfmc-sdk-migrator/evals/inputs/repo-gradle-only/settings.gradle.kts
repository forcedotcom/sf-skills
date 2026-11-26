pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        maven { url = uri("https://salesforce-marketingcloud.github.io/MarketingCloudSDK-Android/repository") }
    }
}
rootProject.name = "news-app"
include(":app")
