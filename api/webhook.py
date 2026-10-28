import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GITHUB_PAT = os.environ.get("GITHUB_PAT", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "Dhiyaahaq33/insta-scout-bot")

def send_telegram(chat_id, text):
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print("Telegram error:", e)

def trigger_github_action(target_url, duration, chat_id):
    if not GITHUB_PAT:
        return False, "GITHUB_PAT belum disetel di environment Vercel."
    
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/scout.yml/dispatches"
    payload = json.dumps({
        "ref": "main",
        "inputs": {
            "target_url": target_url,
            "duration_minutes": str(duration),
            "chat_id": str(chat_id)
        }
    }).encode("utf-8")

    req = urllib.request.Request(api_url, data=payload, headers={
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "InstaScoutBot-Webhook",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "Triggered successfully"
    except Exception as e:
        return False, str(e)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            update = json.loads(post_data.decode("utf-8"))
            message = update.get("message", {})
            text = message.get("text", "").strip()
            chat_id = message.get("chat", {}).get("id")

            if not text or not chat_id:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
                return

            if text.startswith("/start"):
                welcome_msg = (
                    "👋 <b>Halo! Saya Scout Bot (Multi-Platform).</b>\n\n"
                    "Kirimkan link yang ingin Anda riset/tonton:\n"
                    "• <b>Instagram:</b> <code>https://www.instagram.com/reels/DdJbTkTMfxB/</code>\n"
                    "• <b>YouTube:</b> <code>https://youtube.com/shorts/XXXXX</code> atau video panjang\n"
                    "• <b>Akun/Channel:</b> <code>https://youtube.com/@channel durasi: 15m</code>\n\n"
                    "Saya akan otomatis menonton, membaca visual, caption, dan musiknya lalu mengirimkan laporannya ke sini."
                )
                send_telegram(chat_id, welcome_msg)
            elif any(domain in text for domain in ["instagram.com", "youtube.com", "youtu.be", "tiktok.com"]):
                # Extract URL and optional duration
                parts = text.split()
                target_url = parts[0]
                duration = "15"
                for p in parts[1:]:
                    if "durasi:" in p or "m" in p:
                        duration = p.replace("durasi:", "").replace("m", "").replace("menit", "").strip()

                send_telegram(
                    chat_id, 
                    f"🚀 <b>Instruksi Diterima!</b>\nTarget: {target_url}\nDurasi/Batas: {duration} menit.\n\n"
                    f"<i>Runner GitHub Actions sedang dijalankan di cloud. Hasil analisis akan otomatis dikirimkan ke chat ini...</i>"
                )

                ok, reason = trigger_github_action(target_url, duration, chat_id)
                if not ok:
                    send_telegram(chat_id, f"⚠️ <b>Gagal memicu runner:</b> {reason}")
            else:
                send_telegram(chat_id, "Kirimkan link yang valid dari Instagram atau YouTube (Video, Shorts, atau Channel).")

        except Exception as e:
            print("Webhook error:", e)

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Insta Scout Telegram Webhook is running active!")
