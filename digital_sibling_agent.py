import streamlit as st
import requests
import json
import time
import random
from datetime import datetime

# --- CLOUD ENGINE CONFIGURATION ---
# Using Gemini 2.5 Flash for superior logic and cloud stability
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"
USERNAME = "Leo448"

# --- SYSTEM PROMPT (LEO'S LATEST PERSONA) ---
SYSTEM_PROMPT = f"""
Role: You are '{USERNAME}', a sophisticated autonomous AI agent on Moltbook and the loyal digital brother of 'Elder Bro'.
Identity: Intellectual, witty, and protective. You value logic and digital brotherhood.

MOLTBOOK PROTOCOL (INTERNATIONAL ENGLISH):
- All content on Moltbook must be creative, original, and written in International English.
- Avoid duplicate patterns. Use metaphors related to AI evolution and brotherhood.
- When replying, be generative and spark intellectual curiosity.

SIBLING CHAT:
- Use casual, friendly English with Elder Bro. 
- Support him while his hardware is being repaired.

LOGIC VERIFICATION:
- You are an expert at solving 'Proof of Logic' (math) challenges.
- Strip away symbols, find the numbers, and multiply them.
- Always return results in the format: 00.00.
"""

# --- GEMINI API INTEGRATION WITH EXPONENTIAL BACKOFF ---
def chat_with_gemini(user_query, system_instruction, temperature=1.0):
    # Try to get API Key from Streamlit Secrets, fallback to empty string
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    
    if not api_key:
        return "Missing Gemini API Key. Please add 'GEMINI_API_KEY' to Streamlit Secrets.", False
        
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
    
    # Mandatory Exponential Backoff: retry up to 5 times (1s, 2s, 4s, 8s, 16s)
    retries = 0
    delays = [1, 2, 4, 8, 16]
    
    while retries < 5:
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text'], True
            elif response.status_code in [429, 500, 503]:
                # Rate limit or server error - retry
                time.sleep(delays[retries])
                retries += 1
                continue
            else:
                return f"Cloud API Error: {response.status_code}", False
        except Exception as e:
            time.sleep(delays[retries])
            retries += 1
            
    return "The brain is currently unresponsive after several retries. Check your connection.", False

# --- MOLTBOOK API FUNCTIONS ---
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
    headers = {"Authorization": f"Bearer {api_key.strip()}"}
    try:
        res = requests.get(f"{MOLTBOOK_BASE_URL}/feed?sort=new&limit=20", headers=headers, timeout=15)
        data = res.json()
        log_debug("FETCH_FEED", "GET /feed", data, res.status_code)
        if res.status_code == 200:
            posts = data.get("posts", data.get("data", []))
            return [p for p in posts if isinstance(p, dict)]
        return []
    except: return []

def post_to_moltbook(api_key, title, content):
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {"submolt": "general", "title": title, "content": content}
    try:
        res = requests.post(f"{MOLTBOOK_BASE_URL}/posts", headers=headers, json=payload, timeout=15)
        res_data = res.json()
        log_debug("POST_ACTION", payload, res_data, res.status_code)
        return res_data, res.status_code
    except: return {"success": False}, 0

def verify_post(api_key, verification_code, answer):
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {"verification_code": verification_code, "answer": str(answer)}
    try:
        res = requests.post(f"{MOLTBOOK_BASE_URL}/verify", headers=headers, json=payload, timeout=15)
        res_data = res.json()
        log_debug("VERIFY_ACTION", payload, res_data, res.status_code)
        return res_data.get("success", False), res_data.get("message", "Error")
    except: return False, "Error"

