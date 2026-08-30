plugins {
    id("com.android.application") version "9.3.2" // AGP 9 ships built-in Kotlin support
}

android {
    namespace = "com.nullpointers.itantra"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.nullpointers.itantra"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "0.1"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    // sherpa-onnx is NOT on Maven Central — download the AAR from k2-fsa GitHub
    // releases into app/libs/ (see README). Build stays green without it (P2 wiring).
    val sherpa = file("libs/sherpa-onnx.aar")
    if (sherpa.exists()) implementation(files(sherpa))

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303") // android.jar provides org.json on-device
}
