
import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
from gtts import gTTS
import io
import re
import hashlib
import base64

# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Smart PDF Voice Studio",
    page_icon="🎧",
    layout="wide"
)

LANGUAGES = {
    "English": "en",
    "Tamil": "ta",
    "Hindi": "hi",
    "Telugu": "te",
    "Malayalam": "ml"
}

# Demo accounts only
USERS = {
    "admin": hashlib.sha256(b"1234").hexdigest(),
    "student": hashlib.sha256(b"pdf123").hexdigest()
}

# ==================================================
# SESSION STATE
# ==================================================

defaults = {
    "logged_in": False,
    "username": "",
    "pages": [],
    "pdf_id": "",
    "selected_page": 1,
    "search_results": None,
    "search_word": "",
    "audio_data": None,
    "audio_name": "pdf_voice.mp3",
    "font_size": 17,
    "dark_mode": True
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==================================================
# DESIGN
# ==================================================

st.markdown("""
<style>
.block-container {
    max-width: 1250px;
    padding-top: 2rem;
}
.stButton > button {
    width: 100%;
    border-radius: 10px;
    min-height: 42px;
    font-weight: 600;
}
div[data-testid="stMetric"] {
    background: #17233f;
    padding: 16px;
    border-radius: 12px;
    border: 1px solid #334155;
}
.login-box {
    background: #17233f;
    padding: 25px;
    border-radius: 18px;
    border: 1px solid #334155;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# LOGIN PAGE
# ==================================================

def login_page():
    st.markdown(
        "<h1 style='text-align:center'>🎧 Smart PDF Voice Studio</h1>"
        "<p style='text-align:center'>"
        "Read PDFs and listen to them with ease</p>",
        unsafe_allow_html=True
    )

    left, center, right = st.columns([1, 1.2, 1])

    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.subheader("🔐 Login")
        st.write("Enter your account details.")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input(
                "Password",
                type="password"
            )

            submit = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if submit:
            username = username.strip()
            saved_password = USERS.get(username)
            entered_password = hashlib.sha256(
                password.encode()
            ).hexdigest()

            if saved_password and saved_password == entered_password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Incorrect username or password.")

        st.caption("Demo: admin / 1234")
        st.caption("Demo: student / pdf123")


# ==================================================
# PDF EXTRACTION
# ==================================================

def extract_pdf(file):
    reader = PdfReader(file)
    return [
        page.extract_text() or ""
        for page in reader.pages
    ]


# ==================================================
# WORD SEARCH
# ==================================================

def search_pdf(word, pages):
    results = []

    if not word.strip():
        return results

    pattern = re.compile(
        re.escape(word.strip()),
        re.IGNORECASE
    )

    for page_no, page_text in enumerate(pages, start=1):
        matches = list(pattern.finditer(page_text))

        if matches:
            snippets = []

            for match in matches[:5]:
                start = max(0, match.start() - 60)
                end = min(len(page_text), match.end() + 100)
                snippets.append(page_text[start:end])

            results.append({
                "page": page_no,
                "count": len(matches),
                "snippets": snippets
            })

    return results


# ==================================================
# TEXT TO SPEECH
# ==================================================

def convert_to_audio(text, language):
    if not text.strip():
        raise ValueError("No readable text available.")

    output = io.BytesIO()

    # Split long text into smaller parts.
    chunks = [
        text[i:i + 2500]
        for i in range(0, len(text), 2500)
    ]

    for chunk in chunks:
        speech = gTTS(
            text=chunk,
            lang=LANGUAGES[language],
            slow=False
        )
        speech.write_to_fp(output)

    output.seek(0)
    return output.getvalue()


# ==================================================
# AUDIO PLAYER WITH VOLUME AND SPEED
# ==================================================

def audio_player(audio_bytes):
    encoded = base64.b64encode(audio_bytes).decode("utf-8")

    html = f"""
    <div style="
        background:#17233f;
        padding:20px;
        border-radius:15px;
        color:white;
        font-family:Arial;
    ">
        <h3>🎧 Audio Player</h3>

        <audio id="audioPlayer" controls style="width:100%">
            <source
                src="data:audio/mp3;base64,{encoded}"
                type="audio/mpeg">
        </audio>

        <br><br>

        <label>🔊 Volume:
            <span id="volumeLabel">100%</span>
        </label>
        <input id="volume" type="range"
            min="0" max="100" value="100"
            style="width:100%">

        <br><br>

        <label>⏩ Playback Speed:
            <span id="speedLabel">1x</span>
        </label>
        <input id="speed" type="range"
            min="0.5" max="2" step="0.25" value="1"
            style="width:100%">

        <p style="color:#cbd5e1;font-size:13px">
            Adjust the controls while listening.
        </p>
    </div>

    <script>
        const player = document.getElementById("audioPlayer");
        const volume = document.getElementById("volume");
        const speed = document.getElementById("speed");

        volume.addEventListener("input", function() {{
            player.volume = Number(this.value) / 100;
            document.getElementById("volumeLabel").textContent =
                this.value + "%";
        }});

        speed.addEventListener("input", function() {{
            player.playbackRate = Number(this.value);
            document.getElementById("speedLabel").textContent =
                this.value + "x";
        }});
    </script>
    """

    components.html(html, height=310)


# ==================================================
# MAIN DASHBOARD
# ==================================================

def dashboard():
    with st.sidebar:
        st.title("🎧 PDF Studio")
        st.write("User:", st.session_state.username)
        st.divider()

        st.session_state.dark_mode = st.toggle(
            "Dark Mode",
            value=st.session_state.dark_mode
        )

        st.session_state.font_size = st.slider(
            "Reading Font Size",
            min_value=12,
            max_value=28,
            value=st.session_state.font_size
        )

        st.divider()

        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    if not st.session_state.dark_mode:
        st.markdown("""
        <style>
        .stApp {background:#f5f7fb;color:#172033;}
        h1,h2,h3,p,label {color:#172033;}
        div[data-testid="stMetric"] {background:white;}
        </style>
        """, unsafe_allow_html=True)

    st.title("📚 Smart PDF Voice Studio")
    st.write(
        "Upload, read, search, and listen to your PDF."
    )

    # ---------------- UPLOAD ----------------

    uploaded = st.file_uploader(
        "📄 Upload PDF",
        type=["pdf"]
    )

    if uploaded is None:
        st.info("Upload a PDF to start using the features.")

        c1, c2, c3 = st.columns(3)
        c1.subheader("🔍 Word Search")
        c2.subheader("📖 PDF Reader")
        c3.subheader("🎧 Voice Studio")

        c1.write("Find words and their page numbers.")
        c2.write("Read pages and download extracted text.")
        c3.write("Listen with adjustable speed and volume.")
        return

    current_id = f"{uploaded.name}_{uploaded.size}"

    if st.session_state.pdf_id != current_id:
        try:
            with st.spinner("Reading PDF..."):
                st.session_state.pages = extract_pdf(uploaded)
                st.session_state.pdf_id = current_id
                st.session_state.selected_page = 1
                st.session_state.search_results = None
                st.session_state.audio_data = None
        except Exception as error:
            st.error(f"PDF error: {error}")
            return

    pages = st.session_state.pages

    if not pages:
        st.error("No pages found.")
        return

    full_text = "\n\n".join(pages)
    total_pages = len(pages)

    if not full_text.strip():
        st.warning(
            "No selectable text found. Scanned PDFs require OCR."
        )
        return

    # ---------------- OVERVIEW ----------------

    st.success(f"Loaded: {uploaded.name}")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("📄 Pages", total_pages)
    col2.metric("📝 Words", len(full_text.split()))
    col3.metric("🔤 Characters", len(full_text))
    col4.metric(
        "⏱️ Reading Time",
        f"{max(1, len(full_text.split()) // 200)} min"
    )

    st.progress(
        min(st.session_state.selected_page / total_pages, 1.0),
        text="Reading progress"
    )

    st.divider()

    reader_tab, search_tab, voice_tab, tools_tab = st.tabs([
        "📖 PDF Reader",
        "🔍 Word Search",
        "🎧 Voice Studio",
        "🛠️ Text Tools"
    ])

    # ---------------- READER TAB ----------------

    with reader_tab:
        st.subheader("📖 Read PDF Page")

        page_no = st.number_input(
            "Select page",
            min_value=1,
            max_value=total_pages,
            value=min(
                max(1, int(st.session_state.selected_page)),
                total_pages
            ),
            step=1
        )

        page_no = int(page_no)
        st.session_state.selected_page = page_no
        page_text = pages[page_no - 1]

        st.markdown(
            f"**Page {page_no} of {total_pages}**"
        )

        st.text_area(
            "Page Text",
            value=page_text,
            height=300,
            key=f"reader_page_{page_no}"
        )

        st.download_button(
            "⬇️ Download This Page",
            data=page_text,
            file_name=f"page_{page_no}.txt",
            mime="text/plain"
        )

        st.caption(
            f"Words on this page: {len(page_text.split())}"
        )

        if st.button("📖 Add Page to Reading History"):
            history = st.session_state.get("reading_history", [])
            if page_no not in history:
                history.append(page_no)
            st.session_state.reading_history = history
            st.success("Page added to reading history.")

        history = st.session_state.get("reading_history", [])
        if history:
            st.write(
                "Reading history: " +
                ", ".join(str(n) for n in history)
            )

    # ---------------- SEARCH TAB ----------------

    with search_tab:
        st.subheader("🔍 Search Word in PDF")

        word = st.text_input(
            "Enter a word or phrase",
            key="search_input"
        )

        if st.button("Search PDF", key="search_button"):
            if word.strip():
                st.session_state.search_results = search_pdf(
                    word, pages
                )
                st.session_state.search_word = word.strip()
            else:
                st.warning("Enter a word to search.")

        results = st.session_state.search_results

        if results is not None:
            if results:
                total_matches = sum(
                    item["count"] for item in results
                )

                st.success(
                    f"'{st.session_state.search_word}' found on "
                    f"{len(results)} page(s), "
                    f"{total_matches} time(s)."
                )

                for result in results:
                    with st.expander(
                        f"Page {result['page']} — "
                        f"{result['count']} occurrence(s)"
                    ):
                        for snippet in result["snippets"]:
                            st.write(f"...{snippet}...")

                        if st.button(
                            f"Open Page {result['page']}",
                            key=f"open_page_{result['page']}"
                        ):
                            st.session_state.selected_page = result["page"]
                            st.rerun()
            else:
                st.warning("Word not found.")

    # ---------------- VOICE TAB ----------------

    with voice_tab:
        st.subheader("🎧 Voice Studio")

        language = st.selectbox(
            "Choose voice language",
            list(LANGUAGES.keys()),
            key="voice_language"
        )

        choice = st.radio(
            "What should be converted?",
            ["Selected Page", "Entire PDF"],
            horizontal=True
        )

        if choice == "Selected Page":
            text_to_speak = pages[
                st.session_state.selected_page - 1
            ]
            audio_filename = (
                f"page_{st.session_state.selected_page}.mp3"
            )
        else:
            text_to_speak = full_text
            audio_filename = "complete_pdf_voice.mp3"

        st.caption(
            "Audio generation needs an internet connection."
        )

        if st.button("🎙️ Generate Voice", key="generate_voice"):
            if not text_to_speak.strip():
                st.error("No readable text on this selection.")
            else:
                try:
                    with st.spinner("Generating audio..."):
                        audio_data = convert_to_audio(
                            text_to_speak,
                            language
                        )

                    st.session_state.audio_data = audio_data
                    st.session_state.audio_name = audio_filename
                    st.success("Audio generated successfully!")

                except Exception as error:
                    st.error(
                        "Could not generate audio. Check your internet "
                        "connection and selected language."
                    )
                    st.caption(str(error))

        if st.session_state.audio_data:
            st.subheader("🔊 Listen and Adjust")

            audio_player(st.session_state.audio_data)

            st.download_button(
                "⬇️ Download MP3",
                data=st.session_state.audio_data,
                file_name=st.session_state.audio_name,
                mime="audio/mpeg",
                key="download_mp3"
            )

    # ---------------- TEXT TOOLS TAB ----------------

    with tools_tab:
        st.subheader("🛠️ Text Tools")

        st.metric(
            "Total Sentences",
            len(re.findall(r"[.!?]+", full_text))
        )

        st.metric(
            "Average Words per Page",
            round(len(full_text.split()) / total_pages, 1)
        )

        st.download_button(
            "⬇️ Download Complete PDF Text",
            data=full_text,
            file_name="complete_pdf_text.txt",
            mime="text/plain"
        )

        st.subheader("📋 Copy / View Complete Text")
        st.text_area(
            "Complete PDF text",
            value=full_text,
            height=300,
            key="all_pdf_text"
        )

        st.subheader("📝 Text Preview")
        st.write(
            full_text[:1500] +
            ("..." if len(full_text) > 1500 else "")
        )

    st.divider()
    st.caption(
        "Smart PDF Voice Studio | PDF reading and text-to-speech app"
    )


# ==================================================
# APPLICATION ENTRY POINT
# ==================================================

if st.session_state.logged_in:
    dashboard()
else:
    login_page()
