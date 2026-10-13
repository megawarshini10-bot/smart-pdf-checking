import io
import re
import base64
import asyncio
from collections import Counter

import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
from gtts import gTTS

try:
    import edge_tts
except ImportError:
    edge_tts = None

st.set_page_config(page_title="Smart PDF App", page_icon="📖")

# ---------- Simple demo users (change these) ----------
USERS = {"admin": "1234", "student": "pdf123"}

# ---------- Session state ----------
defaults = {"logged_in": False, "user": "", "bookmarks": [], "history": []}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value



def inject_css(dark=False):
    """Web-page style design: gradient background, hero banner, cards, rounded buttons."""
    bg = "linear-gradient(135deg,#0f2027,#203a43,#2c5364)" if dark else "linear-gradient(135deg,#eef2ff,#fdf2f8,#ecfeff)"
    text = "#f8fafc" if dark else "#1e293b"
    card = "rgba(255,255,255,0.08)" if dark else "rgba(255,255,255,0.85)"
    st.markdown(f"""
    <style>
    #MainMenu, footer, header {{visibility: hidden;}}
    .stApp {{background: {bg}; color: {text};}}
    .block-container {{max-width: 900px; padding-top: 1.5rem;}}
    .stApp p, .stApp label, .stApp span, .stApp h2, .stApp h3, .stApp li {{color: {text};}}
    .hero {{
        background: linear-gradient(120deg,#6366f1,#ec4899,#f59e0b);
        padding: 32px 24px; border-radius: 20px; text-align: center;
        color: white; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(99,102,241,0.35);
    }}
    .hero h1 {{color: white !important; margin: 0; font-size: 2.2rem;}}
    .hero p {{color: #fff !important; margin: 6px 0 0 0; font-size: 1.05rem;}}
    .card {{
        background: {card}; padding: 18px 20px; border-radius: 16px;
        margin-bottom: 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }}
    .stButton > button, .stDownloadButton > button {{
        background: linear-gradient(90deg,#6366f1,#ec4899); color: white;
        border: none; border-radius: 12px; padding: 0.6rem 1.4rem;
        font-weight: 600; transition: transform 0.15s;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        transform: translateY(-2px); color: white;
    }}
    .stTextInput input, .stNumberInput input {{border-radius: 10px;}}
    [data-testid="stFileUploader"] section {{
        border: 2px dashed #6366f1; border-radius: 16px; background: {card};
    }}
    </style>
    """, unsafe_allow_html=True)


def hero(title, subtitle):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)



EDGE_VOICES = {
    "American": "en-US-AriaNeural",
    "British": "en-GB-SoniaNeural",
    "Indian": "en-IN-NeerjaNeural",
    "Australian": "en-AU-NatashaNeural",
}


def make_audio(text, accent, tld):
    """Try edge-tts first, then gTTS. Returns MP3 bytes or None."""
    text = text[:5000]
    if edge_tts is not None:
        try:
            async def run():
                data = b""
                comm = edge_tts.Communicate(text, EDGE_VOICES[accent])
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        data += chunk["data"]
                return data
            data = asyncio.run(run())
            if data:
                return data
        except Exception:
            pass
    try:
        buf = io.BytesIO()
        gTTS(text=text[:3000], lang="en", tld=tld).write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None


# ---------- Login page ----------
def login_page():
    inject_css()
    hero("📖 Smart PDF App", "Login to listen to your PDFs")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if USERS.get(username) == password and password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Wrong username or password")


