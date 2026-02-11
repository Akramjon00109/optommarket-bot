# OptomMarket Bot/AI Loyihasini Noldan Yaratish Prompti

**Ahamiyati:** Bu prompt AI yordamchisiga (yoki dasturchiga) loyihaning to'liq arxitekturasi va funksionalini tushuntirib, uni qaytadan yozish yoki shunga o'xshash loyiha qurish uchun ishlatiladi.

---

## 🔥 Loyiha Vazifasi (System Prompt)

**Loyiha Nomi:** OptomMarket AI Bot (Telegram & Instagram & Web)
**Maqsad:** Moguta CMS (MySQL) ma'lumotlar bazasi bilan ishlaydigan, va bir vaqtning o'zida mijozlarga Telegram Bot va Instagram Direct orqali xizmat ko'rsatadigan AI-yordamchi yaratish.

### 🛠 Texnologik Stek (Tech Stack)
- **Til:** Python 3.11+
- **Framework (Telegram):** `aiogram 3.x` (asinxron)
- **Framework (Web/Instagram):** `aiohttp` (Webhook server uchun)
- **Ma'lumotlar Bazasi:** `MySQL` (Moguta CMS ning asosiy bazasi, `aiomysql` orqali ulanish)
- **AI (Sun'iy Intellekt):** Google Gemini 1.5 Flash (yoki OpenAI GPT-4o)
- **Deployment:** Render.com (Docker orqali)
- **Qo'shimcha:** `loguru` (logging), `python-dotenv` (config), `schedule` (cron jobs)

---

### 🚀 Asosiy Funksionallik

#### 1. Telegram Bot (Mijozlar Uchun)
- **/start:** Ro'yxatdan o'tish (Telefon raqam so'rash va bazaga saqlash).
- **Qidiruv (/search):** 
  - Foydalanuvchi matn yozadi (masalan, "Samsung TV").
  - Bot `s_products` jadvalidan `LIKE` orqali qidiradi.
  - Agar topilmasa, AI javob beradi.
  - Natijalar: Rasm, Narx, Kategoriya, va "Sotib olish" (Web App) tugmasi.
  - **Pagination:** Natijalar ko'p bo'lsa (5+), "Keyingi" va "Oldingi" tugmalari bo'lishi shart.
- **Kategoriyalar:** 
  - `s_categories` jadvalidan daraxt (Tree) shaklida kategoriyalarni chiqarish.
  - Sub-kategoriyalar va oxirida mahsulotlar ro'yxati (Pagination bilan).
  - "Orqaga" tugmasi ota-ona kategoriyasiga qaytishi kerak.
- **Buyurtma Holati (/order):**
  - Foydalanuvchi buyurtma ID sini yozadi.
  - Bot `s_orders` va `s_order_status` jadvallaridan ma'lumot olib, holatni (Yangi, Yetkazildi, Bekor qilindi) ko'rsatadi.
- **AI Chat:**
  - Oddiy so'zlashuv (Salomlashish, Do'kon haqida ma'lumot).
  - Mahsulot tavsiyasi (Kontekstli qidiruv).

#### 2. Instagram Integratsiyasi (Direct & Comments)
- **Webhook Server:** `aiohttp` ko'tarish va `/webhook` endpointini ochish.
- **Meta Graph API:** Instagram Page Access Token orqali ishlash.
- **Direct Messages:**
  - Foydalanuvchi yozganda webhook orqali xabar keladi.
  - Bot xabarni AI ga junatadi.
  - AI javobini Instagramga qaytaradi ("Human Agent" tag bilan).
- **Comments/Mentions:**
  - Izoh yoki belgilash bo'lganda, avtomatik "Directga yozildi" deb javob berish va Directga o'tib savolga javob berish.

#### 3. Admin Panel (Bot ichida)
- **/broadcast:** Barcha foydalanuvchilarga reklama yoki yangilik yuborish (Rasm/Video/Matn).
- **/stats:** Foydalanuvchilar soni statistikasi.
- **Loglarni olish:** `bot_*.log` faylini yuklab olish.
- **Katalog Sinxronizatsiyasi:** Facebook Catalog (Commerce Manager) ga mahsulotlarni yuklash (XML feed yoki API orqali).

---

### 🗄 Ma'lumotlar Bazasi Tuzilishi (Moguta CMS - MySQL)

Biz faqat **O'QISH** (Read-Only) rejimida quyidagi jadvallarni ishlatamiz:
1. **s_products:** `id`, `title`, `price`, `old_price`, `image_url`, `short_description`, `url` (slug), `activity=1`.
2. **s_categories:** `id`, `title`, `parent`, `url`.
3. **s_orders:** `id`, `user_email` (yoki phone), `status_id`, `delivery_cost`, `total_price`.
4.  **s_order_status:** `id`, `status_name` (Masalan: 1=Yangi, 2=Yopilgan).

---

### 📂 Loyiha Strukturasi

```text
optommarket-bot/
├── bot/
│   ├── handlers/        # (start, search, order, categories, admin, ai_chat)
│   ├── keyboards/       # (inline va reply tugmalar)
│   ├── services/        # (database, ai_service, instagram_service, product_service)
│   ├── middlewares/     # (Xatolarni ushlash, log qilish)
│   └── main.py          # (Bot va Webhookni ishga tushirish)
├── data/                # (mahalliy JSON fayllar, users.json)
├── logs/                # (log fayllar)
├── .env                 # (Tokenlar va DB login parollar)
├── Dockerfile           # (Deploy uchun)
└── requirements.txt     # (Kutubxonalar)
```
