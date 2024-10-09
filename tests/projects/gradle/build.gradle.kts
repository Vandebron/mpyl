@Suppress("DSL_SCOPE_VIOLATION") // See https://github.com/gradle/gradle/issues/22797
plugins {
    `kotlin-dsl`
    idea
    application
    alias(libs.plugins.springFrameworkBootPlugin)
    alias(libs.plugins.kotlinSpringPlugin)
    alias(libs.plugins.springSependencymanagement)
}

springBoot {
    mainClass.value("com.example.multimodule.service.ApplicationOne")
}

dependencies {
    implementation(libs.spring.boot.starter)
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
}