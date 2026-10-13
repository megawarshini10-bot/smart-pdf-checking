import streamlit as st
from pypdf import PdfReader
from gtts import gTTS
from io import BytesIO
from datetime import datetime
import re
import html

# =========================
# PAGE SETTINGS
# =========================

st.set_page_config(
    page_title="VocaPDF",
    page_icon="🎧",
    layout="wide"
)

# =========================
# SESSION STATE
# =========================

defaults = {
    "logged_in": False,
    "username": "",
    "pages": [],
    "pdf_name": "",
    "audio": None,
    "history": [],
    "summary": ""
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =========================
# ATTRACTIVE DESIGN
# =========================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

.stApp {
    background: linear-gradient(135deg,#f5f0ff,#edf7ff,#fff0f7);
}

.block-container {
    max-width: 1200px;
    padding-top: 2rem;
}

.hero {
    background: linear-gradient(120deg,#6157f5,#a44dff,#ef65c5);
    padding: 35px;
    border-radius: 25px;
    color: white;
    margin-bottom: 25px;
    box-shadow: 0 10px 30px #b8a7ee66;
}

.hero h1 {
    color: white;
    font-size: 38px;
    font-weight: 800;
}

.card {
    background: white;
    border: 1px solid #e5dcff;
    padding: 23px;
    border-radius: 20px;
    margin-bottom: 15px;
    box-shadow: 0 6px 20px #8c7ac51c;
}

.card h3 {
    color: #6651d9;
}

.stButton > button {
    background: linear-gradient(100deg,#6658f5,#bd54e8);
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    min-height: 42px;
}

.stButton > button:hover {
    color: white;
    border: 1px solid #a78bfa;
}

div[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#eae6ff,#fff0fa);
}
</style>
""", unsafe_allow_html=True)


# =========================
# PDF FUNCTIONS
# =========================

def read_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    return [page.extract_text() or "" for page in reader.pages]


def create_audio(text, language):
    text = text.strip()

    if not text:
        raise ValueError("PDF text is empty.")

    output = BytesIO()

    tts = gTTS(text=text, lang=language)
    tts.write_to_fp(output)

    return output.getvalue()


def create_summary(text, number=5):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    return " ".join(sentences[:number])


def show_audio(audio_bytes, filename):
    if not audio_bytes:
        st.warning("No audio is available. Please generate audio first.")
        return

    st.markdown("""
    <div class="card">
        <h3>Audio Studio</h3>
        <p>Use the player below to listen to your generated audio.</p>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit's native audio player is more reliable than an HTML data-URI player.
    st.audio(audio_bytes, format="audio/mp3")

    st.download_button(
        label="Download Audio",
        data=audio_bytes,
        file_name=filename,
        mime="audio/mpeg",
        use_container_width=True,
        key="download_" + re.sub(r"[^a-zA-Z0-9_]", "_", filename)
    )


# =========================
# LOGIN PAGE
# =========================

def login_page():
    left, right = st.columns([1.2, 1])

    with left:
        st.markdown("""
        <div class="hero">
            <div style="font-size:60px;">🎧📚</div>
            <h1>VocaPDF</h1>
            <h3 style="color:white;">Your Smart PDF Voice Assistant</h3>
            <p>✨ Read your PDFs</p>
            <p>🎙️ Listen to your documents</p>
            <p>🔍 Find important words</p>
            <p>📚 Enjoy a colourful workspace</p>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown("""
        <div class="card">
            <h2>📚 Welcome Back!</h2>
            <p>Login to your personal workspace.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("👤 Username")
            password = st.text_input("🔒 Password", type="password")
            submitted = st.form_submit_button(
                "✨ Login",
                use_container_width=True
            )

        if submitted:
            if username == "student" and password == "pdf123":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Incorrect username or password.")

        st.info("Demo Username: student")
        st.info("Demo Password: pdf123")


# =========================
# MAIN DASHBOARD
# =========================

def dashboard():
    with st.sidebar:
        st.markdown("# 🎧 VocaPDF")
        st.markdown(f"### Hi, {st.session_state.username}! 👋")

        page = st.radio(
            "MENU",
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

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    # =========================
    # HOME
    # =========================

    if page == "🏠 Dashboard":
        st.markdown("""
        <div class="hero">
            <h1>Welcome to VocaPDF! 📚</h1>
            <p>Your documents. Your voice. Your experience.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div class="card">
                <h3>📄 PDF Reader</h3>
                <p>Read your PDF document page by page.</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="card">
                <h3>🔍 Word Finder</h3>
                <p>Search for words inside your document.</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div class="card">
                <h3>🎙️ Voice Studio</h3>
                <p>Convert readable PDF text into audio.</p>
            </div>
            """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "📂 Upload your PDF",
            type=["pdf"],
            key="home_upload"
        )

        if uploaded and st.button("Load PDF"):
            try:
                with st.spinner("Reading PDF..."):
                    st.session_state.pages = read_pdf(uploaded)
                    st.session_state.pdf_name = uploaded.name
                    st.session_state.audio = None

                st.success("PDF loaded successfully!")
                st.rerun()

            except Exception as error:
                st.error(f"Unable to read PDF: {error}")

    # =========================
    # PDF READER
    # =========================

    elif page == "📄 PDF Reader":
        st.markdown("""
        <div class="hero">
            <h1>📖 PDF Reader</h1>
            <p>Read your document one page at a time.</p>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            key="reader_upload"
        )

        if uploaded and st.button("Open PDF"):
            try:
                st.session_state.pages = read_pdf(uploaded)
                st.session_state.pdf_name = uploaded.name
                st.session_state.audio = None
                st.success("PDF loaded!")
            except Exception as error:
                st.error(f"Unable to read PDF: {error}")

        pages = st.session_state.pages

        if pages:
            st.success(f"Document: {st.session_state.pdf_name}")

            selected_page = st.selectbox(
                "Select page",
                range(1, len(pages) + 1)
            )

            text = pages[selected_page - 1]

            st.text_area(
                "Page Content",
                value=text,
                height=350
            )

            if st.button("🎙️ Convert This Page"):
                try:
                    with st.spinner("Generating audio..."):
                        st.session_state.audio = create_audio(text, "en")

                    st.success("Audio generated!")

                except Exception as error:
                    st.error(f"Audio error: {error}")

            if st.session_state.audio:
                show_audio(
                    st.session_state.audio,
                    "pdf_page_audio.mp3"
                )

    # =========================
    # WORD FINDER
    # =========================

    elif page == "🔍 Word Finder":
        st.markdown("""
        <div class="hero">
            <h1>🔍 Word Finder</h1>
            <p>Find a word or phrase in your PDF.</p>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            key="search_upload"
        )

        if uploaded and st.button("Load for Search"):
            try:
                st.session_state.pages = read_pdf(uploaded)
                st.session_state.pdf_name = uploaded.name
                st.success("PDF ready for searching!")
            except Exception as error:
                st.error(f"PDF error: {error}")

        if st.session_state.pages:
            query = st.text_input("Enter word or phrase")

            if st.button("Search"):
                if not query.strip():
                    st.warning("Please enter a word.")
                else:
                    found = False

                    for number, text in enumerate(
                        st.session_state.pages, start=1
                    ):
                        matches = list(
                            re.finditer(
                                re.escape(query),
                                text,
                                re.IGNORECASE
                            )
                        )

                        if matches:
                            found = True

                            with st.expander(
                                f"📄 Page {number} — "
                                f"{len(matches)} match(es)"
                            ):
                                for match in matches[:3]:
                                    start = max(0, match.start() - 50)
                                    end = min(
                                        len(text),
                                        match.end() + 80
                                    )

                                    st.write(
                                        "…",
                                        text[start:end].replace("\n", " "),
                                        "…"
                                    )

                    if not found:
                        st.warning("No matches found.")

    # =========================
    # PDF TO VOICE
    # =========================

    elif page == "🎙️ PDF to Voice":
        st.markdown("""
        <div class="hero">
            <h1>🎙️ PDF Voice Studio</h1>
            <p>Turn your PDF into audio.</p>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            key="voice_upload"
        )

        if uploaded and st.button("Extract PDF Text"):
            try:
                with st.spinner("Extracting text..."):
                    st.session_state.pages = read_pdf(uploaded)
                    st.session_state.pdf_name = uploaded.name
                    st.session_state.audio = None

                st.success("PDF text extracted!")

            except Exception as error:
                st.error(f"PDF error: {error}")

        pages = st.session_state.pages

        if pages:
            st.write(f"📄 File: {st.session_state.pdf_name}")

            mode = st.radio(
                "Conversion Mode",
                ["Complete PDF", "Selected Page", "Page Range"]
            )

            if mode == "Complete PDF":
                selected_text = "\n".join(pages)
                filename = "complete_pdf.mp3"

            elif mode == "Selected Page":
                number = st.selectbox(
                    "Choose page",
                    range(1, len(pages) + 1)
                )

                selected_text = pages[number - 1]
                filename = f"page_{number}.mp3"

            else:
                start, end = st.select_slider(
                    "Choose page range",
                    options=list(range(1, len(pages) + 1)),
                    value=(1, len(pages))
                )

                selected_text = "\n".join(pages[start - 1:end])
                filename = f"pages_{start}_{end}.mp3"

            languages = {
                "English": "en",
                "Tamil": "ta",
                "Hindi": "hi",
                "Telugu": "te",
                "Malayalam": "ml"
            }

            language_name = st.selectbox(
                "Voice Language",
                list(languages.keys())
            )

            st.caption(
                "Select the language matching the PDF text. "
                "This app does not translate the document."
            )

            st.text_area(
                "Text Preview",
                selected_text[:4000],
                height=150
            )

            if st.button(
                "✨ Generate Audio",
                use_container_width=True
            ):
                if not selected_text.strip():
                    st.warning("No readable text found.")
                elif len(selected_text) > 40000:
                    st.warning(
                        "Please select a smaller page range."
                    )
                else:
                    try:
                        with st.spinner("Creating your audio..."):
                            audio = create_audio(
                                selected_text,
                                languages[language_name]
                            )

                        st.session_state.audio = audio

                        st.session_state.history.insert(
                            0,
                            {
                                "file": st.session_state.pdf_name,
                                "date": datetime.now().strftime(
                                    "%d-%m-%Y %I:%M %p"
                                ),
                                "mode": mode,
                                "language": language_name
                            }
                        )

                        st.success("🎉 Audio is ready!")

                    except Exception as error:
                        st.error(
                            f"Audio generation failed: {error}"
                        )

            if st.session_state.audio:
                show_audio(
                    st.session_state.audio,
                    filename
                )

    # =========================
    # PDF SUMMARY
    # =========================

    elif page == "📝 PDF Summary":
        st.markdown("""
        <div class="hero">
            <h1>📝 PDF Summary</h1>
            <p>Get a simple summary from your document.</p>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            key="summary_upload"
        )

        if uploaded and st.button("Load for Summary"):
            try:
                st.session_state.pages = read_pdf(uploaded)
                st.session_state.pdf_name = uploaded.name
                st.session_state.summary = ""
                st.success("PDF loaded!")
            except Exception as error:
                st.error(f"PDF error: {error}")

        if st.session_state.pages:
            number = st.slider(
                "Summary sentence count",
                min_value=3,
                max_value=15,
                value=5
            )

            if st.button("Generate Summary"):
                text = "\n".join(st.session_state.pages)

                st.session_state.summary = create_summary(
                    text,
                    number
                )

            if st.session_state.summary:
                st.markdown(
                    '<div class="card"><h3>✨ Your Summary</h3></div>',
                    unsafe_allow_html=True
                )

                st.write(st.session_state.summary)

                st.download_button(
                    "📥 Download Summary",
                    data=st.session_state.summary,
                    file_name="pdf_summary.txt",
                    mime="text/plain"
                )

        st.caption(
            "This basic summary selects the first sentences. "
            "It is not an AI-generated summary."
        )

    # =========================
    # HISTORY
    # =========================

    elif page == "🕘 History":
        st.markdown("""
        <div class="hero">
            <h1>🕘 Conversion History</h1>
            <p>Review your recent audio conversions.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.history:
            for item in st.session_state.history:
                st.markdown(f"""
                <div class="card">
                    <h3>🎧 {html.escape(item['file'])}</h3>
                    <p>📅 {html.escape(item['date'])}</p>
                    <p>📄 {html.escape(item['mode'])}</p>
                    <p>🗣️ {html.escape(item['language'])}</p>
                </div>
                """, unsafe_allow_html=True)

            if st.button("Clear History"):
                st.session_state.history = []
                st.rerun()

        else:
            st.info("No conversions yet. Generate audio first.")


# =========================
# START APP
# =========================

if st.session_state.logged_in:
    dashboard()
else:
    login_page()
