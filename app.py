import streamlit as st
import re
import io
from pypdf import PdfReader
from gtts import gTTS

# ---------------- PAGE SETTINGS ----------------

st.set_page_config(
    page_title="Smart PDF to Voice",
    page_icon="📖",
    layout="wide"
)

st.title("📖 Smart PDF to Voice")
st.write("Upload your PDF and convert text into voice.")

# ---------------- LANGUAGES ----------------

LANGUAGES = {
    "English": "en",
    "Tamil": "ta",
    "Hindi": "hi",
    "Telugu": "te",
    "Malayalam": "ml"
}

# ---------------- PDF UPLOAD ----------------

uploaded_file = st.file_uploader(
    "📄 Upload your PDF",
    type=["pdf"]
)

if uploaded_file is None:
    st.info("Please upload a PDF file to continue.")
    st.stop()

# ---------------- EXTRACT PDF TEXT ----------------

try:
    reader = PdfReader(uploaded_file)

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

except Exception as error:
    st.error(f"Unable to read PDF: {error}")
    st.stop()

total_pages = len(pages)
full_text = "\n\n".join(pages)

if total_pages == 0:
    st.error("This PDF has no pages.")
    st.stop()

# ---------------- PDF INFORMATION ----------------

st.success("PDF uploaded successfully!")

col1, col2, col3 = st.columns(3)

col1.metric("Total Pages", total_pages)
col2.metric("Total Words", len(full_text.split()))
col3.metric("Total Characters", len(full_text))

if not full_text.strip():
    st.warning(
        "No readable text found. "
        "Scanned PDFs require OCR."
    )
    st.stop()

st.divider()

# ---------------- WORD SEARCH ----------------

st.header("🔍 Find a Word in PDF")

search_word = st.text_input(
    "Enter the word you want to find"
)

if st.button("Search Word"):

    if search_word.strip():

        results = []

        for page_number, page_text in enumerate(
            pages, start=1
        ):

            matches = list(
                re.finditer(
                    re.escape(search_word.strip()),
                    page_text,
                    re.IGNORECASE
                )
            )

            if matches:
                results.append({
                    "page": page_number,
                    "count": len(matches),
                    "text": page_text
                })

        st.session_state["search_results"] = results

    else:
        st.warning("Please enter a word.")

if "search_results" in st.session_state:

    results = st.session_state["search_results"]

    if results:

        st.success(
            f"Found the word on {len(results)} page(s)."
        )

        for result in results:

            page_no = result["page"]

            with st.expander(
                f"Page {page_no} — "
                f"{result['count']} occurrence(s)"
            ):

                st.write(result["text"][:2000])

                if st.button(
                    f"Select Page {page_no}",
                    key=f"select_{page_no}"
                ):
                    st.session_state["selected_page"] = page_no
                    st.rerun()

    else:
        st.warning("Word not found in this PDF.")

st.divider()

# ---------------- SELECT PAGE ----------------

st.header("📃 Read a Specific Page")

default_page = st.session_state.get(
    "selected_page", 1
)

page_number = st.number_input(
    "Choose page number",
    min_value=1,
    max_value=total_pages,
    value=min(max(int(default_page), 1), total_pages),
    step=1
)

page_number = int(page_number)

selected_text = pages[page_number - 1]

st.subheader(f"Page {page_number}")

st.text_area(
    "PDF Text",
    value=selected_text,
    height=250
)

st.download_button(
    "⬇️ Download Page Text",
    data=selected_text,
    file_name=f"page_{page_number}.txt",
    mime="text/plain"
)

st.divider()

# ---------------- TEXT TO VOICE ----------------

st.header("🔊 Convert PDF to Voice")

language = st.selectbox(
    "Choose Language",
    list(LANGUAGES.keys())
)

audio_option = st.radio(
    "Choose Audio",
    ["Selected Page", "Entire PDF"]
)

if audio_option == "Selected Page":
    text_to_convert = selected_text
    audio_filename = f"page_{page_number}.mp3"
else:
    text_to_convert = full_text
    audio_filename = "pdf_voice.mp3"

if st.button("🎧 Generate Voice"):

    if not text_to_convert.strip():

        st.error("No text available to convert.")

    else:

        try:

            audio_buffer = io.BytesIO()

            # Split long text into smaller chunks.
            chunks = [
                text_to_convert[i:i + 2500]
                for i in range(
                    0, len(text_to_convert), 2500
                )
            ]

            progress = st.progress(0)

            for index, chunk in enumerate(chunks):

                speech = gTTS(
                    text=chunk,
                    lang=LANGUAGES[language],
                    slow=False
                )

                speech.write_to_fp(audio_buffer)

                progress.progress(
                    (index + 1) / len(chunks)
                )

            st.session_state["audio_data"] = (
                audio_buffer.getvalue()
            )

            st.session_state["audio_filename"] = (
                audio_filename
            )

        except Exception as error:

            st.error(
                "Audio generation failed. "
                "Check your internet connection."
            )
            st.caption(str(error))

# ---------------- PLAY AUDIO ----------------

if st.session_state.get("audio_data"):

    st.success("Audio generated successfully!")

    st.audio(
        st.session_state["audio_data"],
        format="audio/mp3"
    )

    st.download_button(
        "⬇️ Download Audio",
        data=st.session_state["audio_data"],
        file_name=st.session_state["audio_filename"],
        mime="audio/mpeg"
    )

st.divider()

# ---------------- COMPLETE PDF TEXT ----------------

with st.expander("📚 View Complete PDF Text"):

    st.text_area(
        "Complete Text",
        value=full_text,
        height=300
    )

    st.download_button(
        "⬇️ Download Complete Text",
        data=full_text,
        file_name="complete_pdf_text.txt",
        mime="text/plain"
    )
