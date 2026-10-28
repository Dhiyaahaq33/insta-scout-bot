import os
import sys
import time
import json
import argparse
import tempfile
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEFAULT_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
INSTAGRAM_COOKIES = os.getenv("INSTAGRAM_COOKIES", "")

def send_telegram_message(chat_id: str, text: str) -> int:
    """Kirim pesan ke Telegram bot. Mengembalikan message_id jika berhasil."""
    token = TELEGRAM_BOT_TOKEN
    if not token:
        print("[!] TELEGRAM_BOT_TOKEN belum disetel.")
        print(text)
        return 0

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    max_len = 4000
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    last_msg_id = 0

    for chunk in chunks:
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        try:
            res = requests.post(url, json=payload, timeout=15)
            if not res.ok:
                payload["parse_mode"] = ""
                res = requests.post(url, json=payload, timeout=15)
            if res.ok:
                last_msg_id = res.json().get("result", {}).get("message_id", 0)
        except Exception as e:
            print(f"[!] Gagal mengirim pesan ke Telegram: {e}")
    return last_msg_id

def send_progress(chat_id: str, text: str):
    """Kirim pembaruan status progress ke Telegram."""
    if chat_id:
        send_telegram_message(chat_id, f"<i>{text}</i>")

def get_ytdlp_cookie_arg(temp_dir: str):
    """Menyiapkan file cookie jika tersedia di environment."""
    if not INSTAGRAM_COOKIES:
        return []
    cookie_path = os.path.join(temp_dir, "cookies.txt")
    with open(cookie_path, "w", encoding="utf-8") as f:
        f.write(INSTAGRAM_COOKIES)
    return ["--cookies", cookie_path]

def analyze_video_with_gemini(video_path: str, caption: str, uploader: str) -> str:
    """Mengirim video langsung ke Gemini 2.0 Flash untuk ditonton dan dianalisis."""
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY belum disetel. Analisis visual tidak dapat dijalankan."

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)

        print(f"[*] Mengunggah video ke Gemini: {video_path}...")
        video_file = client.files.upload(file=video_path)

        while video_file.state.name == "PROCESSING":
            print("[*] Menunggu Gemini memproses video...")
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)

        prompt = f"""
        Kamu adalah AI Social Media Intelligence Scout. 
        Tonton dan dengarkan video ini dengan teliti.
        
        Metadata Konten:
        - Akun Pengunggah: {uploader}
        - Caption Asli: {caption}
        
        Berikan laporan analisis mendalam dengan format berikut:
        1. 🎵 **Audio / Musik / Lagu**: Identifikasi lagu, tren suara, atau jenis voiceover yang digunakan.
        2. 👀 **Visual Breakdown**: Ceritakan apa yang terlihat di video frame-demi-frame (objek, orang, suasana, teks on-screen).
        3. 🎙️ **Transkrip Ucapan**: Rangkum perkataan orang di dalam video (jika ada pembicaraan).
        4. 💡 **Inti Pesan & Hook**: Analisis hook 3 detik pertama, isi utama, dan ajakan bertindak (CTA).
        5. 🎯 **Kesimpulan & Value**: Apa insight penting atau nilai utama yang ingin disampaikan pembuat konten?
        """

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[video_file, prompt]
        )

        # Bersihkan file dari cloud storage Gemini
        try:
            client.files.delete(name=video_file.name)
        except Exception:
            pass

        return response.text
    except Exception as e:
        print(f"[!] Error saat memproses via Gemini: {e}")
        return f"Gagal menganalisis video via Gemini: {str(e)}"

def process_single_reel(url: str, temp_dir: str) -> dict:
    """Mengunduh dan mengekstrak satu video Reels/Post."""
    cookie_args = get_ytdlp_cookie_arg(temp_dir)
    out_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--no-playlist",
        *cookie_args,
        url
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        return {"error": res.stderr or "Gagal membaca metadata reel"}

    data = json.loads(res.stdout)
    title = data.get("title", "")
    uploader = data.get("uploader", "") or data.get("uploader_id", "")
    caption = data.get("description", "")
    duration = data.get("duration", 0)

    # Download actual file
    download_cmd = [
        sys.executable, "-m", "yt_dlp",
        "-o", out_template,
        "--no-playlist",
        *cookie_args,
        url
    ]
    subprocess.run(download_cmd, check=True)

    # Cari file yang terunduh
    files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith(('.mp4', '.mkv', '.webm'))]
    video_path = files[0] if files else None

    return {
        "url": url,
        "title": title,
        "uploader": uploader,
        "caption": caption,
        "duration": duration,
        "video_path": video_path
    }

