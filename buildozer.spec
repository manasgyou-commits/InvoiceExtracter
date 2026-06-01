[app]
title = Invoice Extractor Pro
package.name = invoiceextractor
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 1.0.0

# Core requirements — PyMuPDF preferred for PDF; pdf2image is the fallback
requirements = python3,kivy==2.2.1,pillow,pytesseract,opencv-python-headless,numpy,PyMuPDF

orientation = portrait
fullscreen = 0

# Android settings
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.arch = arm64-v8a
android.private_storage = True
android.accept_sdk_license = True
android.presplash_color = #FFFFFF
android.wakelock = False
android.logcat_filters = *:S python:D
android.copy_libs = 1
android.apptheme = @android:style/Theme.NoTitleBar
android.release_artifact = apk
android.allow_backup = True
android.entrypoint = org.kivy.android.PythonActivity

[buildozer]
log_level = 2
warn_on_root = 1
