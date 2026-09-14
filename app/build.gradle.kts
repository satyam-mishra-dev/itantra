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

    buildFeatures { buildConfig = true }
    // Where <lang>-stt.zip / <lang>-tts.zip live. Override for a local test server:
    //   ./gradlew assembleDebug -PpackBase=http://10.0.2.2:8000
    defaultConfig.buildConfigField("String", "PACK_BASE",
        "\"${project.findProperty("packBase") ?: "https://github.com/satyam-mishra-dev/itantra-packs/releases/download/v1"}\"")

    // One committed key for every build type + every machine: an APK built on a teammate's laptop
    // used to fail to update one built here ("App not installed" — different debug keys).
    signingConfigs.create("shared") {
        storeFile = file("itantra.keystore"); storePassword = "itantra"; keyAlias = "itantra"; keyPassword = "itantra"
    }
    buildTypes.all { signingConfig = signingConfigs.getByName("shared") }

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
