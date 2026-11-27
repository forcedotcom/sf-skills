plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.example.newsapp"
    compileSdk = 33

    defaultConfig {
        applicationId = "com.example.newsapp"
        minSdk = 24
        targetSdk = 33
        versionCode = 1
        versionName = "1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)

    // Legacy SFMC SDK via the version catalog. Migration updates the catalog
    // entry and adds the unified core + push feature module.
    implementation(libs.marketingcloud)
}
