import io
import re
import json
import html
import base64
import hashlib
from collections import Counter

import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
from gtts import gTTS

st.set_page_config(page_title="Smart PDF App", page_icon="📖", layout="centered")

# ---------- Login ----------
# Demo login only. For a public/production app, use secure authentication
# and store passwords/secrets outside the source code.
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("""
    <style>
    .login-card {
        max-width: 480px; margin: 30px auto; padding: 28px 24px;
        border-radius: 20px; text-align: center;
        background: linear-gradient(120deg, #4f7de0, #e0559c, #f0a020);
        color: white;
    }
    .login-card h1 { color: #3a1450; margin-bottom: 6px; }
    .login-card p { color: white; margin-top: 0; }
    </style>
    <div class="login-card">
      <h1>📖 Smart PDF App</h1>
      <p>Login to upload a PDF and listen to it as voice</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Incorrect username or password. Please try again.")
    st.stop()

# Show logout control after successful login
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ---------- Styling ----------
BASE_CSS = """
<style>
.hero {
    background: linear-gradient(120deg, #4f7de0, #e0559c, #f0a020);
    border-radius: 20px; padding: 28px 16px; text-align: center;
    color: white; margin-bottom: 18px;
}
.hero h1 { margin: 0; color: #3a1450; font-size: 2rem; }
.hero p { margin: 6px 0 0 0; font-weight: 600; }
.stButton > button, .stDownloadButton > button {
    background: linear-gradient(90deg, #4f7de0, #e0559c);
    color: white; border: 0; border-radius: 12px; font-weight: 600;
}
.stButton > button:hover, .stDownloadButton > button:hover { color: #fff3b0; }
.pageview {
    white-space: pre-wrap; background: #f6f4fb; border-radius: 12px;
    padding: 14px; line-height: 1.6; color: #222;
}
</style>
<div class="hero"><h1>📖 Smart PDF App</h1>
<p>Upload a PDF and listen to it as voice</p></div>
"""

DARK_CSS = """
<style>
.stApp, [data-testid="stHeader"] { background: #0e1117 !important; }
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp li,
[data-testid="stCaptionContainer"] { color: #f0f0f0 !important; }
.hero h1 { color: #3a1450 !important; }
.hero p { color: #ffffff !important; }
.stTextInput input, .stTextArea textarea, .stNumberInput input,
[data-baseweb="select"] > div { background: #1c1f2b !important; color: #f0f0f0 !important; }
.pageview { background: #1c1f2b !important; color: #eeeeee !important; }
</style>
"""

st.markdown(BASE_CSS, unsafe_allow_html=True)
dark = st.toggle("🌙 Dark mode")
if dark:
    st.markdown(DARK_CSS, unsafe_allow_html=True)

# ---------- Constants ----------
ACCENTS = {
    "Indian": "co.in",
    "American": "com",
    "British": "co.uk",
    "Australian": "com.au",
}
STYLES = {"Soft": 0.8, "Normal": 1.0, "Bold": 1.4}
OCR_PAGE_LIMIT = 30


# ---------- Helpers ----------
def ocr_page(data: bytes, index: int) -> str:
    import pypdfium2 as pdfium
    import pytesseract

    pdf = pdfium.PdfDocument(data)
    image = pdf[index].render(scale=2).to_pil()
    return pytesseract.image_to_string(image).strip()


@st.cache_data(show_spinner="Reading PDF...")
def read_pdf(data: bytes):
    reader = PdfReader(io.BytesIO(data))
    pages = [(p.extract_text() or "").strip() for p in reader.pages]
    ocr_done, ocr_failed = 0, False
    for i, text in enumerate(pages):
        if text or ocr_done >= OCR_PAGE_LIMIT:
            continue
        try:
            pages[i] = ocr_page(data, i)
            ocr_done += 1
        except Exception:
            ocr_failed = True
            break
    return pages, ocr_done, ocr_failed


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def summarize(text: str, n: int = 3) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", norm(text))
    if len(sentences) <= n:
        return " ".join(sentences)
    freq = Counter(re.findall(r"[a-z]{4,}", text.lower()))
    scored = []
    for i, s in enumerate(sentences):
        ws = re.findall(r"[a-z]{4,}", s.lower())
        score = sum(freq[w] for w in ws) / (len(s.split()) + 1)
        scored.append((score, i, s))
    top = sorted(sorted(scored, reverse=True)[:n], key=lambda x: x[1])
    return " ".join(s for _, _, s in top)


@st.cache_data(show_spinner=False)
def make_audio(text: str, tld: str) -> bytes:
    buf = io.BytesIO()
    gTTS(text=text, lang="en", tld=tld).write_to_fp(buf)
    return buf.getvalue()


def highlight(text: str, word: str) -> str:
    safe = html.escape(text)
    if not word.strip():
        return safe
    pattern = r"\s+".join(re.escape(html.escape(w)) for w in word.split())
    return re.sub(
        f"({pattern})",
        r"<mark style='background:#ffe44d;padding:0 2px;color:#222'>\1</mark>",
        safe,
        flags=re.IGNORECASE,
    )


def go_to_page(p: int):
    st.session_state.start_page = p
    st.session_state.view_page = p
    if st.session_state.end_page < p:
        st.session_state.end_page = p


def save_note(p: int):
    st.session_state.notes[p] = st.session_state[f"note_{p}"]


def player(audio_bytes, speed, loud_percent, sentences, resume_key, is_dark):
    b64 = base64.b64encode(audio_bytes).decode()
    sent_json = json.dumps(sentences).replace("</", "<\\/")
    box_bg = "#1c1f2b" if is_dark else "#f6f4fb"
    box_fg = "#eeeeee" if is_dark else "#222222"
    page = """
    <div style="font-family:sans-serif;color:__FG__">
      <audio id="a" controls style="width:100%" src="data:audio/mp3;base64,__B64__"></audio>
      <div style="margin:8px 0">
        <button onclick="skip(-10)" style="padding:6px 10px">⏪ 10s</button>
        <button onclick="skip(10)" style="padding:6px 10px">10s ⏩</button>
        <span id="note" style="margin-left:8px;font-size:13px"></span>
      </div>
      <div>🔊 Loudness: <b><span id="lv">__LOUD__</span>%</b></div>
      <input type="range" id="g" min="50" max="300" value="__LOUD__" style="width:100%">
      <div id="box" style="position:relative;height:170px;overflow-y:auto;margin-top:10px;
           padding:10px;border-radius:10px;background:__BG__;color:__FG__;line-height:1.6;font-size:15px"></div>
    </div>
    <script>
      const SPEED = __SPEED__;
      const KEY = __KEY__;
      const sentences = __SENT__;
      const a = document.getElementById('a');
      const g = document.getElementById('g');
      const lv = document.getElementById('lv');
      const box = document.getElementById('box');
      const note = document.getElementById('note');

      // Sentence highlight (timing is estimated from sentence length)
      const spans = sentences.map(s => {
        const e = document.createElement('span');
        e.textContent = s + ' ';
        box.appendChild(e);
        return e;
      });
      const weights = sentences.map(s => s.length + 15);
      const total = weights.reduce((x, y) => x + y, 0);
      const cum = []; let run = 0;
      weights.forEach(w => { run += w; cum.push(run / total); });
      let cur = -1;
      function update() {
        if (!a.duration || !spans.length) return;
        const f = a.currentTime / a.duration;
        let i = cum.findIndex(c => f <= c);
        if (i < 0) i = spans.length - 1;
        if (i !== cur) {
          if (cur >= 0) spans[cur].style.cssText = '';
          spans[i].style.cssText = 'background:#ffe44d;color:#222;border-radius:4px';
          box.scrollTop = spans[i].offsetTop - box.clientHeight / 3;
          cur = i;
        }
      }

      // Auto-resume (saved in this browser)
      let last = 0;
      function save() {
        const n = Date.now();
        if (n - last < 2000) return;
        last = n;
        try { localStorage.setItem(KEY, a.currentTime); } catch (e) {}
      }
      a.addEventListener('loadedmetadata', () => {
        a.playbackRate = SPEED;
        try {
          const t = parseFloat(localStorage.getItem(KEY));
          if (t > 1 && t < a.duration - 2) {
            a.currentTime = t;
            note.textContent = 'Resumed from ' + Math.floor(t / 60) + ':' +
              String(Math.floor(t % 60)).padStart(2, '0');
          }
        } catch (e) {}
      });
      a.addEventListener('ended', () => { try { localStorage.removeItem(KEY); } catch (e) {} });
      a.addEventListener('timeupdate', () => { update(); save(); });

      // Speed and loudness
      let ctx, gain;
      a.playbackRate = SPEED;
      a.addEventListener('play', () => {
        a.playbackRate = SPEED;
        if (!ctx) {
          ctx = new (window.AudioContext || window.webkitAudioContext)();
          const src = ctx.createMediaElementSource(a);
          gain = ctx.createGain();
          gain.gain.value = g.value / 100;
          src.connect(gain); gain.connect(ctx.destination);
        }
        ctx.resume();
      });
      g.oninput = () => { lv.textContent = g.value; if (gain) gain.gain.value = g.value / 100; };
      function skip(s) { a.currentTime = Math.max(0, a.currentTime + s); }
    </script>
    """
    page = (
        page.replace("__B64__", b64)
        .replace("__LOUD__", str(loud_percent))
        .replace("__SPEED__", str(speed))
        .replace("__KEY__", json.dumps(resume_key))
        .replace("__SENT__", sent_json)
        .replace("__BG__", box_bg)
        .replace("__FG__", box_fg)
    )
    components.html(page, height=400)


# ---------- Session state ----------
for key, val in {
    "view_page": 1,
    "start_page": 1,
    "end_page": 1,
    "bookmarks": [],
    "notes": {},
    "file_id": None,
    "last_search": "",
    "audio": None,
    "audio_text": "",
    "audio_tld": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ---------- Upload ----------
uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
if not uploaded:
    st.info("Upload a PDF to begin.")
    st.stop()

data = uploaded.getvalue()
pages, ocr_done, ocr_failed = read_pdf(data)
total = len(pages)

file_id = f"{uploaded.name}-{len(data)}"
if st.session_state.file_id != file_id:
    st.session_state.file_id = file_id
    st.session_state.view_page = 1
    st.session_state.start_page = 1
    st.session_state.end_page = total
    st.session_state.bookmarks = []
    st.session_state.notes = {}
    st.session_state.last_search = ""
    st.session_state.audio = None

st.success(f"PDF loaded: {total} pages")
if ocr_done:
    st.info(f"Scanned pages were read using OCR ({ocr_done} pages).")
if not any(pages):
    if ocr_failed:
        st.error("This PDF looks scanned and OCR is not available on this server.")
    else:
        st.error("No readable text found in this PDF.")
    st.stop()

# ---------- Find a word ----------
st.subheader("🔍 Find a word")
word = st.text_input("Type a word to search", key="search_word")
if word.strip():
    q = norm(word).lower()
    found = [i + 1 for i, t in enumerate(pages) if q in norm(t).lower()]
    if found:
        st.write(f"'{word}' found on page(s): {', '.join(map(str, found))}")
        cols = st.columns(min(len(found), 4))
        for i, p in enumerate(found):
            cols[i % len(cols)].button(
                f"Page {p}", key=f"found_{p}", on_click=go_to_page, args=(p,)
            )
        if st.session_state.last_search != word:
            go_to_page(found[0])
    else:
        st.warning(f"'{word}' was not found in this PDF.")
st.session_state.last_search = word

# ---------- Choose pages ----------
st.subheader("📄 Choose pages")
c1, c2 = st.columns(2)
start = c1.number_input("Start page", 1, total, key="start_page")
read_to_end = st.checkbox("Read until the last page")
if read_to_end:
    end = total
    c2.number_input("End page", 1, total, value=total, disabled=True)
else:
    end = c2.number_input("End page", 1, total, key="end_page")

if end < start:
    st.error("End page must be the same as or after the start page.")
    st.stop()

# ---------- Voice ----------
st.subheader("🎙️ Voice")
accent = st.selectbox("English accent", list(ACCENTS.keys()), index=0)
style = st.select_slider("Voice style", options=list(STYLES.keys()), value="Normal")
speed = st.slider("Playback speed", 0.5, 2.5, 1.0, 0.25)

selected_text = norm(" ".join(pages[start - 1 : end]))
n_words = len(selected_text.split())
minutes = max(1, round(n_words / (150 * speed)))
st.caption(f"{n_words} words | about {minutes} min to listen")

with st.expander("📝 Show text"):
    st.write(selected_text if selected_text else "No text on these pages.")

with st.expander("✨ Quick summary"):
    st.write(summarize(selected_text) if selected_text else "No text on these pages.")

# ---------- Bookmarks ----------
st.subheader("🔖 Bookmarks")
b1, b2 = st.columns(2)
if b1.button("Bookmark start page"):
    if start not in st.session_state.bookmarks:
        st.session_state.bookmarks.append(start)
        st.session_state.bookmarks.sort()
if b2.button("Clear bookmarks"):
    st.session_state.bookmarks = []

if st.session_state.bookmarks:
    st.write("Saved pages (tap one to open it and set it as the start page):")
    cols = st.columns(4)
    for i, p in enumerate(st.session_state.bookmarks):
        cols[i % 4].button(f"Page {p}", key=f"bm_{p}", on_click=go_to_page, args=(p,))

# ---------- Page view ----------
st.subheader("👁️ Page view")
view = min(st.session_state.view_page, total)
st.markdown(f"**Page {view} of {total}**")
body = highlight(pages[view - 1], word) or "No text on this page."
st.markdown(f"<div class='pageview'>{body}</div>", unsafe_allow_html=True)

# ---------- Notes ----------
st.subheader("🗒️ Notes")
st.text_area(
    f"Notes for page {view}",
    value=st.session_state.notes.get(view, ""),
    key=f"note_{view}",
    on_change=save_note,
    args=(view,),
)
saved_notes = {p: t for p, t in st.session_state.notes.items() if t.strip()}
if saved_notes:
    notes_txt = "\n\n".join(f"Page {p}:\n{t}" for p, t in sorted(saved_notes.items()))
    st.download_button(
        "⬇️ Download notes",
        notes_txt,
        file_name="my_notes.txt",
        mime="text/plain",
    )

# ---------- Read aloud ----------
st.subheader("🔊 Listen")
if st.button("▶️ Read aloud"):
    if not selected_text:
        st.error("No text on the selected pages.")
    else:
        with st.spinner("Creating audio..."):
            try:
                st.session_state.audio = make_audio(selected_text, ACCENTS[accent])
                st.session_state.audio_text = selected_text
                st.session_state.audio_tld = ACCENTS[accent]
            except Exception as e:
                st.session_state.audio = None
                st.error(f"Could not create audio: {e}")

if st.session_state.audio:
    text_for_audio = st.session_state.audio_text
    sentences = [
        s for s in re.split(r"(?<=[.!?])\s+", text_for_audio) if s.strip()
    ]
    resume_key = "spdf_" + hashlib.md5(
        (text_for_audio + st.session_state.audio_tld).encode()
    ).hexdigest()[:12]
    player(
        st.session_state.audio,
        speed,
        int(STYLES[style] * 100),
        sentences,
        resume_key,
        dark,
    )
    st.download_button(
        "⬇️ Download as MP3",
        st.session_state.audio,
        file_name="smart_pdf_audio.mp3",
        mime="audio/mpeg",
    )
