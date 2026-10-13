import io
import re
import base64
import asyncio
import hashlib
import html
from datetime import datetime
from collections import Counter

import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
from gtts import gTTS

try:
    import edge_tts
except ImportError:
    edge_tts = None


# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Smart PDF App",
    page_icon="📖",
    layout="wide"
)


# ==========================================
# 2. DEMO LOGIN
# ==========================================

USERS = {
    "admin": "1234",
    "student": "pdf123"
}


# ==========================================
# 3. SESSION STATE
# ==========================================

defaults = {
    "logged_in": False,
    "user": "",
    "history": [],
    "dark_mode": False,
    "audio_bytes": None,
    "audio_hash": None,
    "audio_settings": None,
    "last_pdf_hash": None,
    "search_audio": {},
    "selected_page": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================
# 4. VOICE CONFIGURATION
# ==========================================

EDGE_VOICES = {
    "American Female": "en-US-AriaNeural",
    "American Male": "en-US-GuyNeural",
    "British Female": "en-GB-SoniaNeural",
    "Indian Female": "en-IN-NeerjaNeural",
    "Australian Female": "en-AU-NatashaNeural",
}

LANGUAGES = {
    "English": "en",
    "Tamil": "ta",
    "Hindi": "hi",
    "Telugu": "te",
    "Malayalam": "ml",
}


# ==========================================
# 5. DESIGN
# ==========================================

def inject_css(dark=False):

    if dark:
        background = "#111827"
        text_color = "#f9fafb"
        card_background = "#1f2937"
    else:
        background = "#f4f7ff"
        text_color = "#1e293b"
        card_background = "#ffffff"

    st.markdown(
        f"""
        <style>

        #MainMenu, footer {{
            visibility: hidden;
        }}

        .stApp {{
            background: {background};
            color: {text_color};
        }}

        .block-container {{
            max-width: 1150px;
            padding-top: 1.5rem;
        }}

        .hero {{
            background: linear-gradient(
                120deg,
                #6366f1,
                #ec4899,
                #f59e0b
            );
            padding: 30px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 25px;
            color: white;
        }}

        .hero h1 {{
            color: white !important;
            font-size: 2.2rem;
        }}

        .hero p {{
            color: white !important;
        }}

        .stButton > button,
        .stDownloadButton > button {{
            border-radius: 10px;
            font-weight: 600;
        }}

        </style>
        """,
        unsafe_allow_html=True
    )


def hero(title, subtitle):

    st.markdown(
        f"""
        <div class="hero">
            <h1>{html.escape(title)}</h1>
            <p>{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================
# 6. LOGIN PAGE
# ==========================================

def login_page():

    inject_css()

    hero(
        "📖 Smart PDF App",
        "Read, Listen and Learn from PDF"
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        st.subheader("🔐 Login")

        username = st.text_input(
            "Username"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button(
            "Login",
            use_container_width=True
        ):

            if USERS.get(username) == password and password:

                st.session_state.logged_in = True
                st.session_state.user = username

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

        with st.expander("Demo Login Details"):

            st.write("Username: admin")
            st.write("Password: 1234")

            st.write("Username: student")
            st.write("Password: pdf123")


# ==========================================
# 7. PDF TEXT EXTRACTION
# ==========================================

def extract_pdf_text(uploaded_file):

    reader = PdfReader(uploaded_file)

    pages_text = []

    for page in reader.pages:

        text = page.extract_text() or ""

        pages_text.append(text)

    return pages_text


# ==========================================
# 8. TEXT STATISTICS
# ==========================================

def get_statistics(text):

    words = re.findall(
        r"\b[\w'-]+\b",
        text,
        flags=re.UNICODE
    )

    sentences = [
        sentence
        for sentence in re.split(r"[.!?]+", text)
        if sentence.strip()
    ]

    return {
        "words": len(words),
        "characters": len(text),
        "sentences": len(sentences),
        "reading_time": max(
            1,
            round(len(words) / 150)
        )
    }


# ==========================================
# 9. QUICK SUMMARY
# ==========================================

def simple_summary(text, num_sentences=5):

    if not text.strip():
        return "No readable text found."

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip()
    )

    sentences = [
        sentence
        for sentence in sentences
        if sentence.strip()
    ]

    if len(sentences) <= num_sentences:
        return text

    words = re.findall(
        r"[a-zA-Z]{3,}",
        text.lower()
    )

    frequencies = Counter(words)

    scored_sentences = []

    for index, sentence in enumerate(sentences):

        sentence_words = re.findall(
            r"[a-zA-Z]{3,}",
            sentence.lower()
        )

        score = sum(
            frequencies.get(word, 0)
            for word in sentence_words
        )

        scored_sentences.append(
            (score, index, sentence)
        )

    selected = sorted(
        scored_sentences,
        key=lambda item: item[0],
        reverse=True
    )[:num_sentences]

    selected.sort(
        key=lambda item: item[1]
    )

    return " ".join(
        sentence
        for _, _, sentence in selected
    )


# ==========================================
# 10. TEXT TO VOICE
# ==========================================

def make_audio(text, language, voice):

    if not text.strip():
        return None

    text = text.strip()[:5000]

    # Edge TTS for English neural voices
    if language == "English" and edge_tts is not None:

        try:

            async def generate_audio():

                audio_buffer = io.BytesIO()

                communicator = edge_tts.Communicate(
                    text,
                    EDGE_VOICES[voice]
                )

                async for chunk in communicator.stream():

                    if chunk["type"] == "audio":

                        audio_buffer.write(
                            chunk["data"]
                        )

                return audio_buffer.getvalue()

            audio_data = asyncio.run(
                generate_audio()
            )

            if audio_data:
                return audio_data

        except Exception:
            pass

    # gTTS fallback
    try:

        audio_buffer = io.BytesIO()

        gTTS(
            text=text[:3000],
            lang=LANGUAGES[language],
            slow=False
        ).write_to_fp(audio_buffer)

        return audio_buffer.getvalue()

    except Exception:

        return None


# ==========================================
# 11. AUDIO PLAYER
# ==========================================

def audio_player(audio_bytes, speed=1.0):

    encoded_audio = base64.b64encode(
        audio_bytes
    ).decode("utf-8")

    html_code = f"""
    <audio
        id="pdfAudio"
        controls
        style="width:100%"
    >
        <source
            src="data:audio/mpeg;base64,{encoded_audio}"
            type="audio/mpeg"
        >
    </audio>

    <div style="margin-top:10px">

        <button onclick="skipAudio(-10)">
            ⏪ Back 10s
        </button>

        <button onclick="skipAudio(10)">
            Forward 10s ⏩
        </button>

    </div>

    <script>

    const player = document.getElementById("pdfAudio");

    player.playbackRate = {speed};

    player.addEventListener("play", function() {{
        player.playbackRate = {speed};
    }});

    function skipAudio(seconds) {{

        player.currentTime = Math.max(
            0,
            player.currentTime + seconds
        );

    }}

    </script>
    """

    components.html(
        html_code,
        height=130
    )


# ==========================================
# 12. WORD SEARCH ENGINE
# ==========================================

def find_word_in_pdf(query, pages_text):

    results = []

    query = query.strip()

    if not query:
        return results

    pattern = re.compile(
        re.escape(query),
        re.IGNORECASE
    )

    for page_index, page_text in enumerate(pages_text):

        matches = list(
            pattern.finditer(page_text)
        )

        if matches:

            snippets = []

            for match in matches[:5]:

                left = max(
                    0,
                    match.start() - 70
                )

                right = min(
                    len(page_text),
                    match.end() + 100
                )

                snippets.append(
                    page_text[left:right]
                )

            results.append({
                "page": page_index + 1,
                "count": len(matches),
                "text": page_text,
                "snippets": snippets
            })

    return results


# ==========================================
# 13. MAIN APPLICATION
# ==========================================

def main_app():

    # SIDEBAR SETTINGS

    st.sidebar.title("⚙️ Settings")

    st.sidebar.write(
        f"👤 Logged in as: {st.session_state.user}"
    )

    dark = st.sidebar.toggle(
        "🌙 Dark Mode",
        value=st.session_state.dark_mode
    )

    st.session_state.dark_mode = dark

    font_size = st.sidebar.slider(
        "🔠 Text Size",
        min_value=12,
        max_value=28,
        value=16
    )

    if st.sidebar.button("🚪 Logout"):

        st.session_state.logged_in = False

        st.session_state.audio_bytes = None

        st.rerun()

    inject_css(dark)

    hero(
        "📖 Smart PDF App",
        "Upload PDF • Find Words • Read • Listen"
    )

    # PDF UPLOAD

    st.subheader("📤 Upload PDF")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"]
    )

    if uploaded_file is None:

        st.info(
            "Upload a PDF file to begin."
        )

        if st.session_state.history:

            st.subheader("🕘 Reading History")

            for item in reversed(
                st.session_state.history[-10:]
            ):

                st.write("📄", item)

        return

    # FILE IDENTIFICATION

    file_bytes = uploaded_file.getvalue()

    file_hash = hashlib.sha256(
        file_bytes
    ).hexdigest()

    if file_hash != st.session_state.last_pdf_hash:

        st.session_state.last_pdf_hash = file_hash

        st.session_state.audio_bytes = None

        st.session_state.audio_hash = None

        st.session_state.audio_settings = None

        st.session_state.search_audio = {}

        st.session_state.selected_page = None

    # EXTRACT PDF

    try:

        pages_text = extract_pdf_text(
            io.BytesIO(file_bytes)
        )

    except Exception:

        st.error(
            "Unable to open this PDF. "
            "Please upload a valid PDF."
        )

        return

    total_pages = len(pages_text)

    if total_pages == 0:

        st.error("This PDF contains no pages.")

        return

    st.success(
        f"PDF loaded successfully: {total_pages} pages"
    )

    # PDF INFORMATION

    with st.expander("📑 PDF Information"):

        st.write(
            "Filename:",
            uploaded_file.name
        )

        st.write(
            "Total pages:",
            total_pages
        )

        st.write(
            "File size:",
            f"{len(file_bytes) / 1024:.2f} KB"
        )

    # ======================================
    # WORD SEARCH AND PAGE FINDER
    # ======================================

    st.divider()

    st.subheader("🔍 Word Search & Page Finder")

    st.write(
        "Enter a word to find which PDF pages contain it."
    )

    search_query = st.text_input(
        "Search Word or Phrase",
        placeholder="Example: Python"
    )

    search_results = []

    if search_query.strip():

        search_results = find_word_in_pdf(
            search_query,
            pages_text
        )

        if search_results:

            total_matches = sum(
                result["count"]
                for result in search_results
            )

            st.success(
                f"Found '{search_query}' "
                f"{total_matches} time(s) "
                f"on {len(search_results)} page(s)."
            )

            st.subheader("📍 Search Results")

            for result in search_results:

                page_number = result["page"]

                with st.expander(
                    f"📄 Page {page_number} | "
                    f"{result['count']} occurrence(s)"
                ):

                    st.write("**Matching text:**")

                    for snippet in result["snippets"]:

                        st.write(
                            "..." + snippet + "..."
                        )

                    col1, col2 = st.columns(2)

                    with col1:

                        if st.button(
                            f"📖 Read Page {page_number}",
                            key=f"read_{page_number}"
                        ):

                            st.session_state.selected_page = (
                                page_number
                            )

                    with col2:

                        if st.button(
                            f"🔊 Prepare Audio",
                            key=f"audio_{page_number}"
                        ):

                            st.session_state.selected_page = (
                                page_number
                            )

                            st.session_state[
                                "generate_page_audio"
                            ] = page_number

        else:

            st.warning(
                f"'{search_query}' was not found in this PDF."
            )

    # ======================================
    # PAGE SELECTOR
    # ======================================

    st.divider()

    st.subheader("📄 Choose Pages")

    col1, col2 = st.columns(2)

    with col1:

        start_page = st.number_input(
            "Start Page",
            min_value=1,
            max_value=total_pages,
            value=1
        )

    with col2:

        end_page = st.number_input(
            "End Page",
            min_value=1,
            max_value=total_pages,
            value=total_pages
        )

    if start_page > end_page:

        st.error(
            "Start Page must be less than or equal to End Page."
        )

        return

    # ======================================
    # SELECTED PAGE READER
    # ======================================

    selected_page = st.session_state.selected_page

    if selected_page and 1 <= selected_page <= total_pages:

        st.subheader(
            f"📖 Selected Search Result: Page {selected_page}"
        )

        selected_page_text = pages_text[
            selected_page - 1
        ]

        st.text_area(
            "Page Text",
            value=selected_page_text,
            height=250,
            key=f"selected_text_{selected_page}"
        )

        st.download_button(
            "📥 Download Selected Page Text",
            data=selected_page_text,
            file_name=f"page_{selected_page}.txt",
            mime="text/plain",
            key=f"download_page_text_{selected_page}"
        )

    # ======================================
    # TEXT EXTRACTION
    # ======================================

    selected_text = "\n\n".join(
        pages_text[
            int(start_page) - 1:int(end_page)
        ]
    ).strip()

    st.divider()

    st.subheader("📝 Extracted Text")

    if selected_text:

        stats = get_statistics(
            selected_text
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Words",
            stats["words"]
        )

        c2.metric(
            "Characters",
            stats["characters"]
        )

        c3.metric(
            "Sentences",
            stats["sentences"]
        )

        c4.metric(
            "Reading Time",
            f'{stats["reading_time"]} min'
        )

        progress = int(
            int(end_page) / total_pages * 100
        )

        st.subheader("📈 Reading Progress")

        st.progress(
            progress / 100
        )

        st.caption(
            f"Selected end page: {end_page} of {total_pages}"
        )

        with st.expander(
            "Show Extracted Text",
            expanded=True
        ):

            st.text_area(
                "PDF Text",
                value=selected_text[:30000],
                height=300,
                key="extracted_text_area"
            )

        st.download_button(
            "📥 Download Extracted Text",
            data=selected_text,
            file_name="extracted_text.txt",
            mime="text/plain"
        )

        # COPY TEXT

        safe_text = html.escape(
            selected_text[:20000]
        )

        components.html(
            f"""
            <textarea id="copyArea"
                style="width:100%;height:100px"
            >{safe_text}</textarea>

            <button onclick="
                navigator.clipboard.writeText(
                    document.getElementById('copyArea').value
                ).then(() => alert('Text copied!'));
            ">
                📋 Copy Text
            </button>
            """,
            height=150
        )

        # SUMMARY

        with st.expander("✨ Quick Summary"):

            summary = simple_summary(
                selected_text
            )

            st.write(summary)

            st.download_button(
                "📥 Download Summary",
                data=summary,
                file_name="summary.txt",
                mime="text/plain"
            )

    else:

        st.warning(
            "No readable text found in the selected pages."
        )

    # ======================================
    # VOICE SETTINGS
    # ======================================

    st.divider()

    st.subheader("🎙️ Voice Settings")

    language = st.selectbox(
        "Select Language",
        list(LANGUAGES.keys())
    )

    if language == "English":

        voice = st.selectbox(
            "Select Voice",
            list(EDGE_VOICES.keys())
        )

    else:

        voice = ""

        st.caption(
            "Voice generation will use the selected language."
        )

    speed = st.select_slider(
        "⏩ Playback Speed",
        options=[
            0.75,
            1.0,
            1.25,
            1.5,
            1.75,
            2.0
        ],
        value=1.0
    )

    # ======================================
    # GENERATE AUDIO FOR SELECTED PAGES
    # ======================================

    st.divider()

    st.subheader("
