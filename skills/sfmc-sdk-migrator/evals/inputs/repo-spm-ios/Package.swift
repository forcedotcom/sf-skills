// swift-tools-version:5.7
import PackageDescription

let package = Package(
    name: "NewsApp",
    platforms: [.iOS(.v12)],
    products: [
        .library(name: "NewsApp", targets: ["NewsApp"]),
    ],
    dependencies: [
        .package(
            url: "https://github.com/salesforce-marketingcloud/MarketingCloudSDK-iOS-SDK.git",
            exact: "8.1.1"
        ),
    ],
    targets: [
        .target(
            name: "NewsApp",
            dependencies: [
                .product(name: "MarketingCloudSDK", package: "MarketingCloudSDK-iOS-SDK"),
            ]
        ),
    ]
)
