# OptomMarket Telegram Bot + AI Assistant

Moguta CMS platformasi bilan integratsiyalashgan Telegram bot va Mini App.

## 🚀 Xususiyatlar

- ✅ Mahsulotlarni qidirish (tabiiy tilda)
- ✅ Kategoriyalar bo'yicha ko'rish
- ✅ Buyurtma holatini tekshirish
- ✅ AI yordamchisi (Gemini API)
- ✅ Telegram Mini App (Do'konga o'tish)
- ✅ Admin panel (bilimlar bazasini boshqarish)

## 📋 Talablar

- Python 3.10+
- MySQL (Moguta CMS bazasi)
- Telegram Bot Token
- Google Gemini API Key

## ⚙️ O'rnatish

### 1. Kodni yuklab olish

```bash
git clone https://github.com/your-repo/optommarket-bot.git
cd optommarket-bot
```

### 2. Virtual muhit yaratish

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 4. .env faylini sozlash

```bash
cp .env.example .env
```

`.env` faylini tahrirlang:

```env
# Telegram
BOT_TOKEN=your_bot_token_from_botfather

# Database (Beget MySQL)
DB_HOST=your_host.beget.tech
DB_PORT=3306
DB_NAME=your_moguta_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# AI (Gemini)
GEMINI_API_KEY=your_gemini_api_key

# Moguta CMS
MOGUTA_URL=https://your-moguta-site.uz

# Admin
ADMIN_SECRET_KEY=random_secret_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password
```

### 5. Botni ishga tushirish

```bash
python -m bot.main
```

### 6. Admin panelni ishga tushirish (alohida terminal)

```bash
python -m admin.app
```

Admin panel: http://localhost:5000

## 🐳 Docker bilan ishga tushirish

```bash
# Build va run
docker-compose up -d

# Loglarni ko'rish
docker-compose logs -f bot
```

## 📁 Loyiha strukturasi

```
optommarket-bot/
├── bot/
│   ├── main.py              # Bot entry point
│   ├── config.py            # Sozlamalar
│   ├── handlers/            # Telegram handlerlar
│   │   ├── start.py
│   │   ├── search.py
│   │   ├── order.py
│   │   └── ai_chat.py
│   ├── services/            # Biznes logika
│   │   ├── database.py      # MySQL
│   │   ├── ai_service.py    # Gemini AI
│   │   └── product_service.py
│   └── keyboards/           # Telegram klaviaturalar
│       └── inline.py
├── admin/
│   ├── app.py               # Flask admin
│   ├── templates/
│   └── static/
├── data/
│   └── knowledge_base.json  # AI bilimlar bazasi
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 🔧 Beget Serverga Deploy

### 1. SSH orqali ulanish

```bash
ssh login@your-server.beget.tech
```

### 2. Kodni yuklash

```bash
cd ~/optommarket-bot
git pull origin main
```

### 3. Screen sessiya yaratish

```bash
screen -S optommarket-bot
source venv/bin/activate
python -m bot.main
```

Screen'dan chiqish: `Ctrl+A`, keyin `D`

### 4. Supervisor bilan avtomatik ishga tushirish

`/etc/supervisor/conf.d/optommarket-bot.conf`:

```ini
[program:optommarket-bot]
directory=/home/login/optommarket-bot
command=/home/login/optommarket-bot/venv/bin/python -m bot.main
user=login
autostart=true
autorestart=true
stderr_logfile=/home/login/optommarket-bot/logs/error.log
stdout_logfile=/home/login/optommarket-bot/logs/output.log
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start optommarket-bot
```

## 📊 Moguta CMS jadvallar

Bot quyidagi jadvallardan foydalanadi:

| Jadval | Maqsad |
|--------|--------|
| `mg_product` | Mahsulotlar |
| `mg_category` | Kategoriyalar |
| `mg_order` | Buyurtmalar |
| `mg_order_content` | Buyurtma tarkibi |

> ⚠️ **Xavfsizlik**: Faqat `SELECT` huquqiga ega alohida DB foydalanuvchi yarating.

## 🤖 Bot buyruqlari

- `/start` - Bosh menyu
- `/search` - Mahsulot qidirish
- `/order` - Buyurtma holati
- `/help` - Yordam

## 📝 License

MIT

## 👨‍💻 Muallif

OptomMarket Team
