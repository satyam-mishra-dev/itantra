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
        versionCode = 2
        versionName = "0.3"
        ndk {
            // real target phones are ARM; dropping x86 halves the APK (rubric: efficiency)
            abiFilters += listOf("arm64-v8a", "armeabi-v7a")
        }
    }

    buildFeatures { buildConfig = true }
    // Where <lang>-stt.zip / <lang>-tts.zip live. Override for a local test server:
    //   ./gradlew assembleDebug -PpackBase=http://10.0.2.2:8000
    defaultConfig.buildConfigField("String", "PACK_BASE",
        "\"${project.findProperty("packBase") ?: "https://github.com/satyam-mishra-dev/itantra/releases/download/v0.3"}\"")

    // Release signing credentials must never be committed to source control.
    // Configure all four environment variables in a trusted local environment or CI:
    // ANDROID_KEYSTORE_PATH, ANDROID_KEYSTORE_PASSWORD,
    // ANDROID_KEY_ALIAS, ANDROID_KEY_PASSWORD.
    val releaseStoreFile = providers.environmentVariable("ANDROID_KEYSTORE_PATH").orNull
    val releaseStorePassword = providers.environmentVariable("ANDROID_KEYSTORE_PASSWORD").orNull
    val releaseKeyAlias = providers.environmentVariable("ANDROID_KEY_ALIAS").orNull
    val releaseKeyPassword = providers.environmentVariable("ANDROID_KEY_PASSWORD").orNull

    val releaseSigningValues = listOf(
        releaseStoreFile,
        releaseStorePassword,
        releaseKeyAlias,
        releaseKeyPassword
    )
    val hasReleaseSigningCredentials = releaseSigningValues.all { !it.isNullOrBlank() }
    val hasPartialReleaseSigningCredentials =
        releaseSigningValues.any { !it.isNullOrBlank() } && !hasReleaseSigningCredentials

    if (hasPartialReleaseSigningCredentials) {
        throw GradleException(
            "Incomplete release signing configuration. Provide all four ANDROID_KEYSTORE_* environment variables."
        )
    }

    if (hasReleaseSigningCredentials) {
        signingConfigs.create("release") {
            storeFile = file(releaseStoreFile!!)
            storePassword = releaseStorePassword!!
            keyAlias = releaseKeyAlias!!
            keyPassword = releaseKeyPassword!!
        }
    }

    buildTypes {
        getByName("debug") {
            // Use Android Gradle Plugin's standard per-user debug signing key.
        }
        getByName("release") {
            // Without release credentials, this remains an unsigned release build.
            if (hasReleaseSigningCredentials) {
                signingConfig = signingConfigs.getByName("release")
            }
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
