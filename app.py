import streamlit as st
import streamlit.components.v1 as components

from pypdf import PdfReader
from gtts import gTTS

from io import BytesIO
from datetime import datetime
import base64
import re
import html


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="VocaPDF | Smart PDF Voice",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================
# SESSION STATE
# ==========================================

defaults = {
    "logged_in": False,
    "username": "",
    "pdf_text": "",
    "pdf_pages": [],
    "pdf_name": "",
    "audio_bytes": None,
    "audio_name": "pdf_voice.mp3",
    "history": [],
    "dark_mode": False,
    "last_search": "",
    "last_matches": []
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================
# COLORFUL CSS DESIGN
# ==========================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

.stApp {
    background:
        radial-gradient(
            circle at 0% 0%,
            rgba(128, 90, 255, 0.12),
            transparent 35%
        ),
        radial-gradient(
            circle at 100% 10%,
            rgba(0, 210, 255, 0.12),
            transparent 30%
        ),
        linear-gradient(135deg, #f7f7ff, #eef5ff, #fff3fa);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1250px;
}

.hero {
    padding: 36px;
    border-radius: 28px;
    color: white;
    background: linear-gradient(
        120deg,
        #6558f5,
        #a34dff,
        #ed61c5
    );
    box-shadow: 0 15px 35px rgba(112, 80, 220, 0.22);
    margin-bottom: 28px;
}

.hero h1 {
    color: white;
    font-size: 38px;
    font-weight: 800;
}

.hero p {
    color: #f4f0ff;
    font-size: 16px;
}

.section-title {
    font-size: 25px;
    font-weight: 800;
    color: #4338a8;
    margin: 20px 0 12px 0;
}

.feature-card {
    background: rgba(255,255,255,0.92);
    border: 1px solid #e8e5ff;
    border-radius: 22px;
    padding: 22px;
    min-height: 145px;
    box-shadow: 0 8px 25px rgba(63, 55, 130, 0.07);
    margin-bottom: 15px;
}

.feature-icon {
    font-size: 34px;
}

.feature-title {
    font-size: 17px;
    font-weight: 700;
    color: #42358d;
    margin-top: 8px;
}

.feature-text {
    font-size: 13px;
    color: #72718a;
}

.login-box {
    background: rgba(255,255,255,0.96);
    border-radius: 28px;
    padding: 32px;
    box-shadow: 0 15px 45px rgba(75, 60, 160, 0.13);
    border: 1px solid #e8e4ff;
}

.info-card {
    background: linear-gradient(135deg, #ffffff, #f0edff);
    border-radius: 20px;
    padding: 22px;
    border: 1px solid #e5ddff;
    box-shadow: 0 6px 18px rgba(80, 60, 150, 0.06);
}

.info-number {
    color: #7055ee;
    font-size: 28px;
    font-weight: 800;
}

.info-label {
    color: #77728d;
    font-size: 13px;
}

.stButton > button {
    border-radius: 13px;
    border: none;
    font-weight: 600;
    padding: 10px 18px;
    background: linear-gradient(100deg, #6558f5, #bd55e8);
    color: white;
    transition: 0.2s;
}

.stButton > button:hover {
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 7px 18px rgba(101, 88, 245, 0.22);
}

.stTextInput input,
.stTextArea textarea {
    border-radius: 12px;
}

div[data-testid="stFileUploader"] {
    border-radius: 18px;
    padding: 10px;
    background: rgba(255,255,255,0.7);
}

div[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #eeebff, #f9efff);
}

.small-note {
    font-size: 12px;
    color: #77728d;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def extract_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return pages


def make_audio(text, language="en"):
    text = text.strip()

    if not text:
        raise ValueError("No readable text was found.")

    audio_buffer = BytesIO()

    tts = gTTS(
        text=text,
        lang=language,
        slow=False
    )

    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)

    return audio_buffer.getvalue()


def make_summary(text, sentence_count=5):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]

    if not sentences:
        return "No readable text is available for summary."

    return " ".join(sentences[:sentence_count])


def search_pdf(query, pages):
    results = []

    query = query.strip()

    if not query:
        return results

    for page_number, page_text in enumerate(pages, start=1):

        matches = list(
            re.finditer(
                re.escape(query),
                page_text,
                re.IGNORECASE
            )
        )

        if matches:
            snippets = []

            for match in matches[:3]:
                start = max(0, match.start() - 65)
                end = min(len(page_text), match.end() + 100)

                snippet = page_text[start:end].replace("\n", " ")

                snippets.append(snippet)

            results.append({
                "page": page_number,
                "count": len(matches),
                "snippets": snippets
            })

    return results


def audio_player(audio_bytes, filename="pdf_voice.mp3"):

    encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")

    safe_filename = re.sub(
        r"[^a-zA-Z0-9_.-]",
        "_",
        filename
    )

    player_html = f"""
    <div style="
        background: linear-gradient(135deg, #f2edff, #fff0fa);
        border: 1px solid #ded4ff;
        border-radius: 20px;
        padding: 22px;
        font-family: Arial, sans-serif;
    ">

        <div style="
            font-size: 20px;
            font-weight: bold;
            color: #5140b8;
            margin-bottom: 15px;
        ">
            🎧 Your Audio Player
        </div>

        <audio id="audio" controls
            style="width:100%; margin-bottom:15px;">
            <source
                src="data:audio/mpeg;base64,{encoded_audio}"
                type="audio/mpeg">
            Your browser does not support audio playback.
        </audio>

        <div style="margin:12px 0;">
            <label style="font-weight:bold;color:#5140b8;">
                🔊 Volume
            </label>

            <input
                id="volume"
                type="range"
                min="0"
                max="100"
                value="100"
                style="width:100%;"
                oninput="changeVolume(this.value)">
            <span id="volumeLabel">100%</span>
        </div>

        <div style="margin:12px 0;">
            <label style="font-weight:bold;color:#5140b8;">
                ⏩ Playback Speed
            </label>

            <select
                id="speed"
                onchange="changeSpeed(this.value)"
                style="
                    padding:9px;
                    border-radius:9px;
                    border:1px solid #c9bfff;
                    margin-left:10px;
                ">

                <option value="0.5">0.5x</option>
                <option value="0.75">0.75x</option>
                <option value="1" selected>1x Normal</option>
                <option value="1.25">1.25x</option>
                <option value="1.5">1.5x</option>
                <option value="1.75">1.75x</option>
                <option value="2">2x</option>

            </select>
        </div>

        <p style="color:#77718d;font-size:12px;">
            Use the audio controls to play, pause, seek and replay.
        </p>

        <a
            download="{html.escape(safe_filename, quote=True)}"
            href="data:audio/mpeg;base64,{encoded_audio}"
            style="
                display:inline-block;
                background:linear-gradient(100deg,#6558f5,#bd55e8);
                color:white;
                text-decoration:none;
                padding:11px 18px;
                border-radius:11px;
                font-weight:bold;
            ">
            📥 Download Audio
        </a>

    </div>

    <script>

    const audio = document.getElementById("audio");

    function changeVolume(value) {{
        audio.volume = Number(value) / 100;

        document.getElementById("volumeLabel").innerText =
            value + "%";
    }}

    function changeSpeed(value) {{
        audio.playbackRate = Number(value);
    }}

    </script>
    """

    components.html(
        player_html,
        height=390,
        scrolling=False
    )


# ==========================================
# LOGIN PAGE
# ==========================================

def show_login():

    left, right = st.columns([1.1, 1])

    with left:

        st.markdown("""
        <div class="hero" style="margin-top:35px; min-height:380px;">

            <div style="font-size:65px;">🎧📚</div>

            <h1>VocaPDF</h1>

            <p style="font-size:20px;">
                Turn your PDF into an audio experience.
            </p>

            <hr style="border-color:rgba(255,255,255,0.3);">

            <p>✨ Listen to your documents</p>
            <p>🔍 Find words in seconds</p>
            <p>🎵 Control your listening experience</p>
            <p>📖 Read one page or your complete PDF</p>

        </div>
        """, unsafe_allow_html=True)

    with right:

        st.markdown("<br><br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="login-box">

            <div style="font-size:42px;">💜</div>

            <h2 style="color:#5140b8;">
                Welcome Back!
            </h2>

            <p style="color:#77718d;">
                Login to explore your smart PDF workspace.
            </p>

        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):

            username = st.text_input(
                "👤 Username",
                placeholder="Enter your username"
            )

            password = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Enter your password"
            )

            submitted = st.form_submit_button(
                "✨ Login to VocaPDF",
                use_container_width=True
            )

            if submitted:

                # DEMO LOGIN:
                # Username: student
                # Password: pdf123

                if username == "student" and password == "pdf123":

                    st.session_state.logged_in = True
                    st.session_state.username = username

                    st.success("Login successful!")

                    st.rerun()

                else:
                    st.error(
                        "Incorrect username or password. "
                        "Please try again."
                    )

        st.caption(
            "Demo login: student  |  Password: pdf123"
        )

        st.caption(
            "This is a demonstration login, not a production "
            "authentication system."
        )


# ==========================================
# DASHBOARD
# ==========================================

def show_dashboard():

    with st.sidebar:

        st.markdown("# 🎧 VocaPDF")

        st.markdown("---")

        st.markdown(
            f"### 👋 Hi, {st.session_state.username}!"
        )

        st.toggle(
            "🌙 Dark Mode",
            key="dark_mode"
        )

        st.markdown("---")

        menu = st.radio(
            "YOUR WORKSPACE",
            [
                "🏠 Dashboard",
                "📄 PDF Reader",
                "🔍 Word Finder",
                "🎙️ PDF to Voice",
                "📝 PDF Summary",
                "🕘 History"
            ]
        )

        st.markdown("---")

        if st.button(
            "🚪 Logout",
            use_container_width=True
        ):

            st.session_state.logged_in = False
            st.session_state.username = ""

            st.rerun()

    # Dark mode colors
    if st.session_state.dark_mode:

        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg,#17162a,#24203b);
            color: #f5f2ff;
        }

        .section-title {
            color: #c6baff;
        }

        .feature-card {
            background: #292541;
            border-color: #49416d;
        }

        .feature-title {
            color: #e2d9ff;
        }

        .feature-text {
            color: #d0c9e5;
        }

        div[data-testid="stSidebar"] {
            background: #211e35;
        }

        </style>
        """, unsafe_allow_html=True)

    # --------------------------------------
    # DASHBOARD HOME
    # --------------------------------------

    if menu == "🏠 Dashboard":

        st.markdown("""
        <div class="hero">

            <h1>Welcome to Your Smart Workspace! 💜</h1>

            <p>
                Read PDFs, discover important words and listen
                to your documents with your own audio settings.
            </p>

        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("""
            <div class="info-card">
                <div class="info-number">📄</div>
                <div class="info-label">Smart PDF Reader</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div class="info-card">
                <div class="info-number">🔍</div>
                <div class="info-label">Word & Page Finder</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown("""
            <div class="info-card">
                <div class="info-number">🎧</div>
                <div class="info-label">Audio Experience</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(
            '<div class="section-title">✨ Explore Features</div>',
            unsafe_allow_html=True
        )

        features = [
            ("📄", "PDF Reader", "Upload and read PDF documents."),
            ("🔍", "Word Finder", "Find words and matching pages."),
            ("🎙️", "PDF to Voice", "Convert document text to audio."),
            ("🎚️", "Audio Controls", "Adjust volume and playback speed."),
            ("📝", "Quick Summary", "Create a basic text summary."),
            ("🕘", "History", "View previous conversion activities.")
        ]

        columns = st.columns(3)

        for index, feature in enumerate(features):

            with columns[index % 3]:

                st.markdown(f"""
                <div class="feature-card">

                    <div class="feature-icon">
                        {feature[0]}
                    </div>

                    <div class="feature-title">
                        {feature[1]}
                    </div>

                    <div class="feature-text">
                        {feature[2]}
                    </div>

                </div>
                """, unsafe_allow_html=True)

        st.info(
            "👈 Choose a feature from the sidebar to get started."
        )

        st.markdown(
            '<div class="section-title">📂 Upload Your PDF</div>',
            unsafe_allow_html=True
        )

        uploaded_file = st.file_uploader(
            "Choose a PDF document",
            type=["pdf"],
            key="home_pdf_upload"
        )

        if uploaded_file:

            if st.button("📥 Load PDF", key="home_load"):

                try:

                    with st.spinner("Reading your PDF..."):

                        pages = extract_pdf(uploaded_file)

                    st.session_state.pdf_pages = pages

                    st.session_state.pdf_text = "\n".join(pages)

                    st.session_state.pdf_name = uploaded_file.name

                    st.session_state.audio_bytes = None

                    st.success(
                        f"Loaded {uploaded_file.name} successfully!"
                    )

                    st.rerun()

                except Exception as error:

                    st.error(f"Could not read this PDF: {error}")

    # --------------------------------------
    # PDF READER
    # --------------------------------------

    elif menu == "📄 PDF Reader":

        st.markdown(
            '<div class="section-title">📖 Smart PDF Reader</div>',
            unsafe_allow_html=True
        )

        uploaded_file = st.file_uploader(
            "Upload a PDF",
            type=["pdf"],
            key="reader_upload"
        )

        if uploaded_file:

            if st.button("📂 Open PDF"):

                try:

                    with st.spinner("Extracting PDF text..."):

                        pages = extract_pdf(uploaded_file)

                    st.session_state.pdf_pages = pages

                    st.session_state.pdf_text = "\n".join(pages)

                    st.session_state.pdf_name = uploaded_file.name

                    st.session_state.audio_bytes = None

                    st.success("PDF loaded successfully!")

                except Exception as error:

                    st.error(f"PDF error: {error}")

        pages = st.session_state.pdf_pages

        if pages:

            st.success(
                f"📄 {st.session_state.pdf_name} | "
                f"{len(pages)} pages"
            )

            selected_page = st.selectbox(
                "Select page",
                options=list(range(1, len(pages) + 1))
            )

            page_text = pages[selected_page - 1]

            st.text_area(
                f"Page {selected_page} Text",
                value=page_text,
                height=400
            )

            st.caption(
                f"Characters on this page: {len(page_text)}"
            )

            if st.button("🎙️ Convert This Page to Voice"):

                if not page_text.strip():

                    st.warning("This page has no extractable text.")

                else:

                    try:

                        with st.spinner("Creating audio..."):

                            audio = make_audio(page_text, "en")

                        st.session_state.audio_bytes = audio

                        st.session_state.audio_name = (
                            f"page_{selected_page}_voice.mp3"
                        )

                        st.success("Audio is ready!")

                    except Exception as error:

                        st.error(f"Audio conversion failed: {error}")

            if st.session_state.audio_bytes:

                audio_player(
                    st.session_state.audio_bytes,
                    st.session_state.audio_name
                )

        else:

            st.info("Upload a PDF to start reading.")


    # --------------------------------------
    # WORD FINDER
    # --------------------------------------

    elif menu == "🔍 Word Finder":

        st.markdown(
            '<div class="section-title">🔎 Find Words in Your PDF</div>',
            unsafe_allow_html=True
        )

        uploaded_file = st.file_uploader(
            "Upload a PDF",
            type=["pdf"],
            key="finder_upload"
        )

        if uploaded_file:

            if st.button("Load PDF", key="finder_load"):

                try:

                    pages = extract_pdf(uploaded_file)
