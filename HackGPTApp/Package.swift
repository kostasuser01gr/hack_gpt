// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "HackGPTApp",
    platforms: [
        .macOS(.v13),
        .iOS(.v16)
    ],
    targets: [
        .executableTarget(
            name: "HackGPTApp",
            path: "Sources/HackGPTApp",
            swiftSettings: [
                .unsafeFlags(["-parse-as-library"])
            ]
        )
    ]
)
