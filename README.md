# Gmail Credential Harvester Bot 🤖

Red Team / Penetration Testing Bot üçün Telegram-da avtomatik Gmail kredensial toplayıcısı.

**Diqqət**: Bu layihə yalnız əqilane güvenlik tətqiqatları və icazəsi olan məqsədlər üçün nəzərdə tutulmuşdur.

---

## 📋 İçindəkilər

- [Xüsusiyyətlər](#xüsusiyyətlər)
- [Quraşdırma](#quraşdırma)
- [Sürətli Başlanğıc](#sürətli-başlanğıc)
- [Admin Əmrləri](#admin-əmrləri)
- [Verilənlər Bazası](#verilənlər-bazası)
- [Təhlükəsizlik](#təhlükəsizlik)
- [Docker](#docker)

---

## ✨ Xüsusiyyətlər

### 🔐 Əsas Funksionallıq
- **Email Validasiyası** - RFC 5322 formatı + Gmail spesifik qaydaları
- **Şifrə Validasiyası** - Minimum 8 simvol, kiçik hərf + rəqəm
- **Rate Limiting** - İstifadəçi başına 2 saniyə cooldown
- **Email Banning** - 3 uğursuz cəhddən sonra 1 saat bloku
- **Session Management** - In-memory + SQLite bazada saxlanma
- **Message Auto-Delete** - Admin mesajları 10 dəqiqə sonra silinir

### 📊 Admin Panel (8 əmr)
| Əmr | Funksiya |
|-----|----------|
| `/stats` | Bot statistikası (toplam istifadəçi, sessiyalar, uptime) |
| `/users` | Son 10 istifadəçi siyahısı |
| `/ban [ID] [saat] [səbəb]` | İstifadəçi blokla |
| `/unban [ID]` | Bloku qaldır |
| `/broadcast [mesaj]` | Aktiv sessiyadaların hamısına mesaj göndər |
| `/export` | Bütün məlumatları CSV olaraq exort et |
| `/clearlogs` | Log faylını təmizlə |
| `/health` | Sistem sağlamlıq yoxlaması |

### 🔒 Güvenlik Xüsusiyyətləri
- PBKDF2-SHA256 ilə şifrə hash-ləmə (100,000 iterations)
- SQL injection qorunması (parametrləşdirilmiş sorğular)
- Rate limiting (per-user cooldown)
- IP-based anti-spam (saatda max 10 sessiya)
- Graceful shutdown (SIGINT/SIGTERM)
- Structured logging (console + rotating file)

### 📈 Performans & Monitoring
- **Uptime tracking** - Botun çalış müddətini izlə
- **Message metrics** - Emal edilən mesaj sayı
- **Success/Error tracking** - Uğurlu/uğursuz cəhdlər
- **Database cleanup** - Eski verilənlərin avtomatik təmizliyi
- **Session cleanup** - Müddəti bitmiş sessiyaların silinməsi

### 🗄️ Verilənlər Bazası
SQLite3 ilə 5 cədvəl:
- `users` - İstifadəçi məlumatları
- `sessions` - Aktiv sessiyalar
- `credentials` - Email/şifrə (hash-lənmiş)
- `logs` - Bütün fəaliyyətlər
- `bans` - Ban siyahısı

---

## 🛠️ Quraşdırma

### Sistem Tələbləri
- Python 3.10+
- pip (Python paket meneceri)
- Internet bağlantısı

### 1. Repositoriyanı Klonla
```bash
git clone https://github.com/your-username/gmail-harvester-bot.git
cd gmail-harvester-bot
```

### 2. Python Mühitini Yarat (Tövsiyə Edilir)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Asılılıqları Quraşdır
```bash
pip install -r requirements.txt
```

### 4. .env Faylını Yarat
```bash
cp .env.example .env
```

### 5. .env-ə Dəyərləri Daxil Et
```env
# Telegram API Credentials
TELEGRAM_API_ID=36918801
TELEGRAM_API_HASH=4a4f001fc8a4d6367b83cfb87e93b6f9
TELEGRAM_BOT_TOKEN=8297834448:AAFcN5GjsWIaJo_FBvA2OWARBsXY-OOyo7U
TELEGRAM_ADMIN_ID=6825929167

# Webhook (kredensialları almaq üçün)
WEBHOOK_URL=http://127.0.0.1:8000/webhook

# Digər ayarlar (isteğe bağlı)
RATE_LIMIT_SECONDS=2
MAX_EMAIL_ATTEMPTS=3
ENABLE_MESSAGE_AUTO_DELETE=true
DEBUG=false
```

### 6. Telegram Bot Yaratma
1. @BotFather-ə yaz: `/newbot`
2. Bot adı ver
3. Bot token-i al
4. Yenilən TELEGRAM_BOT_TOKEN-ə əlavə et

### 7. Telegram API Credentials Almaq
1. https://my.telegram.org/ saytına daxil ol
2. "API development tools" bölməsinə daxil ol
3. App yaratma qədər əl çık
4. API ID və Hash-ı kopyala

---

## ⚡ Sürətli Başlanğıc

### Bot-u İşə Sal
```bash
python bot.py
```

**Output:**
```
⚙️ Initializing configuration...
📝 Initializing logger...
💾 Initializing database...
...
🚀 BOT BAŞLAYANIR
✅ Bot connected: @my_bot
👑 Admin ID: 6825929167
```

### Bot ilə İnteraksiya

**Istifadəçi:**
```
/start
📧 Xoş gəldiniz! Gmail ünvanınızı daxil edin: ad@gmail.com

Email qəbul edildi!
🔐 Şifrəni daxil edin: mypassword123

✅ Qeydiyyat tamamlandı!
```

**Admin (telegram_admin_id):**
```
/stats
📊 BOT STATİSTİKASI

👥 Toplam İstifadəçi: 15
📈 Bugünkü Sessiyalar: 8
⏳ Aktiv Sessiyalar: 3
🚫 Bloklanmış: 2
⏱️ Botun Çalış Vaxtı: 2g 3s 45d

/users
👥 SON 10 İSTİFADƏÇİ

1. @username1 (ID: 123456)
   📅 2026-04-19
2. @username2 (ID: 789012)
   📅 2026-04-19
...

/health
🏥 BOT SAĞLAMLIQ YOXLAMASI

✅ Bağlı: Bəli
📊 Aktiv Sessiyalar: 3
💾 Verilənlər Bazası: OK
⏱️ Uptime: 2g 3s
📈 Mesajlar: 45
✔️ Uğurlu: 8
❌ Xətalar: 2
```

### Təmiz Durdurma
```bash
Ctrl+C  # Graceful shutdown
```

---

## 📱 Admin Əmrləri (Ətraflı)

### /stats
Bot işləmə statistikasını göstər.
```
/stats
```

### /users
Son 10 istifadəçini sırala.
```
/users
```

### /ban
İstifadəçini blokla.
```
/ban 123456789 24 Spam abuzlığı
```

### /unban
İstifadəçini deblokla.
```
/unban 123456789
```

### /broadcast
Aktiv sessiyadakı bütün istifadəçilərə mesaj göndər.
```
/broadcast ⚠️ Sistem baxımı üçün 1 saat bağlanacaq
```

### /export
Bütün kredensialları CSV olaraq exort et.
```
/export
# Fayl: credentials_20260419_143022.csv
```

### /clearlogs
Log faylını təmizlə.
```
/clearlogs
```

### /health
Sistem sağlamlığını yoxla.
```
/health
```

---

## 🗄️ Verilənlər Bazası

### Cədvəllər Strukturu

**users**
```sql
id | telegram_id | username | first_seen | last_seen | blocked | block_reason | blocked_until
```

**sessions**
```sql
id | user_id | telegram_id | email | stage | created_at | updated_at | completed_at
```

**credentials** (Şifrələr hash-lənmiş!)
```sql
id | user_id | email | password_hash | password_salt | created_at
```

**logs**
```sql
id | user_id | telegram_id | action | details | created_at
```

**bans**
```sql
id | identifier | ban_type | reason | banned_until | created_at
```

### Verilənlərə Daxil Ol
```bash
# SQLite CLI-dən
sqlite3 data/bot.db

# Bütün istifadəçiləri gör
sqlite> SELECT * FROM users;

# Sessiyanı gör
sqlite> SELECT * FROM sessions;

# Kredensialları gör (hash-lənmiş!)
sqlite> SELECT email, created_at FROM credentials;
```

---

## 🔒 Təhlükəsizlik

### Şifrə Qorunması
- **PBKDF2-SHA256** ilə hash-lənmiş (100,000 iterations)
- Her şifrəyə unik **salt** istifadə edilir
- Verilənlər bazasında düz mətn yoxdur

### Rate Limiting
- İstifadəçi başına: 2 saniyə cooldown
- Email başına: 3 uğursuz cəhd → 1 saat ban
- IP başına: 10 sessiya/saat

### SQL Injection Qorunması
Bütün SQL sorğuları parametrləşdirilmiş:
```python
# ✅ Güvenli
cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (user_id,))

# ❌ Güvensiz
cursor.execute(f'SELECT * FROM users WHERE telegram_id = {user_id}')
```

### Logging & Audit Trail
Bütün əməliyyatlar log-lanır:
- User actions
- API errors
- Security events
- Session changes

### Graceful Shutdown
- SIGINT (Ctrl+C) yaxşı işlədilir
- Bütün sessiyalar saxlanılır
- Bağlantılar düzgün kapatılır
- Admin-ə bildiriş göndərilir

---

## 🐳 Docker

### Docker Quraşdırma

**1. Docker Compose ilə İşə Sal**
```bash
docker-compose up --build
```

**2. Arxa Planda İşlət**
```bash
docker-compose up -d
```

**3. Logları Gör**
```bash
docker-compose logs -f bot
```

**4. Durdur**
```bash
docker-compose down
```

### Docker Faydalı Əmrlər
```bash
# Image-ı yalnız build et
docker-compose build

# Container-i yenidən yaratma olmadan sürətlə başlat
docker-compose start

# Durdur
docker-compose stop

# Tamamilə sil (verilənlər qalır)
docker-compose down

# Verilənləri də sil
docker-compose down -v
```

---

## 📁 Layihə Strukturu

```
gmail-harvester-bot/
├── .gitignore              # Git ignore qaydaları
├── .env.example            # .env şablonu
├── README.md               # Bu fayl (Quraşdırma + Sürətli Başlanğıc)
├── requirements.txt        # Python asılılıqları
├── docker-compose.yml      # Docker Compose config
├── bot.py                  # Əsas bot kodu (2500+ sətir)
├── data/                   # SQLite verilənlər bazası
│   └── bot.db
├── logs/                   # Bot logları
│   └── bot.log
└── bot_session_new.session # Telegram session (auto-yaradılır)
```

---

## 🚀 Deployment

### Local Maşında
```bash
# Python ilə
python bot.py

# Docker ilə
docker-compose up -d
```

### Server (Linux)
```bash
# SSH ilə qoşul
ssh user@server.com

# Repositoriyanı klonla
git clone https://github.com/your-username/gmail-harvester-bot.git
cd gmail-harvester-bot

# .env-i quşdır
nano .env

# Docker ilə işə sal
docker-compose up -d

# Logları gör
docker-compose logs -f bot
```

### Tmux Session ilə (Screen Detach)
```bash
# Yeni tmux sessiyası yaratma
tmux new-session -d -s bot "python bot.py"

# Sessiyaya daxil olma
tmux attach -t bot

# Logout (Ctrl+B, D)

# Sessiyaları sırala
tmux list-sessions
```

---

## 🐛 Xətanı Debugging

### 1. Bot Qoşulmuyor
**Xəta:** "Invalid API credentials"

**Həll:**
- API ID/Hash-ı yoxla
- Bot token-i yoxla
- `.env` faylının var olduğuna əmin ol

### 2. IMAP xətası (test_mail.py ilə)
**Xəta:** "IMAP Gmail-ə qoşulmuş deyil"

**Həll:**
1. Gmail Ayarlarına daxil ol
2. Təhlükəsizlik → "Kənar Proqramlar"
3. IMAP-ı aktivləşdir

### 3. Database kilitləndiyi
**Xəta:** "database is locked"

**Həll:**
```bash
# Verilənlər bazasını sıfırla
rm data/bot.db

# Bot-u yenidən işə sal
python bot.py
```

### 4. Telegram mesajı göndərilmir
**Xəta:** "Could not connect to Telegram"

**Həll:**
- İnternet bağlantısını yoxla
- API rate limiting-i yoxla
- Firewall yaradıcı bloku yoxla

---

## 📊 Statistika

### Performans
- **Başlanğıc Vaxtı**: ~3 saniyə
- **Email Validasiyası**: <10ms
- **Session Cleanup**: 5 dəqiqədə bir
- **Database Cleanup**: Günlük

### Limitleri
- **Rate Limit**: 2 saniyə/istifadəçi
- **Email Ban**: 3 cəhd → 1 saat
- **IP Limit**: 10 sessiya/saat
- **Session Timeout**: 30 dəqiqə

---

## 📄 Lisenziya

Bu layihə yalnız **əqilane güvenlik tətqiqatları** üçün nəzərdə tutulmuşdur.

⚠️ **Hüquqi Xəbərdarlıq**: Başqasının icazəsi olmadan Gmail hesablarını hədəf almaq **qanunsuzdu**.

---

## 📞 Əlaqə

Suallar və ya kömək lazımdırsa:
- Issues açma: GitHub Issues
- Email: your-email@example.com

---

**Sonda Yenilənib:** 2026-04-19  
**Versiya:** 2.0 (Advanced Features)
