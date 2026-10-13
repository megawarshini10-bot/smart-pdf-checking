import streamlit as st
from pypdf import PdfReader
from gtts import gTTS
from io import BytesIO
from datetime import datetime
import re

st.set_page_config(
    page_title="VocaPDF",
    page_icon="V",
    layout="wide"
)

# ---------------- SESSION STATE ----------------

defaults = {
    "logged_in": False,
    "pdf_text": "",
    "pdf_name": "",
    "page_texts": [],
    "audio_data": None,
    "history": [],
    "search_results": []
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------- CUSTOM DESIGN ----------------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f5f3ff, #eff6ff);
}

.main-title {
    font-size: 42px;
    font-weight: 800;
    color: #4f46e5;
}

.subtitle {
    font-size: 17px;
    color: #64748b;
}

div.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    min-height: 42px;
}

section[data-testid="stSidebar"] {
    background-color: #eef2ff;
}
</style>
""", unsafe_allow_html=True)


# ---------------- LOGIN PAGE ----------------

if not st.session_state.logged_in:

    st.markdown(
        "<h1 style='text-align:center;color:#4f46e5;'>VocaPDF</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:center;'>Your Personal PDF Reading Assistant</p>",
        unsafe_allow_html=True
    )

    st.write("")

    left, center, right = st.columns([1, 1.2, 1])

    with center:

        st.subheader("Login to Continue")

        with st.form("login_form"):

            username = st.text_input("Username")

            password = st.text_input(
                "Password",
                type="password"
            )

            login_button = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if login_button:

            if username == "student" and password == "pdf123":

                st.session_state.logged_in = True

                st.rerun()

            else:

                st.error("Incorrect username or password.")

        st.info(
            "Demo Login\n\n"
            "Username: student\n\n"
            "Password: pdf123"
        )

    st.stop()


# ---------------- DASHBOARD HEADER ----------------

st.markdown(
    "<div class='main-title'>VocaPDF</div>",
    unsafe_allow_html=True
)

st.markdown(
    "<div class='subtitle'>"
    "Read your PDF and listen to its content."
    "</div>",
    unsafe_allow_html=True
)

st.divider()


# ---------------- SIDEBAR ----------------

with st.sidebar:

    st.title("VocaPDF")

    st.write("Welcome, Student!")

    menu = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Load PDF",
            "PDF Reader",
            "Text Search",
            "Generate Audio",
            "History"
        ]
    )

    st.divider()

    if st.button("Logout", use_container_width=True):

        st.session_state.logged_in = False

        st.rerun()


# ---------------- DASHBOARD ----------------

if menu == "Dashboard":

    st.subheader("Welcome to VocaPDF")

    st.write(
        "Convert PDF text into audio and listen using "
        "your browser's audio player."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "PDF Loaded",
            "Yes" if st.session_state.pdf_text else "No"
        )

    with c2:
        st.metric(
            "Pages",
            len(st.session_state.page_texts)
        )

    with c3:
        st.metric(
            "Audio Ready",
            "Yes" if st.session_state.audio_data else "No"
        )

    st.divider()

    st.subheader("How to Use")

    st.write("1. Open Load PDF.")

    st.write("2. Upload your PDF file.")

    st.write("3. Click Load PDF.")

    st.write("4. Open Generate Audio.")

    st.write("5. Select pages and voice language.")

    st.write("6. Click Generate Audio and play the result.")


# ---------------- LOAD PDF ----------------

elif menu == "Load PDF":

    st.subheader("Load Your PDF")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        key="pdf_upload"
    )

    if uploaded_file is not None:

        st.write("Selected file:", uploaded_file.name)

        if st.button(
            "Load PDF",
            type="primary",
            use_container_width=True
        ):

            try:

                with st.spinner("Reading PDF..."):

                    uploaded_file.seek(0)

                    reader = PdfReader(uploaded_file)

                    if reader.is_encrypted:

                        st.error(
                            "This PDF is password protected. "
                            "Please upload an unlocked PDF."
                        )

                    else:

                        page_texts = []

                        for page in reader.pages:

                            text = page.extract_text() or ""

                            page_texts.append(text)

                        full_text = "\n\n".join(page_texts).strip()

                        if not full_text:

                            st.error(
                                "No readable text found. "
                                "This may be a scanned PDF."
                            )

                        else:

                            st.session_state.pdf_name = (
                                uploaded_file.name
                            )

                            st.session_state.page_texts = page_texts

                            st.session_state.pdf_text = full_text

                            st.session_state.audio_data = None

                            st.session_state.history.append({
                                "file": uploaded_file.name,
                                "time": datetime.now().strftime(
                                    "%d-%m-%Y %I:%M %p"
                                )
                            })

                            st.success("PDF loaded successfully!")

                            st.write(
                                "Total pages:",
                                len(page_texts)
                            )

                            st.write(
                                "Extracted characters:",
                                len(full_text)
                            )

                            st.info(
                                "Your PDF is ready. "
                                "Open PDF Reader or Generate Audio."
                            )

            except Exception as e:

                st.error(
                    "Unable to read this PDF. "
                    "Please try another PDF file."
                )

                st.caption(str(e))

    if st.session_state.pdf_text:

        st.success(
            "Current PDF: " + st.session_state.pdf_name
        )


# ---------------- PDF READER ----------------

elif menu == "PDF Reader":

    st.subheader("PDF Reader")

    if not st.session_state.pdf_text:

        st.warning("Please load a PDF first.")

    else:

        st.write(
            "File:",
            st.session_state.pdf_name
        )

        st.write(
            "Total pages:",
            len(st.session_state.page_texts)
        )

        page_number = st.number_input(
            "Select page number",
            min_value=1,
            max_value=len(st.session_state.page_texts),
            value=1,
            step=1
        )

        page_content = st.session_state.page_texts[
            int(page_number) - 1
        ]

        st.text_area(
            "PDF Page Content",
            value=page_content,
            height=350
        )

        if not page_content.strip():

            st.warning(
                "No readable text found on this page."
            )


# ---------------- TEXT SEARCH ----------------

elif menu == "Text Search":

    st.subheader("Search Inside PDF")

    if not st.session_state.pdf_text:

        st.warning("Please load a PDF first.")

    else:

        query = st.text_input(
            "Enter a word or phrase"
        )

        if st.button("Search", type="primary"):

            if query.strip():

                results = []

                for i, text in enumerate(
                    st.session_state.page_texts
                ):

                    if query.lower() in text.lower():

                        results.append({
                            "page": i + 1,
                            "text": text
                        })

                st.session_state.search_results = results

                if results:

                    st.success(
                        f"Found results on {len(results)} page(s)."
                    )

                    for result in results:

                        with st.expander(
                            f"Page {result['page']}"
                        ):

                            st.write(result["text"])

                else:

                    st.warning("No matching text found.")


# ---------------- GENERATE AUDIO ----------------

elif menu == "Generate Audio":

    st.subheader("PDF to Audio Converter")

    if not st.session_state.pdf_text:

        st.warning(
            "Please open Load PDF and load a PDF first."
        )

    else:

        st.write(
            "Current PDF:",
            st.session_state.pdf_name
        )

        total_pages = len(st.session_state.page_texts)

        page_mode = st.radio(
            "Choose pages",
            [
                "Entire PDF",
                "Selected Page",
                "Page Range"
            ]
        )

        selected_text = ""

        if page_mode == "Entire PDF":

            selected_text = st.session_state.pdf_text

        elif page_mode == "Selected Page":

            selected_page = st.number_input(
                "Page number",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1,
                key="audio_page"
            )

            selected_text = st.session_state.page_texts[
                int(selected_page) - 1
            ]

        else:

            col1, col2 = st.columns(2)

            with col1:

                start_page = st.number_input(
                    "Start page",
                    min_value=1,
                    max_value=total_pages,
                    value=1,
                    step=1
                )

            with col2:

                end_page = st.number_input(
                    "End page",
                    min_value=1,
                    max_value=total_pages,
                    value=total_pages,
                    step=1
                )

            if start_page <= end_page:

                selected_text = "\n\n".join(
                    st.session_state.page_texts[
                        int(start_page) - 1:int(end_page)
                    ]
                )

            else:

                st.error(
                    "End page must be greater than "
                    "or equal to start page."
                )

        language_names = {
            "English": "en",
            "Tamil": "ta",
            "Hindi": "hi",
            "Telugu": "te",
            "Malayalam": "ml"
        }

        language = st.selectbox(
            "Voice Language",
            list(language_names.keys())
        )

        st.caption(
            "The selected language controls the text-to-speech "
            "voice. It does not translate the PDF."
        )

        if selected_text.strip():

            st.write(
                "Characters to convert:",
                len(selected_text)
            )

            if st.button(
                "Generate Audio",
                type="primary",
                use_container_width=True
            ):

                try:

                    text_to_read = selected_text.strip()

                    # Split long text into smaller pieces.
                    chunks = []

                    while text_to_read:

                        if len(text_to_read) <= 2500:

                            chunks.append(text_to_read)

                            break

                        split_position = text_to_read.rfind(
                            " ",
                            0,
                            2500
                        )

                        if split_position < 500:

                            split_position = 2500

                        chunks.append(
                            text_to_read[:split_position]
                        )

                        text_to_read = text_to_read[
                            split_position:
                        ].strip()

                    audio_buffer = BytesIO()

                    progress = st.progress(0)

                    status = st.empty()

                    for index, chunk in enumerate(chunks):

                        status.write(
                            f"Generating audio: "
                            f"{index + 1} of {len(chunks)}"
                        )

                        speech = gTTS(
                            text=chunk,
                            lang=language_names[language],
                            slow=False
                        )

                        part = BytesIO()

                        speech.write_to_fp(part)

                        audio_buffer.write(part.getvalue())

                        progress.progress(
                            (index + 1) / len(chunks)
                        )

                    audio_data = audio_buffer.getvalue()

                    if not audio_data:

                        raise ValueError(
                            "Audio generation returned empty data."
                        )

                    st.session_state.audio_data = audio_data

                    status.success(
                        "Audio generated successfully!"
                    )

                except Exception as e:

                    st.session_state.audio_data = None

                    st.error(
                        "Audio generation failed. "
                        "Check your internet connection and try again."
                    )

                    st.caption(str(e))

        else:

            st.warning(
                "No text is available in the selected pages."
            )

        # Display audio player outside the Generate button.
        if st.session_state.audio_data:

            st.divider()

            st.subheader("Your Audio")

            st.audio(
                st.session_state.audio_data,
                format="audio/mp3"
            )

            st.download_button(
                label="Download Audio",
                data=st.session_state.audio_data,
                file_name="vocapdf_audio.mp3",
                mime="audio/mpeg",
                use_container_width=True
            )

            st.info(
                "Use the audio player's volume control to "
                "increase or decrease the sound."
            )


# ---------------- HISTORY ----------------

elif menu == "History":

    st.subheader("PDF Reading History")

    if st.session_state.history:

        for item in reversed(st.session_state.history):

            st.write("PDF:", item["file"])

            st.caption("Loaded at: " + item["time"])

            st.divider()

    else:

        st.info("No PDF history available yet.")
