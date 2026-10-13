import io
import re
import base64
from collections import Counter

import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
from gtts import gTTS

st.set_page_config(page_title="Smart PDF App", page_icon="📖")

# ---------- Simple demo users (change these) ----------
USERS = {"admin": "1234", "student": "pdf123"}

# ---------- Session state ----------
defaults = {"logged_in": False, "user": "", "bookmarks": [], "history": []}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------- Login page ----------
def login_page():
    st.title("🔐 Login")
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

    if dark:
        st.markdown(
            "<style>.stApp{background-color:#0e1117;color:#fafafa;}"
            ".stApp p,.stApp label,.stApp h1,.stApp h2,.stApp h3{color:#fafafa;}"
            "</style>",
            unsafe_allow_html=True,
        )

    st.title("📖 Smart PDF App")

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
                buf = io.BytesIO()
                gTTS(text=selected, lang="en", tld=voices[voice]).write_to_fp(buf)
            audio_player(buf.getvalue(), speed)
            st.download_button(
                "⬇️ Download as MP3",
                data=buf.getvalue(),
                file_name="smart_pdf_audio.mp3",
                mime="audio/mpeg",
            )
            st.session_state.history.append(f"{uploaded.name} (pages {start}-{end})")


if st.session_state.logged_in:
    main_app()
else:
    login_page()
