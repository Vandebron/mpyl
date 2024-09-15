plugins {
    `kotlin-dsl`
    idea
}

subprojects {
    apply(plugin = "idea")
}

allprojects {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}