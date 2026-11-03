# ساخت BamdadDesk برای مک

در بخش Actions، workflow با نام **Custom macOS Client Generator** را اجرا کنید.
ورودی `version` نسخهٔ RustDesk است؛ مثلاً `1.5.0`.
برای تنظیمات بدون رمز از `config_json` استفاده کنید:

```json
{"platform":"macos","appname":"BamdadDesk","exename":"bamdad","serverIP":"desk.example.org","overrideManual":"relay-server=desk.example.org:21117"}
```

برای تنظیمات محرمانه یا تصاویر، `config_ref` شاخهٔ رمزگذاری‌شدهٔ
`rdgen-inputs/<UUID>` و secret موجود `RDGEN_PRIVATE_KEY` پشتیبانی می‌شوند.
شاخهٔ موقت بعد از ساخت حذف می‌شود. رمز عبور را در `config_json` وارد نکنید.
این مسیر از Actions اجرا می‌شود؛ دکمهٔ سایت فعلاً مخصوص Windows است.

خروجی‌ها در Artifacts همان اجرا تا ۳۰ روز قابل دریافت‌اند:

- `macos-client-x86_64`: مک‌های Intel
- `macos-client-aarch64`: مک‌های Apple Silicon، سری M

فایل ZIP را باز کنید، DMG داخل آن را اجرا کنید و BamdadDesk را به Applications بکشید.
برای کنترل دستگاه، مجوزهای Screen Recording و Accessibility را در
System Settings → Privacy & Security فعال کنید.

معماری پردازنده، امضای bundle و تنظیمات داخل برنامه پیش از بسته‌بندی بررسی می‌شوند.
بدون گواهی Apple، خروجی امضای ad-hoc دارد و notarized نیست؛ macOS ممکن است
برای اجرای آن تأیید کاربر را در Privacy & Security بخواهد.
این بررسی‌های ساخت جای تست اتصال و مجوزها روی مک واقعی را نمی‌گیرند.
