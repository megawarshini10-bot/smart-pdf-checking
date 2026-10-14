import io
import re
import html
import base64
from collections import Counter

import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
from gtts import gTTS

st.set_page_config(page_title="Smart PDF App", page_icon="📖", layout="centered")

# ---------- Styling ----------
st.markdown(
    """
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
    """,
    unsafe_allow_html=True,
)

# ---------- Helpers ----------
ACCENTS = {
    "Indian": "co.in",
    "American": "com",
    "British": "co.uk",
    "Australian": "com.au",
}
STYLES = {"Soft": 0.8, "Normal": 1.0, "Bold": 1.4}


@st.cache_data(show_spinner=False)
def read_pdf(data: bytes):
    reader = PdfReader(io.BytesIO(data))
    return [(p.extract_text() or "").strip() for p in reader.pages]


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
        r"<mark style='background:#ffe44d;padding:0 2px'>\1</mark>",
        safe,
        flags=re.IGNORECASE,
    )


def go_to_page(p: int):
    st.session_state.start_page = p
    st.session_state.view_page = p
    if st.session_state.end_page < p:
        st.session_state.end_page = p


def player(audio_bytes: bytes, speed: float, loud_percent: int):
    b64 = base64.b64encode(audio_bytes).decode()
    page = """
    <div style="font-family:sans-serif">
      <audio id="a" controls style="width:100%" src="data:audio/mp3;base64,__B64__"></audio>
      <div style="margin:8px 0">
        <button onclick="skip(-10)" style="padding:6px 10px">⏪ 10s</button>
        <button onclick="skip(10)" style="padding:6px 10px">10s ⏩</button>
      </div>
      <div>🔊 Loudness: <b><span id="lv">__LOUD__</span>%</b></div>
      <input type="range" id="g" min="50" max="300" value="__LOUD__" style="width:100%">
    </div>
    <script>
      const a = document.getElementById('a');
      const g = document.getElementById('g');
      const lv = document.getElementById('lv');
      let ctx, gain;
      a.playbackRate = __SPEED__;
      a.addEventListener('loadedmetadata', () => { a.playbackRate = __SPEED__; });
      a.addEventListener('play', () => {
        a.playbackRate = __SPEED__;
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
    )
    components.html(page, height=190)


# ---------- Session state ----------
for key, val in {
    "view_page": 1,
    "start_page": 1,
    "end_page": 1,
    "bookmarks": [],
    "file_id": None,
    "last_search": "",
    "audio": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ---------- Upload ----------
uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
if not uploaded:
    st.info("Upload a PDF to begin.")
    st.stop()

data = uploaded.getvalue()
pages = read_pdf(data)
total = len(pages)

file_id = f"{uploaded.name}-{len(data)}"
if st.session_state.file_id != file_id:
    st.session_state.file_id = file_id
    st.session_state.view_page = 1
    st.session_state.start_page = 1
    st.session_state.end_page = total
    st.session_state.bookmarks = []
    st.session_state.last_search = ""
    st.session_state.audio = None

if not any(pages):
    st.error("No readable text found. This PDF may be a scanned image.")
    st.stop()

st.success(f"PDF loaded: {total} pages")

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
        cols[i % 4].button(
            f"Page {p}", key=f"bm_{p}", on_click=go_to_page, args=(p,)
        )

# ---------- Page view ----------
st.subheader("👁️ Page view")
view = min(st.session_state.view_page, total)
st.markdown(f"**Page {view} of {total}**")
body = highlight(pages[view - 1], word) or "No text on this page."
st.markdown(f"<div class='pageview'>{body}</div>", unsafe_allow_html=True)

# ---------- Read aloud ----------
st.subheader("🔊 Listen")
if st.button("▶️ Read aloud"):
    if not selected_text:
        st.error("No text on the selected pages.")
    else:
        with st.spinner("Creating audio..."):
            try:
                st.session_state.audio = make_audio(selected_text, ACCENTS[accent])
            except Exception as e:
                st.session_state.audio = None
                st.error(f"Could not create audio: {e}")

if st.session_state.audio:
    player(st.session_state.audio, speed, int(STYLES[style] * 100))
    st.download_button(
        "⬇️ Download as MP3",
        st.session_state.audio,
        file_name="smart_pdf_audio.mp3",
        mime="audio/mpeg",
    )