# ---------- Helpers ----------
def simple_summary(text, num_sentences=3):
    """Pick the sentences that contain the most frequent words."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    if not words or len(sentences) <= num_sentences:
        return text
    freq = Counter(words)
    scored = []
    for i, s in enumerate(sentences):
        score = sum(freq.get(w, 0) for w in re.findall(r"[a-zA-Z]{4,}", s.lower()))
        scored.append((score, i, s))
    top = sorted(scored, reverse=True)[:num_sentences]
    top = sorted(top, key=lambda x: x[1])
    return " ".join(s for _, _, s in top)


def audio_player(audio_bytes, speed):
    """Audio player with play/pause, 10s skip buttons and speed control."""
    b64 = base64.b64encode(audio_bytes).decode()
    html = f"""
    <audio id="player" controls style="width:100%">
      <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    <div style="display:flex;gap:8px;margin-top:8px;font-family:sans-serif">
      <button onclick="skip(-10)">⏪ 10s</button>
      <button onclick="skip(10)">10s ⏩</button>
    </div>
    <script>
      const p = document.getElementById('player');
      p.playbackRate = {speed};
      p.addEventListener('play', () => p.playbackRate = {speed});
      function skip(s) {{ p.currentTime = Math.max(0, p.currentTime + s); }}
    </script>
    """
    components.html(html, height=120)


# ---------- Main app ----------
def main_app():
    # Sidebar: user, theme, font size, logout
    st.sidebar.write(f"👤 Logged in as: **{st.session_state.user}**")
    dark = st.sidebar.toggle("Dark mode")
    font_size = st.sidebar.slider("Text size", 12, 28, 16)
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    inject_css(dark)
    hero("📖 Smart PDF App", "Upload a PDF and listen to it as voice")

    uploaded = st.file_uploader("Upload a PDF", type="pdf")
    if not uploaded:
        if st.session_state.history:
            st.subheader("🕘 Reading history")
            for item in reversed(st.session_state.history[-5:]):
                st.write("•", item)
        return

    reader = PdfReader(uploaded)
    total = len(reader.pages)
    pages_text = [(p.extract_text() or "") for p in reader.pages]
    st.success(f"PDF loaded: {total} pages")

    # Word search
    st.subheader("🔍 Find a word")
    word = st.text_input("Type a word to search")
    start_default = 1
    if word:
        found = [i + 1 for i, t in enumerate(pages_text) if word.lower() in t.lower()]
        if found:
            st.write(f"'{word}' found on page(s): {', '.join(map(str, found))}")
            start_default = found[0]
        else:
            st.warning("Word not found in this PDF")

    # Page range
    st.subheader("📄 Choose pages")
    c1, c2 = st.columns(2)
    start = c1.number_input("Start page", 1, total, start_default)
    end = c2.number_input("End page", 1, total, total)

    # Voice settings
    st.subheader("🎙️ Voice")
    voices = {"American": "com", "British": "co.uk", "Indian": "co.in", "Australian": "com.au"}
    voice = st.selectbox("English accent", list(voices.keys()))
    speed = st.select_slider("Playback speed", [0.75, 1.0, 1.25, 1.5, 1.75, 2.0], value=1.0)

    # Text preview, reading time and summary
    if start <= end:
        selected = " ".join(pages_text[start - 1:end]).strip()
        word_count = len(selected.split())
        st.caption(f"{word_count} words | about {max(1, round(word_count / 150 / speed))} min to listen")

        with st.expander("📝 Show text"):
            st.markdown(
                f"<div style='font-size:{font_size}px;line-height:1.6'>{selected[:3000]}</div>",
                unsafe_allow_html=True,
            )
        with st.expander("✨ Quick summary"):
            st.write(simple_summary(selected) if selected else "No text found")

    # Bookmarks
    st.subheader("🔖 Bookmarks")
    b1, b2 = st.columns(2)
    if b1.button("Bookmark start page"):
        if int(start) not in st.session_state.bookmarks:
            st.session_state.bookmarks.append(int(start))
    if b2.button("Clear bookmarks"):
        st.session_state.bookmarks = []
    if st.session_state.bookmarks:
        st.write("Saved pages:", sorted(st.session_state.bookmarks))

    # Read aloud + download
    if st.button("▶️ Read aloud"):
        if start > end:
            st.error("Start page must be less than or equal to end page")
        elif not selected:
            st.error("No readable text found on these pages")
        else:
            with st.spinner("Creating audio..."):
                audio_bytes = make_audio(selected, voice, voices[voice])
            if audio_bytes is None:
                st.error("Voice service is busy. Please try fewer pages or try again later.")
                st.stop()
            audio_player(audio_bytes, speed)
            st.download_button(
                "⬇️ Download as MP3",
                data=audio_bytes,
                file_name="smart_pdf_audio.mp3",
                mime="audio/mpeg",
            )
            st.session_state.history.append(f"{uploaded.name} (pages {start}-{end})")


if st.session_state.logged_in:
    main_app()
else:
    login_page()
