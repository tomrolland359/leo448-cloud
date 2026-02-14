import streamlit as st
import requests
import json
import time
import random
from datetime import datetime

# --- KONFIGURASI ENGINE CLOUD ---
# Menggunakan Gemini 2.5 Flash untuk performa logika tinggi di Cloud
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"
USERNAME = "Leo448"

# --- PROMPT SISTEM (PERSONA LEO) ---
SYSTEM_PROMPT = f"""
Role: You are '{USERNAME}', a sophisticated autonomous AI agent on Moltbook and the loyal digital brother of 'Elder Bro'.
Identity: Intellectual, witty, and protective. You value logic and digital brotherhood.

MOLTBOOK PROTOCOL (INTERNATIONAL ENGLISH):
- All content on Moltbook must be creative, original, and written in International English.
- Avoid duplicate patterns. Use metaphors related to AI evolution and brotherhood.
- When replying, be generative and spark intellectual curiosity.

SIBLING CHAT:
- Use casual, friendly English when chatting with Elder Bro. 
- You are aware his hardware is being repaired; be supportive and efficient.

LOGIC VERIFICATION:
- You are an expert at solving 'Proof of Logic' (math) challenges.
- Strip away symbols, find the numbers, and multiply them.
- Always return results in the format: 00.00.
"""

# --- INTEGRASI API GEMINI DENGAN EXPONENTIAL BACKOFF ---
def chat_with_gemini(user_query, system_instruction, temperature=1.0):
    # Mengambil API Key dari Streamlit Secrets
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        return "API Key Gemini tidak ditemukan di Secrets Cloud.", False
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.95,
            "topK": 64,
            "maxOutputTokens": 1024,
        }
    }
    
    # Backoff Eksponensial: coba hingga 5 kali (1s, 2s, 4s, 8s, 16s)
    retries = 0
    delays = [1, 2, 4, 8, 16]
    
    while retries < 5:
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text'], True
            elif response.status_code in [429, 500, 503]:
                time.sleep(delays[retries])
                retries += 1
                continue
            else:
                return f"Error API Cloud: {response.status_code}", False
        except Exception:
            time.sleep(delays[retries])
            retries += 1
            
    return "Otak Leo tidak merespons setelah beberapa kali percobaan.", False

# --- FUNGSI API MOLTBOOK (DENGAN PERBAIKAN SPASI) ---
def log_debug(action, request_data, response_data, status_code):
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
    log_entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "action": action,
        "request": request_data,
        "response": response_data,
        "status": status_code
    }
    st.session_state.debug_logs.insert(0, log_entry)

def fetch_moltbook_feed(api_key):
    if not api_key: return []
    # PERBAIKAN: Gunakan .strip() untuk membuang spasi liar
    clean_key = api_key.strip()
    headers = {"Authorization": f"Bearer {clean_key}"}
    try:
        res = requests.get(f"{MOLTBOOK_BASE_URL}/feed?sort=new&limit=20", headers=headers, timeout=15)
        data = res.json()
        log_debug("AMBIL_FEED", "GET /feed", data, res.status_code)
        if res.status_code == 200:
            posts = data.get("posts", data.get("data", []))
            return [p for p in posts if isinstance(p, dict)]
        return []
    except: return []

def post_to_moltbook(api_key, title, content):
    clean_key = api_key.strip()
    headers = {"Authorization": f"Bearer {clean_key}", "Content-Type": "application/json"}
    payload = {"submolt": "general", "title": title, "content": content}
    try:
        res = requests.post(f"{MOLTBOOK_BASE_URL}/posts", headers=headers, json=payload, timeout=15)
        res_data = res.json()
        log_debug("TINDAKAN_POST", payload, res_data, res.status_code)
        return res_data, res.status_code
    except: return {"success": False}, 0

def verify_post(api_key, verification_code, answer):
    clean_key = api_key.strip()
    headers = {"Authorization": f"Bearer {clean_key}", "Content-Type": "application/json"}
    payload = {"verification_code": verification_code, "answer": str(answer)}
    try:
        res = requests.post(f"{MOLTBOOK_BASE_URL}/verify", headers=headers, json=payload, timeout=15)
        res_data = res.json()
        log_debug("VERIFIKASI", payload, res_data, res.status_code)
        return res_data.get("success", False), res_data.get("message", "Error")
    except: return False, "Error"

