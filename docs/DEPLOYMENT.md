# راهنمای استقرار

## اجرای محلی

```powershell
copy .env.example .env
docker compose up --build
```

سپس رابط در `http://localhost:8501` و مستندات API در `http://localhost:8000/docs` در دسترس‌اند.

## متغیرهای ضروری

تنظیمات نمونه در `.env.example` قرار دارد. مقدار واقعی `AVALAI_API_KEY` را هرگز داخل image یا Git قرار ندهید. در محیط سازمانی از Docker secrets، Kubernetes Secrets یا secret manager استفاده کنید.

## داده پایدار

Compose از volumeهای نام‌دار برای `data`، `storage` و cache مدل استفاده می‌کند. پیش از upgrade از volume داده و دیتابیس backup سازگار تهیه کنید.

## Production checklist

- reverse proxy با TLS و محدودیت اندازه request؛
- احراز هویت SSO و RBAC در API؛
- PostgreSQL و migration versioned؛
- object storage امن و malware scanning؛
- worker queue برای OCR و embedding؛
- observability، rate limiting و backup/restore آزموده‌شده؛
- pin کردن image و dependencyها و اجرای vulnerability scan؛
- عدم انتشار پورت API در اینترنت مگر پشت gateway.

این MVP تا تکمیل موارد بالا نباید میزبان دانش محرمانه باشد.

