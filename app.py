import streamlit as st
from pypdf import PdfReader
from gtts import gTTS
from io import BytesIO

st.set_page_config(
    page_title="PDF to Voice Converter",
    page_icon="📄"
)

st.title("📄 PDF to Voice Converter")
st.write("Upload a PDF and convert its text into voice.")

pdf_file = st.file_uploader(
    "Upload your PDF",
    type=["pdf"]
)

if pdf_file:

    st.success("✅ PDF uploaded successfully!")

    reader = PdfReader(pdf_file)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    if text.strip():

        st.subheader("📖 PDF Text")

        st.text_area(
            "Extracted Text",
            text,
            height=250
        )

        if st.button("🔊 Convert PDF to Voice"):

            with st.spinner("Converting PDF to voice..."):

                audio = BytesIO()

                tts = gTTS(
                    text=text,
                    lang="en"
                )

                tts.write_to_fp(audio)

                audio.seek(0)

            st.success("🎉 PDF converted to voice!")

            st.audio(
                audio,
                format="audio/mp3"
            )

            st.download_button(
                label="⬇️ Download Voice",
                data=audio,
                file_name="pdf_voice.mp3",
                mime="audio/mp3"
            )

    else:

        st.error(
            "❌ No text found in this PDF. "
            "Scanned/image-only PDFs may not work."
        )
