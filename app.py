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
    try:  # bold + loud voice (needs ffmpeg)
        from pydub import AudioSegment
        from pydub.effects import compress_dynamic_range, normalize

        seg = AudioSegment.from_file(BytesIO(audio), format="mp3")
        seg = compress_dynamic_range(seg, threshold=-25.0, ratio=4.0)
        seg = normalize(seg, headroom=0.1)
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
        <style>
          .b {{ padding:10px 14px; font-size:16px; margin:4px 4px 4px 0; }}
          .row {{ margin-top:8px; font-size:15px; }}
          select {{ font-size:15px; padding:6px; margin-right:12px; }}
        </style>
        <div>
          <button class="b" onclick="skip(-10)">⏪ 10s</button>
          <button class="b" onclick="playBtn()">▶️ Play Voice</button>
          <button class="b" onclick="pauseBtn()">⏸️ Pause</button>
          <button class="b" onclick="skip(10)">10s ⏩</button>
          <button class="b" onclick="stopBtn()">⏹️ Stop</button>
        </div>
        <div class="row">
          Speed:
          <select id="speed" onchange="setSpeed()">
            <option value="0.75">0.75x</option>
            <option value="1">1x</option>
            <option value="1.25" selected>1.25x</option>
            <option value="1.5">1.5x</option>
            <option value="2">2x</option>
          </select>
          Voice boost:
          <select id="boost" onchange="setBoost()">
            <option value="1">1x</option>
            <option value="1.5" selected>1.5x</option>
            <option value="2">2x</option>
            <option value="3">3x</option>
          </select>
        </div>
        <script>
          var parts = {parts_js};
          var i = 0, started = false;
          var a = new Audio();
          a.volume = 1.0;
          var ctx = null, gainNode = null;

          function setupAudio() {{
            if (ctx) return;
            try {{
              var AC = window.AudioContext || window.webkitAudioContext;
              ctx = new AC();
              var src = ctx.createMediaElementSource(a);
              gainNode = ctx.createGain();
              src.connect(gainNode);
              gainNode.connect(ctx.destination);
              setBoost();
            }} catch (e) {{ ctx = null; }}
          }}
          function setSpeed() {{
            var s = parseFloat(document.getElementById("speed").value);
            a.defaultPlaybackRate = s;
            a.playbackRate = s;
          }}
          function setBoost() {{
            if (gainNode) gainNode.gain.value = parseFloat(document.getElementById("boost").value);
          }}

          function playPart(idx, offset, fromEnd) {{
            i = idx;
            a.onloadedmetadata = function() {{
              var d = isFinite(a.duration) ? a.duration : 0;
              a.currentTime = fromEnd ? Math.max(0, d - offset) : offset;
              setSpeed();
              a.play();
            }};
            a.src = "data:audio/mp3;base64," + parts[i];
          }}

          a.onended = function() {{
            if (i < parts.length - 1) {{ playPart(i + 1, 0, false); }}
            else {{ i = 0; started = false; }}
          }};

          function playBtn() {{
            setupAudio();
            if (ctx && ctx.state === "suspended") ctx.resume();
            if (!started) {{ started = true; playPart(0, 0, false); }}
            else {{ a.play(); }}
          }}
          function pauseBtn() {{ a.pause(); }}
          function stopBtn() {{ a.pause(); i = 0; started = false; }}

          function skip(sec) {{
            if (!started) return;
            var t = a.currentTime + sec;
            if (sec > 0) {{
              if (t < a.duration) {{ a.currentTime = t; }}
              else if (i < parts.length - 1) {{ playPart(i + 1, t - a.duration, false); }}
              else {{ stopBtn(); }}
            }} else {{
              if (t >= 0) {{ a.currentTime = t; }}
              else if (i > 0) {{ playPart(i - 1, -t, true); }}
              else {{ a.currentTime = 0; }}
            }}
          }}
        </script>
        """,
        height=170,
    )
