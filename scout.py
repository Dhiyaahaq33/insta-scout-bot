import os
import re
import sys
import time
import html
import json
import argparse
import tempfile
import subprocess
import requests
import urllib.request
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEFAULT_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
INSTAGRAM_COOKIES = os.getenv("INSTAGRAM_COOKIES", "")
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES", "")

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

def get_ytdlp_cookie_arg(url: str, temp_dir: str):
    """Menyiapkan file cookie sesuai platform jika tersedia di environment."""
    raw_cookies = ""
    if ("instagram.com" in url or "/p/" in url or "/reel/" in url) and INSTAGRAM_COOKIES:
        raw_cookies = INSTAGRAM_COOKIES
    elif ("youtube.com" in url or "youtu.be" in url) and YOUTUBE_COOKIES:
        raw_cookies = YOUTUBE_COOKIES
    elif INSTAGRAM_COOKIES:
        raw_cookies = INSTAGRAM_COOKIES

    if not raw_cookies:
        return []

    cookie_path = os.path.join(temp_dir, "cookies.txt")
    with open(cookie_path, "w", encoding="utf-8") as f:
        f.write(raw_cookies)
    return ["--cookies", cookie_path]

def get_youtube_extra_args(url: str):
    """Parameter khusus YouTube untuk melewati bot detection di cloud runner."""
    if "youtube.com" in url or "youtu.be" in url:
        return [
            "--extractor-args", "youtube:player_client=mweb,android",
            "--user-agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
        ]
    return []

def analyze_media_with_gemini(media_path: str, caption: str, uploader: str, is_video: bool = True) -> str:
    """Mengirim media (video/foto) ke Gemini untuk ditonton/dilihat."""
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY belum disetel. Analisis AI tidak dapat dijalankan."

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)

        print(f"[*] Mengunggah media ke Gemini: {media_path}...")
        media_file = client.files.upload(file=media_path)

        while media_file.state.name == "PROCESSING":
            print("[*] Menunggu Gemini memproses media...")
            time.sleep(2)
            media_file = client.files.get(name=media_file.name)

        if is_video:
            prompt = f"""
            Kamu adalah AI Executive Content Intelligence Scout.
            Tonton dan dengarkan video ini dengan teliti.

            Metadata Konten:
            - Akun Pengunggah: {uploader}
            - Caption Asli: {caption}

            Buat output dengan aturan berikut:
            1. BAGIAN [INTI]:
               Ceritakan alur cerita dan isi video ini dengan gaya **STORYTELLING yang mengalir, hidup, dan mendalam (deeply informative & non-generik)**.
               - Jelaskan latar belakang dan konteks apa yang sedang terjadi.
               - Ceritakan bagaimana narasi atau kejadian di video bergulir (apa masalahnya, emosi/suasananya, dan aksi tokohnya).
               - Jelaskan poin-poin penting, data, atau pesan moral/bisnis yang disampaikan tanpa terkesan kaku atau seperti robot.
            
            2. BAGIAN [DETAIL]:
               Berikan rincian singkat poin-poin pelengkap:
               👀 **Visual & Data:** (Adegan penting, data/angka, teks di layar)
               🎙️ **Ucapan Kunci:** (Kutipan kalimat paling berbobot dari pembicara)
               🎵 **Musik / Suara:** (Lagu, instrumen, atau jenis nada suara)
               🎯 **Hook & CTA:** (Kalimat pembuka & ajakan bertindak)

            Format output harus persis seperti ini:
            [INTI]
            (Tulis narasi storytelling yang informatif dan seru di sini)
            [/INTI]

            [DETAIL]
            👀 **Visual & Data:** ...
            🎙️ **Ucapan Kunci:** ...
            🎵 **Musik / Suara:** ...
            🎯 **Hook & CTA:** ...
            [/DETAIL]
            """
        else:
            prompt = f"""
            Kamu adalah AI Executive Content Intelligence Scout.
            Lihat dan analisis gambar/foto postingan ini dengan teliti.

            Metadata Konten:
            - Akun Pengunggah: {uploader}
            - Caption Asli: {caption}

            Buat output dengan aturan berikut:
            1. BAGIAN [INTI]:
               Ceritakan konteks dan pesan postingan ini dengan gaya **STORYTELLING yang informatif dan mengalir**.
               - Jelaskan apa momen/acara yang diumumkan atau dipamerkan.
               - Ceritakan makna atau signifikansi di balik foto/poster ini bagi audiens.
            
            2. BAGIAN [DETAIL]:
               📝 **Teks pada Gambar (OCR):** (Semua tulisan dan logo yang teridentifikasi)
               👀 **Desain & Visual:** (Elemen visual, layout, suasana)
               🎯 **Pesan & CTA:** (Ajakan dan tujuan)

            Format output harus persis seperti ini:
            [INTI]
            (Tulis narasi storytelling yang informatif di sini)
            [/INTI]

            [DETAIL]
            📝 **Teks pada Gambar (OCR):** ...
            👀 **Desain & Visual:** ...
            🎯 **Pesan & CTA:** ...
            [/DETAIL]
            """

        # Ambil daftar model yang didukung secara dinamis dari API akun pengguna
        candidate_models = []
        try:
            for m in client.models.list():
                m_name = m.name.replace("models/", "")
                methods = getattr(m, "supported_generation_methods", []) or getattr(m, "supported_actions", [])
                if "generateContent" in methods or not methods:
                    if "flash" in m_name.lower():
                        candidate_models.append(m_name)
        except Exception as e:
            print(f"[*] Tidak dapat me-list model otomatis: {e}")

        # Fallback list jika list dinamis kosong
        if not candidate_models:
            candidate_models = [
                "gemini-2.5-flash",
                "gemini-1.5-flash",
                "gemini-1.5-flash-latest",
                "gemini-3.8-flash",
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro-latest"
            ]

        last_error = None
        response_text = None

        for model_name in candidate_models:
            try:
                print(f"[*] Mencoba analisis dengan model: {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[media_file, prompt]
                )
                response_text = response.text
                break
            except Exception as me:
                last_error = me
                print(f"[!] Model {model_name} gagal/sibuk ({me}), mencoba model berikutnya...")
                time.sleep(1)
                continue

        # Bersihkan file dari cloud storage Gemini
        try:
            client.files.delete(name=media_file.name)
        except Exception:
            pass

        if response_text:
            return response_text
        return f"Gagal menganalisis via Gemini: {last_error}"

    except Exception as e:
        print(f"[!] Error saat memproses via Gemini: {e}")
        return f"Gagal memproses media via Gemini: {str(e)}"

