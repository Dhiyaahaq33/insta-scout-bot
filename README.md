# 👁️ Insta Scout Bot (100% Serverless & Zero-VPS)

Bot riset dan pengamat konten Instagram otonom bertenaga AI Multimodal (**Google Gemini 2.0 Flash**). 

Bekerja secara **Serverless (Tanpa VPS)** menggunakan kombinasi:
1. **Telegram Bot** sebagai antarmuka chat di ponsel/desktop.
2. **Vercel Serverless Function** sebagai penerima Webhook (respons instan 1 detik).
3. **GitHub Actions Runner** sebagai mesin penjelajah & downloader (gratis 2.000 menit/bulan, tanpa batas timeout 60 detik Vercel).
4. **Google Gemini Multimodal API** sebagai otak visual & audio untuk "menonton" dan "mendengarkan" konten.

---

## 🚀 Alur Kerja

```
[Anda di Telegram] 
       │ (Kirim link Reels atau Profil akun)
       ▼
[Vercel Webhook] 
       │ (Terima pesan instan & pemicu)
       ▼
[GitHub Actions Runner (Ubuntu)]
       │ (Download media, ekstrak frame & audio)
       ▼
[Google Gemini 2.0 Flash API]
       │ (AI 'menonton' visual, musik, transkrip teks & hook)
       ▼
[Telegram Chat Anda] (Laporan riset rapi terkirim otomatis!)
```

---

## 🛠️ Setup & Konfigurasi Cepat

### 1. Masukkan Secrets ke GitHub Repository
Di GitHub repo ini: Buka **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**:

* `GEMINI_API_KEY`: Kunci API Gemini dari [Google AI Studio](https://aistudio.google.com/).
* `TELEGRAM_BOT_TOKEN`: Token dari `@BotFather`.
* `TELEGRAM_CHAT_ID`: ID angka Telegram Anda dari `@userinfobot`.
* `INSTAGRAM_COOKIES` *(Opsional)*: String cookie jika akun target terproteksi ketat.

---

### 2. Deploy Webhook ke Vercel (1-Click)
1. Buka [Vercel](https://vercel.com/) ➔ **Add New Project** ➔ Import repositori `insta-scout-bot`.
2. Tambahkan Environment Variables di Vercel:
   * `TELEGRAM_BOT_TOKEN`: Token bot Anda.
   * `GITHUB_PAT`: Personal Access Token GitHub dengan izin `repo` dan `workflow`.
   * `GITHUB_REPO`: `Dhiyaahaq33/insta-scout-bot`
3. Klik **Deploy**.

---

### 3. Pasang Webhook ke Telegram
Setelah Vercel selesai deploy (misal URL: `https://insta-scout-bot.vercel.app`), jalankan perintah ini di browser atau terminal:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<DOMAIN-VERCEL-ANDA>/api/webhook"
```

---

## 📱 Cara Pakai

Cukup buka chat bot Telegram Anda dan kirim:
* `https://www.instagram.com/reels/DdJbTkTMfxB/`
* `https://www.instagram.com/nama_akun/ durasi: 15 menit`

Bot akan langsung merespons dan mengirimkan laporan lengkapnya ke Telegram!
