rootProject.name = "gradle-multi-module"
include("tests:projects:gradle")

dependencyResolutionManagement {
    versionCatalogs {
        create("libs") {
            from(files("libs.versions.toml"))
        }
    }
}