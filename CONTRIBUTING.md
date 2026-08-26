# راهنمای مشارکت

از مشارکت در Enterprise Knowledge Platform سپاسگزاریم. تغییرات باید کوچک، قابل بازبینی و همراه با تست باشند.

## راه‌اندازی محیط توسعه

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
copy .env.example .env
```

در Linux و macOS به‌جای دستور فعال‌سازی بالا از `source .venv/bin/activate` استفاده کنید.

## کنترل کیفیت

پیش از ارسال Pull Request اجرا کنید:

```powershell
python -m ruff check .
python -m pytest
```

برای فعال کردن کنترل‌های خودکار پیش از commit:

```powershell
python -m pip install pre-commit
pre-commit install
```

## قواعد تغییر

- برای رفتار جدید یا رفع باگ، تست اضافه کنید.
- API موجود را بدون توضیح migration ناسازگار نکنید.
- فایل `.env`، دیتابیس، اسناد بارگذاری‌شده و indexهای FAISS را commit نکنید.
- متن commit را امری و کوتاه بنویسید؛ مانند `fix: validate review transition`.
- تغییرات امنیتی را ابتدا طبق [SECURITY.md](SECURITY.md) به‌صورت خصوصی گزارش کنید.

## Pull Request

PR باید مسئله، راه‌حل، روش تست و هر تغییر در schema یا تنظیمات را توضیح دهد. CI باید سبز باشد و داده حساس یا generated artifact در diff وجود نداشته باشد.

