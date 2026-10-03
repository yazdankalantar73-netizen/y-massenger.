[app]
title = Y MESSENGER
package.name = ymessenger
package.domain = com.yazdanscript
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,json
version = 1.26.1.7
requirements = python3,kivy,requests,pillow
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[android]
android.api = 35
android.minapi = 23
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
