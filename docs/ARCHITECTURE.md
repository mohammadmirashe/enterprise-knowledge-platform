# معماری سامانه

## نمای کلی

سامانه از دو ورودی اصلی تشکیل شده است: رابط Streamlit برای کاربران و API مبتنی بر FastAPI. داده‌های ساخت‌یافته در SQLite، فایل‌های اصلی در storage محلی و chunkهای قابل بازیابی در FAISS نگهداری می‌شوند.

```text
Browser
  └─ Streamlit UI (ui.py)
       └─ FastAPI (app/main.py)
            ├─ Capture and evaluation (app/capture_agent.py)
            ├─ SQLite persistence (app/database.py)
            ├─ File extraction/OCR (app/ingestion.py)
            ├─ PDF export (app/pdf_export.py)
            └─ RAG service (app/service.py)
                 ├─ Cleaning and splitting (src/)
                 ├─ Embeddings
                 ├─ FAISS vector store
                 └─ OpenAI-compatible LLM
```

## جریان ثبت دانش

1. کاربر یک capture session ایجاد می‌کند.
2. متن یا سند به فیلدهای ساخت‌یافته تبدیل می‌شود.
3. ارزیابی completeness، quality، evidence و confidence انجام می‌شود.
4. پیش‌نویس ذخیره و برای بازبینی ارسال می‌شود.
5. پس از تأیید، رکورد منتشرشده وارد documents و index بازیابی می‌شود.

## مرزهای داده

- `data/uploads/`: فایل‌های اصلی؛ نباید وارد Git شوند.
- `data/processed/`: JSONLهای پردازش‌شده؛ قابل بازسازی و خارج از Git.
- `storage/knowledge.db`: داده‌های عملیاتی SQLite.
- `storage/vector_db/`: index و metadata مربوط به FAISS.

## محدودیت فعلی

نسخه MVP فاقد identity provider و authorization واقعی است. همچنین retrieval فعلی باید پیش از Production به فیلترهای status، sensitivity، tenant و واحد سازمانی مجهز شود. جزئیات بیشتر در [SECURITY.md](../SECURITY.md) آمده است.

## Demo Mode

در `DEMO_MODE=true`، پنج رکورد کاملاً ساختگی از مسیر واقعی persistence، review و graph به‌صورت idempotent ایجاد می‌شوند. پاسخ‌گویی دمو از یک retrieval محلی و deterministic روی رکوردهای منتشرشده استفاده می‌کند و هیچ فراخوانی خارجی یا دانلود embedding ندارد. این مسیر برای walkthrough و ارزیابی repository است و جایگزین RAG یا کنترل دسترسی Production محسوب نمی‌شود.
