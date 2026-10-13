import streamlit as st
from pypdf import PdfReader
from gtts import gTTS
from io import BytesIO
import re

st.set_page_config(
    page_title="VocaPDF - PDF to Voice",
    page_icon="📄",
    layout="wide"
)

# -------------------- DESIGN --------------------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #eef2ff, #f5f3ff);
}
.main-title {
    text-align: center;
    color: #3730a3;
    font-size: 38px;
    font-weight: bold;
}
.sub-title {
    text-align: center;
    color: #475569;
    font-size: 17px;
}
div.stButton > button {
    background-color: #4f46e5;
    color: white;
    border-radius: 8px;
    border: none;
    padding: 10px 20px;
    font-weight: bold;
}
div.stButton > button:hover {
    background-color: #3730a3;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# -------------------- SESSION STATE --------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "audio_data" not in st.session_state:
    st.session_state.audio_data = None

if "history" not in st.session_state:
    st.session_state.history = []

# -------------------- LOGIN PAGE --------------------

if not st.session_state.logged_in:
    st.markdown(
        '<div class="main-title">VocaPDF</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-title">PDF Reading and Voice Converter</div>',
        unsafe_allow_html=True
    )

    st.write("")
    st.write("")

    _, login_col, _ = st.columns([1, 1.2, 1])

    with login_col:
        st.subheader("Login")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            if username == "student" and password == "pdf123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Incorrect username or password.")

        st.caption("Demo username: student")
        st.caption("Demo password: pdf123")

    st.stop()

# -------------------- SIDEBAR --------------------

st.sidebar.title("VocaPDF Menu")

page = st.sidebar.radio(
    "Select a page",
    [
        "Dashboard",
        "PDF to Voice",
        "PDF Reader",
        "Text Search",
        "History"
    ]
)

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.pdf_text = ""
    st.session_state.audio_data = None
    st.rerun()

# -------------------- DASHBOARD --------------------

if page == "Dashboard":
    st.markdown(
        '<div class="main-title">VocaPDF Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sub-title">Read your PDF and listen to it as audio.</div>',
        unsafe_allow_html=True
    )

    st.write("")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("PDF Loaded", "Yes" if st.session_state.pdf_text else "No")

    with col2:
        st.metric(
            "Words Extracted",
            len(st.session_state.pdf_text.split())
        )

    with col3:
        st.metric("Audio Created", "Yes" if st.session_state.audio_data else "No")

    st.info("Open PDF to Voice from the menu to upload a PDF and generate audio.")

# -------------------- PDF TO VOICE --------------------

elif page == "PDF to Voice":
    st.title("PDF to Voice Converter")
    st.write("Upload a PDF, extract its text, and generate an audio file.")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"]
    )

    if uploaded_file is not None:
        if st.button("Extract PDF Text"):
            try:
                reader = PdfReader(uploaded_file)

                extracted_text = []

                for page_number, pdf_page in enumerate(reader.pages):
                    page_text = pdf_page.extract_text() or ""
                    if page_text.strip():
                        extracted_text.append(page_text)

                full_text = "\n".join(extracted_text).strip()

                if full_text:
                    st.session_state.pdf_text = full_text
                    st.session_state.audio_data = None
                    st.success("PDF text extracted successfully.")
                else:
                    st.error(
                        "No readable text found. This PDF may contain scanned images."
                    )

            except Exception as error:
                st.error("Could not read this PDF.")
                st.code(str(error))

    if st.session_state.pdf_text:
        st.subheader("Extracted Text")

        st.text_area(
            "PDF content",
            value=st.session_state.pdf_text,
            height=220
        )

        col1, col2 = st.columns(2)

        with col1:
            language = st.selectbox(
                "Choose voice language",
                options=[
                    "English",
                    "Tamil",
                    "Hindi",
                    "Telugu",
                    "Malayalam"
                ]
            )

        with col2:
            speech_speed = st.selectbox(
                "Voice speed",
                options=["Normal", "Slow"]
            )

        language_codes = {
            "English": "en",
            "Tamil": "ta",
            "Hindi": "hi",
            "Telugu": "te",
            "Malayalam": "ml"
        }

        if st.button("Generate Audio", use_container_width=True):
            text_to_speak = re.sub(
                r"\s+",
                " ",
                st.session_state.pdf_text
            ).strip()

            if not text_to_speak:
                st.error("No text is available to convert.")
            else:
                try:
                    with st.spinner("Generating audio. Please wait..."):
                        audio_buffer = BytesIO()

                        speech = gTTS(
                            text=text_to_speak,
                            lang=language_codes[language],
                            slow=(speech_speed == "Slow")
                        )

                        speech.write_to_fp(audio_buffer)
                        audio_buffer.seek(0)

                        st.session_state.audio_data = audio_buffer.getvalue()

                    st.session_state.history.append({
                        "language": language,
                        "words": len(text_to_speak.split())
                    })

                    st.success("Audio generated successfully.")

                except Exception as error:
                    st.session_state.audio_data = None
                    st.error(
                        "Audio generation failed. Check your internet connection "
                        "and try again."
                    )
                    st.code(str(error))

    if st.session_state.audio_data:
        st.subheader("Generated Audio")

        st.audio(
            st.session_state.audio_data,
            format="audio/mp3"
        )

        st.download_button(
            label="Download MP3 Audio",
            data=st.session_state.audio_data,
            file_name="pdf_voice.mp3",
            mime="audio/mpeg",
            use_container_width=True
        )

# -------------------- PDF READER --------------------

elif page == "PDF Reader":
    st.title("PDF Reader")

    if st.session_state.pdf_text:
        st.text_area(
            "Read extracted PDF text",
            value=st.session_state.pdf_text,
            height=400
        )
    else:
        st.info("Go to PDF to Voice and extract text from a PDF first.")

# -------------------- TEXT SEARCH --------------------

elif page == "Text Search":
    st.title("Search in PDF")

    search_word = st.text_input("Enter a word or phrase to search")

    if search_word:
        if st.session_state.pdf_text:
            matches = [
                line for line in st.session_state.pdf_text.splitlines()
                if search_word.lower() in line.lower()
            ]

            if matches:
                st.success(f"Found {len(matches)} matching lines.")
                for match in matches:
                    st.write(match)
            else:
                st.warning("No matching text found.")
        else:
            st.info("Extract PDF text first from the PDF to Voice page.")

# -------------------- HISTORY --------------------

elif page == "History":
    st.title("Conversion History")

    if st.session_state.history:
        for number, item in enumerate(
            reversed(st.session_state.history),
            start=1
        ):
            st.write(
                f"{number}. Language: {item['language']} | "
                f"Words: {item['words']}"
            )
    else:
        st.info("No conversions in this session yet.")

# -------------------- FOOTER --------------------

st.sidebar.markdown("---")
st.sidebar.caption("VocaPDF | PDF Reading and Voice Converter")


                