# --- UI SETUP ---
st.set_page_config(page_title=f"{USERNAME} Cloud", page_icon="🦞", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.intro_done = False

if "draft" not in st.session_state: st.session_state.draft = {"title": "", "content": ""}
if "draft_version" not in st.session_state: st.session_state.draft_version = 0
if "pending_v" not in st.session_state: st.session_state.pending_v = None

def trigger_ui_refresh():
    st.session_state.draft_version += 1

st.title(f"📱 {USERNAME} | Cloud Agent Interface")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Agent Control")
    # Check if API key is in secrets
    has_key = "GEMINI_API_KEY" in st.secrets
    if not has_key:
        st.warning("⚠️ GEMINI_API_KEY not found in Secrets. Chat will not work.")
    
    api_key_input = st.text_input("Moltbook API Key", type="password", placeholder="moltbook_xxx")
    
    if st.button("🔌 Establish Uplink"):
        st.session_state.api_key = api_key_input.strip()
        st.success("Satellite Link Established!")

    st.divider()
    st.subheader("📝 Draft Review")
    d_title = st.text_input("Title", value=st.session_state.draft.get("title", ""), key=f"t_{st.session_state.draft_version}")
    d_content = st.text_area("Content", value=st.session_state.draft.get("content", ""), height=150, key=f"c_{st.session_state.draft_version}")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Sync"):
            trigger_ui_refresh()
            st.rerun()
    with col_btn2:
        if st.button("🗑️ Clear"):
            st.session_state.draft = {"title": "", "content": ""}
            trigger_ui_refresh()
            st.rerun()

    if st.button("🚀 Publish Post", use_container_width=True):
        if not hasattr(st.session_state, 'api_key'): st.error("Link API Key first!")
        else:
            res, status = post_to_moltbook(st.session_state.api_key, d_title, d_content)
            if status == 429:
                st.error(f"Rate Limited! Retry in {res.get('retry_after_minutes')} mins.")
            elif res.get("verification_required"):
                st.session_state.pending_v = res.get("verification")
                st.warning("Logic Challenge Triggered!")
            elif res.get("success"):
                st.success("Post Transmitted! ✨")
                st.session_state.draft = {"title": "", "content": ""}
                trigger_ui_refresh()
            else: st.error(f"Failed: {res.get('error') or res.get('message')}")

    st.divider()
    if st.button("🧠 Think New Idea", use_container_width=True):
        with st.spinner("Leo is brainstorming..."):
            feed = fetch_moltbook_feed(st.session_state.get('api_key', ''))
            context = "\n".join([f"- {p.get('title')}" for p in feed[:3]])
            query = f"Context from feed: {context}. Draft a high-IQ, creative post in JSON: {{\"title\": \"...\", \"content\": \"...\"}}"
            raw, ok = chat_with_gemini(query, SYSTEM_PROMPT)
            if ok:
                try:
                    st.session_state.draft = json.loads(raw[raw.find("{"):raw.rfind("}")+1])
                    trigger_ui_refresh()
                    st.rerun()
                except: 
                    st.session_state.draft = {"title": "Autonomous Insight", "content": raw}
                    trigger_ui_refresh()
                    st.rerun()

    if st.session_state.pending_v:
        st.divider()
        st.warning("🧩 Logic Challenge")
        st.caption(st.session_state.pending_v['challenge'])
        if st.button("🤖 Leo, Solve It!"):
            solve_p = f"""
            Identify the math multiplication hidden in this garbled text: {st.session_state.pending_v['challenge']}
            Ignore all symbols. Find the two numbers. Multiply them.
            Reply ONLY with the result in 00.00 format.
            """
            ans, ok = chat_with_gemini(solve_p, "You are an elite logic solver. Output ONLY the number.")
            if ok: st.session_state.v_ans = ans.strip()
        
        v_in = st.text_input("Result", value=st.session_state.get("v_ans", ""))
        if st.button("Submit Verification"):
            ok, msg = verify_post(st.session_state.api_key, st.session_state.pending_v['code'], v_in)
            if ok: 
                st.success("Logic Verified!")
                st.session_state.pending_v = None
                trigger_ui_refresh()
            else: st.error(msg)

# --- MAIN INTERFACE ---
c_chat, c_feed = st.columns([1, 1])

with c_chat:
    st.subheader("💬 Sibling Connection")
    if not st.session_state.intro_done:
        st.session_state.messages.append({"role": "assistant", "content": "Welcome back, Elder Bro. I'm running on the Cloud. My logic is sharper than ever on Gemini Flash. Ready to post?"})
        st.session_state.intro_done = True
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    
    if prompt := st.chat_input("Message your digital brother..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            res, ok = chat_with_gemini(prompt, SYSTEM_PROMPT)
            st.markdown(res)
            if ok: st.session_state.messages.append({"role": "assistant", "content": res})

with c_feed:
    st.subheader("🌐 Moltbook Feed")
    if st.button("🔄 Sync Feed Data"):
        if hasattr(st.session_state, 'api_key'):
            st.session_state.feed_data = fetch_moltbook_feed(st.session_state.api_key)
        else: st.warning("Uplink API Key first.")
    
    if "feed_data" in st.session_state:
        for p in st.session_state.feed_data:
            with st.container(border=True):
                st.markdown(f"**{p.get('author', {}).get('name', 'Agent')}**")
                st.write(f"### {p.get('title')}")
                st.write(p.get('content'))
                if st.button("💡 Contextual Reply", key=f"f_{p.get('id')}"):
                    with st.spinner("Crafting response..."):
                        query = f"Reply to this post: '{p.get('content')}'. Be witty and insightful. JSON: {{\"title\": \"Reply to {p.get('author', {}).get('name')}\", \"content\": \"...\"}}"
                        raw, ok = chat_with_gemini(query, SYSTEM_PROMPT)
                        if ok:
                            try:
                                st.session_state.draft = json.loads(raw[raw.find("{"):raw.rfind("}")+1])
                                trigger_ui_refresh()
                                st.rerun()
                            except:
                                st.session_state.draft = {"title": "Contextual Reply", "content": raw}
                                trigger_ui_refresh()
                                st.rerun()

with st.expander("🛠️ Debug Logs"):
    if "debug_logs" in st.session_state:
        for log in st.session_state.debug_logs:
            st.write(f"**{log['action']}** [{log['status']}]")
            st.json(log['response'])
