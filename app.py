import base64
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from pypdf import PdfReader

MAX_PAGES = 30
CHUNK_CHARS = 3000

st.set_page_config(page_title="Smart PDF App", page_icon="📄")
st.title("📄 Smart PDF App")
st.write("Upload a PDF file and listen to it as voice.")


def split_chunks(text, size=CHUNK_CHARS):
    chunks, cur = [], ""
    for line in text.split("\n"):
        while len(line) > size:
            if cur.strip():
                chunks.append(cur)
                cur = ""
            chunks.append(line[:size])
            line = line[size:]
        if len(cur) + len(line) + 1 > size:
            chunks.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur)
    return [c for c in chunks if c.strip()]


def make_audio(chunk):
    buf = BytesIO()
    gTTS(text=chunk, lang="en", tld="co.in").write_to_fp(buf)
    audio = buf.getvalue()
    try:  # louder voice
        from pydub import AudioSegment
        seg = AudioSegment.from_file(BytesIO(audio), format="mp3") + 8
        out = BytesIO()
        seg.export(out, format="mp3")
        audio = out.getvalue()
    except Exception:
        pass
    return base64.b64encode(audio).decode()


@st.cache_data(show_spinner=False)
def convert(text):
    chunks = split_chunks(text)
    with ThreadPoolExecutor(max_workers=4) as ex:
        return list(ex.map(make_audio, chunks))


pdf = st.file_uploader("📄 Upload your PDF", type=["pdf"])

if pdf:
    st.success("✅ PDF uploaded successfully!")
    reader = PdfReader(pdf)
    total = len(reader.pages)
    st.info(f"Total pages: {total}")

    c1, c2 = st.columns(2)
    start = c1.number_input("From page", 1, total, 1)
    end = c2.number_input("To page", 1, total, min(total, 5))

    if end < start:
        st.error("'To page' should be 'From page'-ku mela irukanum.")
        st.stop()
    if end - start + 1 > MAX_PAGES:
        st.warning(f"Oru thadavai max {MAX_PAGES} pages mattum.")
        st.stop()

    text = "\n".join(
        (reader.pages[i].extract_text() or "") for i in range(start - 1, end)
    ).strip()

    if not text:
        st.error("No text found in this PDF (maybe scanned images).")
        st.stop()

    st.subheader("📖 Extracted Text")
    st.text_area("PDF Text", text, height=250)

    with st.spinner("Converting to voice..."):
        parts = convert(text)
    st.success("🎉 PDF converted to voice successfully!")

    parts_js = "[" + ",".join(f'"{p}"' for p in parts) + "]"
    components.html(
        f"""
        <button onclick="playBtn()" style="padding:10px 18px;font-size:16px;margin-right:8px;">▶️ Play Voice</button>
        <button onclick="stopBtn()" style="padding:10px 18px;font-size:16px;">⏹️ Stop</button>
        <script>
          var parts = {parts_js};
          var i = 0, started = false;
          var a = new Audio();
          a.volume = 1.0;
          function playPart() {{ a.src = "data:audio/mp3;base64," + parts[i]; a.play(); }}
          a.onended = function() {{ i++; if (i < parts.length) playPart(); else {{ i = 0; started = false; }} }};
          function playBtn() {{ if (!started) {{ started = true; playPart(); }} else {{ a.play(); }} }}
          function stopBtn() {{ a.pause(); i = 0; started = false; }}
        </script>
        """,
        height=80,
    )
