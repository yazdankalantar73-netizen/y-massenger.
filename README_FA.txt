Y MESSENGER - Kivy

فایل‌ها:
- kivy_app.py : برنامه اندروید با Kivy
- server.py   : همان بک‌اند Flask پروژه
- buildozer.spec : تنظیمات ساخت APK
- requirements.txt : وابستگی‌ها

نکته مهم:
در گوشی، 127.0.0.1 به خود گوشی اشاره می‌کند. اگر server.py روی کامپیوتر اجرا می‌شود،
داخل برنامه روی «آدرس سرور» بزن و IP کامپیوتر را وارد کن، مثلاً:
http://192.168.1.20:5000

روی کامپیوتر:
python server.py

ساخت APK روی Linux/WSL:
pip install buildozer
buildozer android debug

خروجی APK معمولاً داخل پوشه bin ساخته می‌شود.