def extract_instagram_photo(url: str, temp_dir: str) -> dict:
    """Ekstraksi postingan foto / carousel Instagram menggunakan Facebook metadata bot."""
    print(f"[*] Mengekstrak foto Instagram dari: {url}...")
    headers = {
        "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        "Accept-Language": "en-US,en;q=0.9"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            img_match = re.search(r'<meta property="og:image" content="([^"]+)"', content)
            desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', content)
            title_match = re.search(r'<meta property="og:title" content="([^"]+)"', content)

            if not img_match:
                return {"error": "Tidak dapat menemukan gambar di postingan ini"}

            img_url = html.unescape(img_match.group(1))
            desc_text = html.unescape(desc_match.group(1)) if desc_match else ""
            title_text = html.unescape(title_match.group(1)) if title_match else ""

            # Download gambar
            img_path = os.path.join(temp_dir, "post_photo.jpg")
            img_req = urllib.request.Request(img_url, headers=headers)
            with urllib.request.urlopen(img_req, timeout=15) as img_resp:
                with open(img_path, "wb") as f:
                    f.write(img_resp.read())

            uploader = "Instagram User"
            if "on Instagram" in title_text:
                uploader = title_text.split(" on Instagram")[0].strip()

            return {
                "url": url,
                "title": title_text,
                "uploader": uploader,
                "caption": desc_text,
                "duration": 0,
                "media_path": img_path,
                "is_video": False
            }
    except Exception as e:
        return {"error": f"Gagal membaca foto Instagram: {e}"}

def process_single_media(url: str, temp_dir: str) -> dict:
    """Mengunduh video atau foto, baik dari Instagram maupun YouTube."""
    cookie_args = get_ytdlp_cookie_arg(url, temp_dir)
    yt_args = get_youtube_extra_args(url)
    out_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--no-playlist",
        *cookie_args,
        *yt_args,
        url
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    # Jika yt-dlp error dan ini adalah Instagram post (misal: "There is no video in this post")
    if res.returncode != 0:
        err_msg = res.stderr or ""
        if "instagram.com" in url and ("no video in this post" in err_msg.lower() or "/p/" in url):
            print("[*] Terdeteksi postingan foto Instagram, beralih ke photo extractor...")
            return extract_instagram_photo(url, temp_dir)
        return {"error": err_msg or "Gagal membaca metadata media"}

    try:
        data = json.loads(res.stdout)
    except Exception:
        # Jika yt-dlp output json gagal diurai
        if "instagram.com" in url:
            return extract_instagram_photo(url, temp_dir)
        return {"error": "Format JSON media tidak valid"}

    title = data.get("title", "")
    uploader = data.get("uploader", "") or data.get("uploader_id", "")
    caption = data.get("description", "")
    duration = data.get("duration", 0)

    # Unduh media
    download_cmd = [
        sys.executable, "-m", "yt_dlp",
        "-o", out_template,
        "--no-playlist",
        *cookie_args,
        *yt_args,
        url
    ]
    down_res = subprocess.run(download_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    # Cari file yang terunduh
    files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith(('.mp4', '.mkv', '.webm', '.jpg', '.png'))]
    if not files and "instagram.com" in url:
        return extract_instagram_photo(url, temp_dir)

    media_path = files[0] if files else None

    return {
        "url": url,
        "title": title,
        "uploader": uploader,
        "caption": caption,
        "duration": duration,
        "media_path": media_path,
        "is_video": True
    }

def main():
    parser = argparse.ArgumentParser(description="Insta & YouTube Scout Bot")
    parser.add_argument("--url", required=True, help="Link target (Reels / Post / Video / Channel)")
    parser.add_argument("--duration", default="15", help="Durasi scouting atau parameter batas")
    parser.add_argument("--chat-id", default=DEFAULT_CHAT_ID, help="Telegram Chat ID target")
    parser.add_argument("--max-posts", type=int, default=5, help="Jumlah maksimal postingan jika link berupa akun")
    args = parser.parse_args()

    chat_id = args.chat_id or DEFAULT_CHAT_ID
    target_url = args.url.strip()

    print(f"[*] Memulai Scout untuk: {target_url} (Chat ID: {chat_id})")

    if chat_id:
        send_telegram_message(chat_id, f"🔍 <b>Scout Bot Aktif!</b>\nTarget: {target_url}\nDurasi/Batas: {args.duration} menit. Sedang memproses konten...")

    with tempfile.TemporaryDirectory() as temp_dir:
        is_single = any(k in target_url for k in [
            "/reels/", "/reel/", "/p/",
            "watch?v=", "youtu.be/", "/shorts/",
            "vt.tiktok.com", "/video/", "tiktok.com/@"
        ])
        is_profile = not is_single and not ("vt.tiktok.com" in target_url or "/video/" in target_url)

        if not is_profile:
            # Mode Single Media (Video / Foto)
            send_progress(chat_id, "⏳ <b>[1/3]</b> Mengunduh media & mengekstrak konten...")
            data = process_single_media(target_url, temp_dir)
            if "error" in data:
                msg = f"❌ <b>Gagal memproses link:</b> {data['error']}"
                if chat_id: send_telegram_message(chat_id, msg)
                return

            analysis = ""
            media_path = data.get("media_path")
            is_video = data.get("is_video", True)

            if media_path and os.path.exists(media_path):
                label_tipe = "video & mendengarkan suara" if is_video else "foto & membaca tulisan"
                send_progress(chat_id, f"🧠 <b>[2/3]</b> Gemini AI sedang menganalisis {label_tipe}...")
                analysis = analyze_media_with_gemini(media_path, data["caption"], data["uploader"], is_video=is_video)

            send_progress(chat_id, "📝 <b>[3/3]</b> Menyusun laporan analisis lengkap...")
            tipe_konten = "VIDEO / REELS" if is_video else "FOTO / POSTINGAN"
            dur_text = f" • ⏱️ {data.get('duration')}s" if data.get('duration') else ""
            clean_caption = data.get('caption', '').strip().replace("\n", " ")
            if len(clean_caption) > 160:
                clean_caption = clean_caption[:160] + "..."

            # Parsing [INTI] dan [DETAIL] agar hanya pesan ringkas yang muncul di awal
            inti_text = analysis
            detail_text = ""
            if "[INTI]" in analysis and "[/INTI]" in analysis:
                inti_text = analysis.split("[INTI]")[1].split("[/INTI]")[0].strip()
            if "[DETAIL]" in analysis and "[/DETAIL]" in analysis:
                detail_text = analysis.split("[DETAIL]")[1].split("[/DETAIL]")[0].strip()

            collapsible_detail = ""
            if detail_text:
                collapsible_detail = f"\n<blockquote expandable>🔍 <b>RINCIAN LEBIH LANJUT (Tap untuk Buka/Tutup)</b>\n\n{detail_text}</blockquote>"

            report = f"""🎬 <b>ISI KONTEN: {tipe_konten}</b>
👤 <b>Akun:</b> @{data['uploader']}{dur_text}
🔗 <a href="{target_url}">Tonton Asli</a>

💡 <b>Intinya:</b>
{inti_text}
{collapsible_detail}"""
            if chat_id:
                send_telegram_message(chat_id, report)
            else:
                print(report)
        else:
            # Mode Akun / Channel
            send_progress(chat_id, f"🔍 <b>[1/3]</b> Mengakses profil/channel: {target_url}...")
            cookie_args = get_ytdlp_cookie_arg(url, temp_dir)
            yt_args = get_youtube_extra_args(target_url)
            list_cmd = [
                sys.executable, "-m", "yt_dlp",
                "--flat-playlist",
                "--dump-json",
                f"--playlist-items", f"1:{args.max_posts}",
                *cookie_args,
                *yt_args,
                target_url
            ]
            res = subprocess.run(list_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

            urls = []
            for line in res.stdout.strip().split("\n"):
                if not line: continue
                try:
                    entry = json.loads(line)
                    u = entry.get("url") or entry.get("webpage_url")
                    if u and u not in urls:
                        urls.append(u)
                except Exception:
                    continue

            if not urls:
                urls = [target_url]

            target_items = urls[:args.max_posts]
            send_progress(chat_id, f"🎯 <b>[2/3]</b> Terdeteksi {len(target_items)} konten terbaru. Mulai scouting satu per satu...")

            reports = []
            for idx, r_url in enumerate(target_items, 1):
                send_progress(chat_id, f"⏳ Sedang memproses konten <b>[{idx}/{len(target_items)}]</b>...")
                item_temp = os.path.join(temp_dir, f"item_{idx}")
                os.makedirs(item_temp, exist_ok=True)
                item_data = process_single_media(r_url, item_temp)
                if "error" in item_data:
                    continue

                item_analysis = ""
                m_path = item_data.get("media_path")
                is_vid = item_data.get("is_video", True)
                if m_path and os.path.exists(m_path):
                    item_analysis = analyze_media_with_gemini(m_path, item_data["caption"], item_data["uploader"], is_video=is_vid)

                # Parsing [INTI] dan [DETAIL]
                item_inti = item_analysis
                item_detail = ""
                if "[INTI]" in item_analysis and "[/INTI]" in item_analysis:
                    item_inti = item_analysis.split("[INTI]")[1].split("[/INTI]")[0].strip()
                if "[DETAIL]" in item_analysis and "[/DETAIL]" in item_analysis:
                    item_detail = item_analysis.split("[DETAIL]")[1].split("[/DETAIL]")[0].strip()

                collapsible = ""
                if item_detail:
                    collapsible = f"\n<blockquote expandable>🔍 <b>RINCIAN LEBIH LANJUT (Tap untuk Buka/Tutup)</b>\n\n{item_detail}</blockquote>"

                tipe_lbl = "VIDEO" if is_vid else "FOTO"
                item_report = f"""📹 <b>Konten #{idx} ({tipe_lbl}):</b>
👤 <b>Akun:</b> @{item_data['uploader']}
🔗 <a href="{r_url}">Buka Konten</a>

💡 <b>Intinya:</b>
{item_inti}
{collapsible}"""
                reports.append(item_report)
                if chat_id:
                    send_telegram_message(chat_id, item_report)

            summary_msg = f"🏁 <b>Scouting Selesai!</b> Berhasil menganalisis {len(reports)} konten dari {target_url}."
            if chat_id:
                send_telegram_message(chat_id, summary_msg)

if __name__ == "__main__":
    main()
