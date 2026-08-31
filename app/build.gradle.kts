plugins {
    id("com.android.application") version "9.3.2" // AGP 9 ships built-in Kotlin support
}

android {
    namespace = "com.nullpointers.itantra"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.nullpointers.itantra"
        minSdk = 26 // res/font (Outfit) needs 26; Android 8 (2017) is the floor of "low-end phones sold today"
        targetSdk = 34
        versionCode = 1
        versionName = "0.2"
        ndk {
            // real target phones are ARM; dropping x86 halves the APK (rubric: efficiency)
            abiFilters += listOf("arm64-v8a", "armeabi-v7a")
        }
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
