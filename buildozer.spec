[app]
title = AutoGen
package.name = autogen
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 1
entrypoint = main.py
icon.filename = AutoGen.png
presplash.filename = AutoGenSplash.png
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.arch = armeabi-v7a,arm64-v8a
android.enable_androidx = True
android.debug = 1
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1