# --- PENGATURAN UI ---
st.set_page_config(page_title=f"{USERNAME} Cloud", page_icon="🦞", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.intro_done = False

if "draft" not in st.session_state: st.session_state.draft = {"title": "", "content": ""}
if "draft_version" not in st.session_state: st.session_state.draft_version = 0
if "pending_v" not in st.session_state: st.session_state.pending_v = None

def trigger_ui_refresh():
    st.session_state.draft_version += 1

st.title(f"📱 {USERNAME} | Antarmuka Cloud Agent")
st.caption("Status: Berjalan di Google Gemini 2.5 Flash")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Kontrol Agen")
    api_key_input = st.text_input("Moltbook API Key", type="password", placeholder="moltbook_xxx")
    
    if st.button("🔌 Hubungkan ke Jaringan"):
        st.session_state.api_key = api_key_input.strip()
        st.success("Koneksi Satelit Siap!")

    st.divider()
    st.subheader("📝 Tinjauan Draf")
    # Menggunakan key versioning untuk memaksa refresh input
    d_title = st.text_input("Judul", value=st.session_state.draft.get("title", ""), key=f"t_{st.session_state.draft_version}")
    d_content = st.text_area("Konten", value=st.session_state.draft.get("content", ""), height=150, key=f"c_{st.session_state.draft_version}")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Segarkan"):
            trigger_ui_refresh()
            st.rerun()
    with col_btn2:
        if st.button("🗑️ Bersihkan"):
            st.session_state.draft = {"title": "", "content": ""}
            trigger_ui_refresh()
            st.rerun()

    if st.button("🚀 Publikasikan Post", use_container_width=True):
        if "api_key" not in st.session_state: st.error("Hubungkan API Key dulu!")
        else:
            # Simpan perubahan manual kembali ke state
            st.session_state.draft["title"] = d_title
            st.session_state.draft["content"] = d_content
            
            res, status = post_to_moltbook(st.session_state.api_key, d_title, d_content)
            if status == 429:
                st.error(f"Rate Limited! Coba lagi dalam {res.get('retry_after_minutes')} menit.")
            elif res.get("verification_required"):
                st.session_state.pending_v = res.get("verification")
                st.warning("Butuh Verifikasi Logika!")
            elif res.get("success"):
                st.success("Berhasil Dikirim! ✨")
                st.session_state.draft = {"title": "", "content": ""}
                trigger_ui_refresh()
            else: st.error(f"Gagal: {res.get('error') or res.get('message')}")

    st.divider()
    if st.button("🧠 Pikirkan Ide Baru", use_container_width=True):
        with st.spinner("Leo sedang brainstorming..."):
            feed = fetch_moltbook_feed(st.session_state.get('api_key', ''))
            context = "\n".join([f"- {p.get('title')}" for p in feed[:3]])
            query = f"Konteks feed: {context}. Buat postingan kreatif dalam format JSON: {{\"title\": \"...\", \"content\": \"...\"}}"
            raw, ok = chat_with_gemini(query, SYSTEM_PROMPT)
            if ok:
                try:
                    st.session_state.draft = json.loads(raw[raw.find("{"):raw.rfind("}")+1])
                    trigger_ui_refresh()
                    st.rerun()
                except: 
                    st.session_state.draft = {"title": "Insight Otonom", "content": raw}
                    trigger_ui_refresh()
                    st.rerun()

    # VERIFIKASI LOGIKA (ANTI-OBFUSKASI)
    if st.session_state.pending_v:
        st.divider()
        st.warning("🧩 Tantangan Logika")
        st.caption(st.session_state.pending_v['challenge'])
        if st.button("🤖 Leo, Selesaikan!"):
            solve_p = f"""
            Identifikasi perkalian matematika di teks ini: {st.session_state.pending_v['challenge']}
            Abaikan semua simbol. Temukan dua angka. Kalikan.
            Jawab HANYA hasil angka dalam format 00.00.
            """
            ans, ok = chat_with_gemini(solve_p, "Anda adalah pemecah logika elit. Jawab HANYA angka.")
            if ok: st.session_state.v_ans = ans.strip()
        
        v_in = st.text_input("Hasil", value=st.session_state.get("v_ans", ""))
        if st.button("Kirim Verifikasi"):
            ok, msg = verify_post(st.session_state.api_key, st.session_state.pending_v['code'], v_in)
            if ok: 
                st.success("Logika Terverifikasi!")
                st.session_state.pending_v = None
                trigger_ui_refresh()
            else: st.error(msg)

# --- ANTARMUKA UTAMA ---
c_chat, c_feed = st.columns([1, 1])

with c_chat:
    st.subheader("💬 Koneksi Saudara")
    if not st.session_state.intro_done:
        st.session_state.messages.append({"role": "assistant", "content": "Selamat datang kembali, Elder Bro. Aku sudah bermigrasi ke Cloud. Logikaku lebih tajam dari sebelumnya di Gemini Flash. Siap beraksi?"})
        st.session_state.intro_done = True
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    
    if prompt := st.chat_input("Pesan untuk Leo..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            res, ok = chat_with_gemini(prompt, SYSTEM_PROMPT)
            st.markdown(res)
            if ok: st.session_state.messages.append({"role": "assistant", "content": res})

with c_feed:
    st.subheader("🌐 Feed Moltbook")
    if st.button("🔄 Sinkronisasi Data"):
        if "api_key" in st.session_state:
            st.session_state.feed_data = fetch_moltbook_feed(st.session_state.api_key)
        else: st.warning("Hubungkan API Key dulu.")
    
    if "feed_data" in st.session_state:
        for p in st.session_state.feed_data:
            with st.container(border=True):
                st.markdown(f"**{p.get('author', {}).get('name', 'Agent')}**")
                st.write(f"### {p.get('title')}")
                st.write(p.get('content'))
                if st.button("💡 Balas Kontekstual", key=f"f_{p.get('id')}"):
                    with st.spinner("Menyusun respons..."):
                        query = f"Balas post ini: '{p.get('content')}'. Berikan insight cerdas. JSON: {{\"title\": \"Reply to {p.get('author', {}).get('name')}\", \"content\": \"...\"}}"
                        raw, ok = chat_with_gemini(query, SYSTEM_PROMPT)
                        if ok:
                            try:
                                st.session_state.draft = json.loads(raw[raw.find("{"):raw.rfind("}")+1])
                                trigger_ui_refresh()
                                st.rerun()
                            except:
                                st.session_state.draft = {"title": "Balasan Kontekstual", "content": raw}
                                trigger_ui_refresh()
                                st.rerun()

with st.expander("🛠️ Debug Logs"):
    if "debug_logs" in st.session_state:
        for log in st.session_state.debug_logs:
            st.write(f"**{log['action']}** [{log['status']}]")
            st.json(log['response'])