def main():
    parser = argparse.ArgumentParser(description="Insta Scout Bot - Autonomous Instagram Scout")
    parser.add_argument("--url", required=True, help="Link Instagram (Reels / Post / Akun)")
    parser.add_argument("--duration", default="15", help="Durasi scouting atau parameter waktu")
    parser.add_argument("--chat-id", default=DEFAULT_CHAT_ID, help="Telegram Chat ID target")
    parser.add_argument("--max-posts", type=int, default=5, help="Jumlah maksimal postingan jika link berupa akun")
    args = parser.parse_args()

    chat_id = args.chat_id or DEFAULT_CHAT_ID
    target_url = args.url.strip()

    print(f"[*] Memulai Insta Scout untuk: {target_url} (Chat ID: {chat_id})")

    if chat_id:
        send_telegram_message(chat_id, f"🔍 <b>Insta Scout Aktif!</b>\nTarget: {target_url}\nDurasi/Batas: {args.duration} menit. Sedang memproses konten...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Cek apakah single post/reel/video atau akun/channel
        is_single = any(k in target_url for k in [
            "/reels/", "/reel/", "/p/", 
            "watch?v=", "youtu.be/", "/shorts/"
        ])
        is_profile = not is_single

        if not is_profile:
            # Mode Single Reel / Video
            send_progress(chat_id, "⏳ <b>[1/3]</b> Mengunduh media & mengekstrak trek audio/video...")
            data = process_single_reel(target_url, temp_dir)
            if "error" in data:
                msg = f"❌ <b>Gagal memproses link:</b> {data['error']}"
                if chat_id: send_telegram_message(chat_id, msg)
                return

            analysis = ""
            if data.get("video_path") and os.path.exists(data["video_path"]):
                send_progress(chat_id, "🧠 <b>[2/3]</b> Gemini 2.0 Flash sedang 'menonton' visual & mendengarkan suara...")
                analysis = analyze_video_with_gemini(data["video_path"], data["caption"], data["uploader"])

            send_progress(chat_id, "📝 <b>[3/3]</b> Menyusun laporan analisis lengkap...")
            report = f"""
🎬 <b>HASIL ANALISIS KONTEN</b>
🔗 <b>URL:</b> {target_url}
👤 <b>Uploader:</b> @{data['uploader']}
⏱️ <b>Durasi:</b> {data['duration']} detik

📝 <b>Caption:</b>
{data['caption'][:300] + ('...' if len(data['caption']) > 300 else '')}

══════════════════════════
{analysis}
══════════════════════════
✅ <i>Scout selesai secara otomatis.</i>
"""
            if chat_id:
                send_telegram_message(chat_id, report)
            else:
                print(report)
        else:
            # Mode Akun / Profil / Channel: Mengambil daftar video teratas
            send_progress(chat_id, f"🔍 <b>[1/3]</b> Mengakses profil/channel: {target_url}...")
            print(f"[*] Mengambil reels terbaru dari akun: {target_url}...")
            cookie_args = get_ytdlp_cookie_arg(temp_dir)
            list_cmd = [
                sys.executable, "-m", "yt_dlp",
                "--flat-playlist",
                "--dump-json",
                f"--playlist-items", f"1:{args.max_posts}",
                *cookie_args,
                target_url
            ]
            res = subprocess.run(list_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            
            reels_urls = []
            for line in res.stdout.strip().split("\n"):
                if not line: continue
                try:
                    entry = json.loads(line)
                    u = entry.get("url") or entry.get("webpage_url")
                    if u and u not in reels_urls:
                        reels_urls.append(u)
                except Exception:
                    continue

            if not reels_urls:
                reels_urls = [target_url]

            target_items = reels_urls[:args.max_posts]
            send_progress(chat_id, f"🎯 <b>[2/3]</b> Terdeteksi {len(target_items)} video terbaru. Mulai scouting satu per satu...")

            reports = []
            for idx, r_url in enumerate(target_items, 1):
                send_progress(chat_id, f"⏳ Sedang memproses konten <b>[{idx}/{len(target_items)}]</b>...")
                item_temp = os.path.join(temp_dir, f"reel_{idx}")
                os.makedirs(item_temp, exist_ok=True)
                item_data = process_single_reel(r_url, item_temp)
                if "error" in item_data:
                    continue

                item_analysis = ""
                if item_data.get("video_path") and os.path.exists(item_data["video_path"]):
                    item_analysis = analyze_video_with_gemini(item_data["video_path"], item_data["caption"], item_data["uploader"])

                item_report = f"""
📹 <b>Konten #{idx}:</b> {r_url}
👤 <b>Uploader:</b> @{item_data['uploader']}
{item_analysis}
──────────────────────────
"""
                reports.append(item_report)
                if chat_id:
                    send_telegram_message(chat_id, item_report)

            summary_msg = f"🏁 <b>Scouting Selesai!</b> Berhasil menganalisis {len(reports)} konten dari {target_url}."
            if chat_id:
                send_telegram_message(chat_id, summary_msg)

if __name__ == "__main__":
    main()
