import io
import re
import html
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
defaults = {"logged_in": False, "user": "", "bookmarks": [], "history": [], "audio": None}
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
    #MainMenu, footer, [data-testid="stToolbar"] {{visibility: hidden;}}
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

MAX_CHARS = 20000  # about 8 to 10 pages of text per audio

EDGE_VOICES = {
    "American": "en-US-AriaNeural",
    "British": "en-GB-SoniaNeural",
    "Indian": "en-IN-NeerjaNeural",
    "Australian": "en-AU-NatashaNeural",
}


def make_audio(text, accent, tld, pitch="+0Hz", volume="+0%"):
    """Try edge-tts first, then gTTS. Returns MP3 bytes or None."""
    text = text[:MAX_CHARS]
    if edge_tts is not None:
        try:
            async def run():
                data = b""
                comm = edge_tts.Communicate(text, EDGE_VOICES[accent], pitch=pitch, volume=volume)
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
        gTTS(text=text[:4000], lang="en", tld=tld).write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None


def set_start_page(page):
    st.session_state.start_page = page


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
    """Audio player: play/pause, 10s skip, speed and a loudness (boldness) slider."""
    b64 = base64.b64encode(audio_bytes).decode()
    html = f"""
    <div style="font-family:sans-serif">
      <audio id="player" controls style="width:100%"></audio>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button onclick="skip(-10)">⏪ 10s</button>
        <button onclick="skip(10)">10s ⏩</button>
      </div>
      <div style="margin-top:10px">
        🔊 Loudness: <b id="lv">100</b>%
        <input id="loud" type="range" min="50" max="300" value="100" style="width:100%">
      </div>
    </div>
    <script>
      const bin = atob("{b64}");
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const url = URL.createObjectURL(new Blob([bytes], {{type: "audio/mpeg"}}));
      const p = document.getElementById('player');
      p.src = url;
      p.playbackRate = {speed};
      p.addEventListener('play', () => p.playbackRate = {speed});

      let ctx, gain;
      function setupGain() {{
        if (ctx) return;
        ctx = new (window.AudioContext || window.webkitAudioContext)();
        const src = ctx.createMediaElementSource(p);
        gain = ctx.createGain();
        src.connect(gain); gain.connect(ctx.destination);
      }}
      p.addEventListener('play', () => {{
        setupGain();
        if (ctx.state === 'suspended') ctx.resume();
        gain.gain.value = document.getElementById('loud').value / 100;
      }});
      document.getElementById('loud').addEventListener('input', (e) => {{
        document.getElementById('lv').textContent = e.target.value;
        if (gain) gain.gain.value = e.target.value / 100;
      }});
      function skip(s) {{ p.currentTime = Math.max(0, p.currentTime + s); }}
    </script>
    """
    components.html(html, height=190)


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
            if st.session_state.get("last_word") != word:
                st.session_state.start_page = found[0]
                st.session_state.last_word = word
        else:
            st.warning("Word not found in this PDF")

    # Page range
    st.subheader("📄 Choose pages")
    c1, c2 = st.columns(2)
    if "start_page" not in st.session_state or st.session_state.start_page > total:
        st.session_state.start_page = 1
    start = c1.number_input("Start page", 1, total, key="start_page")
    end = c2.number_input("End page", 1, total, total)

    # Voice settings
    st.subheader("🎙️ Voice")
    voices = {"American": "com", "British": "co.uk", "Indian": "co.in", "Australian": "com.au"}
    voice = st.selectbox("English accent", list(voices.keys()))
    style = st.select_slider("Voice style", ["Soft", "Normal", "Bold"], value="Normal")
    speed = st.select_slider("Playback speed", [0.75, 1.0, 1.25, 1.5, 1.75, 2.0], value=1.0)

    # Text preview, reading time and summary
    selected = ""
    if start <= end:
        selected = " ".join(pages_text[start - 1:end]).strip()
        word_count = len(selected.split())
        st.caption(f"{word_count} words | about {max(1, round(word_count / 150 / speed))} min to listen")

        with st.expander("📝 Show text"):
            st.markdown(
                f"<div style='font-size:{font_size}px;line-height:1.6'>{html.escape(selected[:3000])}</div>",
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
        st.write("Saved pages (tap one to set it as the start page):")
        saved = sorted(st.session_state.bookmarks)
        cols = st.columns(min(len(saved), 4))
        for i, p in enumerate(saved):
            cols[i % len(cols)].button(
                f"Page {p}", key=f"bm_{p}", on_click=set_start_page, args=(p,)
            )

    # Read aloud
    if st.button("▶️ Read aloud"):
        if start > end:
            st.error("Start page must be less than or equal to end page")
        elif not selected:
            st.error("No readable text found on these pages")
        else:
            if len(selected) > MAX_CHARS:
                st.info("These pages are long, so only the first part will be read. Choose fewer pages to read the rest.")
            with st.spinner("Creating audio..."):
                styles = {"Soft": ("+8Hz", "-10%"), "Normal": ("+0Hz", "+0%"), "Bold": ("-15Hz", "+30%")}
                pitch, vol = styles[style]
                audio_bytes = make_audio(selected, voice, voices[voice], pitch, vol)
            if audio_bytes is None:
                st.error("Voice service is busy. Please try fewer pages or try again later.")
            else:
                st.session_state.audio = {"bytes": audio_bytes, "speed": speed}
                st.session_state.history.append(f"{uploaded.name} (pages {start}-{end})")

    # Show the player and download button (stays visible after other clicks)
    if st.session_state.audio:
        audio_player(st.session_state.audio["bytes"], st.session_state.audio["speed"])
        st.download_button(
            "⬇️ Download as MP3",
            data=st.session_state.audio["bytes"],
            file_name="smart_pdf_audio.mp3",
            mime="audio/mpeg",
        )


if st.session_state.logged_in:
    main_app()
else:
    login_page()
