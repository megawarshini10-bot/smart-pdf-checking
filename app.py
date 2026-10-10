import base64
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from pypdf import PdfReader

MAX_PAGES = 30
CHUNK_CHARS = 3000

st.set_page_config(page_title="Smart PDF App", page_icon="🎧", layout="centered")

# ---------- Styling ----------
st.markdown(
    """
    <style>
      .hero {
        background: linear-gradient(135deg, #7C3AED 0%, #DB2777 100%);
        padding: 28px 22px; border-radius: 18px; color: white;
        text-align: center; margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(124,58,237,0.25);
      }
      .hero h1 { margin: 0; font-size: 2rem; color: white; }
      .hero p { margin: 6px 0 0; font-size: 1rem; opacity: 0.95; }
      .steps { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 18px; }
      .step {
        flex: 1; min-width: 140px; background: #F5F3FF; border-left: 5px solid #7C3AED;
        padding: 12px 14px; border-radius: 12px; font-size: 0.95rem; color: #1F2937;
      }
      .step b { color: #7C3AED; }
      .step.s2 { border-color: #DB2777; background: #FDF2F8; } .step.s2 b { color: #DB2777; }
      .step.s3 { border-color: #059669; background: #ECFDF5; } .step.s3 b { color: #059669; }
      .stat {
        border-radius: 14px; padding: 14px; text-align: center; color: white;
        font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.12);
      }
      .stat .n { font-size: 1.7rem; display: block; }
      .stat .l { font-size: 0.85rem; opacity: 0.95; }
      .st1 { background: linear-gradient(135deg,#6366F1,#8B5CF6); }
      .st2 { background: linear-gradient(135deg,#EC4899,#F43F5E); }
      .st3 { background: linear-gradient(135deg,#10B981,#059669); }
      .footer { text-align: center; color: #6B7280; font-size: 0.85rem; margin-top: 30px; }
    </style>
    <div class="hero">
      <h1>🎧 Smart PDF App</h1>
      <p>Upload a PDF and listen to it as clear, bold voice.</p>
    </div>
    <div class="steps">
      <div class="step"><b>Step 1</b><br>📄 Upload your PDF</div>
      <div class="step s2"><b>Step 2</b><br>📑 Select pages</div>
      <div class="step s3"><b>Step 3</b><br>🔊 Press Play and listen</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- Logic ----------
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


PLAYER_HTML = """
<style>
  * { box-sizing: border-box; font-family: sans-serif; }
  .card { background: linear-gradient(135deg,#1E1B4B,#4C1D95); border-radius: 18px;
          padding: 18px; color: white; box-shadow: 0 8px 22px rgba(0,0,0,0.25); }
  .title { font-size: 1.05rem; font-weight: 700; margin-bottom: 10px; }
  .bar { height: 8px; background: rgba(255,255,255,0.25); border-radius: 8px; overflow: hidden; }
  #fill { height: 100%; width: 0%; background: linear-gradient(90deg,#34D399,#FBBF24,#F472B6); }
  #info { font-size: 0.85rem; margin: 8px 0 12px; opacity: 0.9; }
  .row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  button { border: none; color: white; font-size: 15px; font-weight: 600; padding: 11px 14px;
           border-radius: 12px; cursor: pointer; flex: 1; min-width: 80px; }
  button:active { transform: scale(0.96); }
  .play { background: #10B981; } .pause { background: #F59E0B; } .stop { background: #EF4444; }
  .skip { background: #3B82F6; }
  .opts { display: flex; flex-wrap: wrap; gap: 12px; font-size: 0.9rem; align-items: center; }
  select { font-size: 14px; padding: 6px 8px; border-radius: 8px; border: none; }
</style>
<div class="card">
  <div class="title">🎧 Now Playing: Your PDF</div>
  <div class="bar"><div id="fill"></div></div>
  <div id="info">Ready. Press Play.</div>
  <div class="row">
    <button class="skip" onclick="skip(-10)">⏪ 10s</button>
    <button class="play" onclick="playBtn()">▶️ Play</button>
    <button class="pause" onclick="pauseBtn()">⏸️ Pause</button>
    <button class="skip" onclick="skip(10)">10s ⏩</button>
    <button class="stop" onclick="stopBtn()">⏹️ Stop</button>
  </div>
  <div class="opts">
    <span>⚡ Speed:
      <select id="speed" onchange="setSpeed()">
        <option value="0.75">0.75x</option><option value="1">1x</option>
        <option value="1.25" selected>1.25x</option><option value="1.5">1.5x</option>
        <option value="2">2x</option>
      </select>
    </span>
    <span>🔊 Boost:
      <select id="boost" onchange="setBoost()">
        <option value="1">1x</option><option value="1.5" selected>1.5x</option>
        <option value="2">2x</option><option value="3">3x</option>
      </select>
    </span>
  </div>
</div>
<script>
  var parts = __PARTS__;
  var i = 0, started = false;
  var a = new Audio();
  a.volume = 1.0;
  var ctx = null, gainNode = null;
  var fill = document.getElementById("fill");
  var info = document.getElementById("info");

  function fmt(s) {
    if (!isFinite(s)) s = 0;
    var m = Math.floor(s / 60), r = Math.floor(s % 60);
    return m + ":" + (r < 10 ? "0" : "") + r;
  }
  function updateUI() {
    var d = isFinite(a.duration) ? a.duration : 0;
    var frac = d ? a.currentTime / d : 0;
    fill.style.width = (((i + frac) / parts.length) * 100) + "%";
    info.textContent = "Part " + (i + 1) + " / " + parts.length + "  •  " + fmt(a.currentTime) + " / " + fmt(d);
  }
  a.ontimeupdate = updateUI;

  function setupAudio() {
    if (ctx) return;
    try {
      var AC = window.AudioContext || window.webkitAudioContext;
      ctx = new AC();
      var src = ctx.createMediaElementSource(a);
      gainNode = ctx.createGain();
      src.connect(gainNode);
      gainNode.connect(ctx.destination);
      setBoost();
    } catch (e) { ctx = null; }
  }
  function setSpeed() {
    var s = parseFloat(document.getElementById("speed").value);
    a.defaultPlaybackRate = s;
    a.playbackRate = s;
  }
  function setBoost() {
    if (gainNode) gainNode.gain.value = parseFloat(document.getElementById("boost").value);
  }
  function playPart(idx, offset, fromEnd) {
    i = idx;
    a.onloadedmetadata = function() {
      var d = isFinite(a.duration) ? a.duration : 0;
      a.currentTime = fromEnd ? Math.max(0, d - offset) : offset;
      setSpeed();
      a.play();
    };
    a.src = "data:audio/mp3;base64," + parts[i];
  }
  a.onended = function() {
    if (i < parts.length - 1) { playPart(i + 1, 0, false); }
    else { i = 0; started = false; info.textContent = "Finished ✅"; fill.style.width = "100%"; }
  };
  function playBtn() {
    setupAudio();
    if (ctx && ctx.state === "suspended") ctx.resume();
    if (!started) { started = true; playPart(0, 0, false); }
    else { a.play(); }
  }
  function pauseBtn() { a.pause(); }
  function stopBtn() { a.pause(); i = 0; started = false; fill.style.width = "0%"; info.textContent = "Stopped. Press Play."; }
  function skip(sec) {
    if (!started) return;
    var t = a.currentTime + sec;
    if (sec > 0) {
      if (t < a.duration) { a.currentTime = t; }
      else if (i < parts.length - 1) { playPart(i + 1, t - a.duration, false); }
      else { stopBtn(); }
    } else {
      if (t >= 0) { a.currentTime = t; }
      else if (i > 0) { playPart(i - 1, -t, true); }
      else { a.currentTime = 0; }
    }
  }
</script>
"""

# ---------- App ----------
pdf = st.file_uploader("📄 Upload your PDF", type=["pdf"])

if pdf:
    st.success("✅ PDF uploaded successfully!")
    reader = PdfReader(pdf)
    total = len(reader.pages)

    st.markdown("#### 📑 Select Pages")
    c1, c2 = st.columns(2)
    start = c1.number_input("From page", 1, total, 1)
    end = c2.number_input("To page", 1, total, min(total, 5))

    if end < start:
        st.error("'To page' should be greater than or equal to 'From page'.")
        st.stop()
    if end - start + 1 > MAX_PAGES:
        st.warning(f"Maximum {MAX_PAGES} pages at a time. Please reduce the page range.")
        st.stop()

    text = "\n".join(
        (reader.pages[i].extract_text() or "") for i in range(start - 1, end)
    ).strip()

    if not text:
        st.error("No text found in this PDF (maybe scanned images).")
        st.stop()

    words = len(text.split())
    minutes = max(1, round(words / 150))

    s1, s2, s3 = st.columns(3)
    s1.markdown(f'<div class="stat st1"><span class="n">{total}</span><span class="l">Total Pages</span></div>', unsafe_allow_html=True)
    s2.markdown(f'<div class="stat st2"><span class="n">{words}</span><span class="l">Words</span></div>', unsafe_allow_html=True)
    s3.markdown(f'<div class="stat st3"><span class="n">~{minutes} min</span><span class="l">Listening Time</span></div>', unsafe_allow_html=True)

    st.write("")
    with st.spinner("Converting to voice..."):
        parts = convert(text)
    st.success("🎉 PDF converted to voice successfully!")

    tab1, tab2 = st.tabs(["🎧 Listen", "📖 Extracted Text"])
    with tab1:
        parts_js = "[" + ",".join(f'"{p}"' for p in parts) + "]"
        components.html(PLAYER_HTML.replace("__PARTS__", parts_js), height=280)
    with tab2:
        st.text_area("PDF Text", text, height=300)

st.markdown(
    '<div class="footer">Made with ❤️ using Python • Streamlit • gTTS • pypdf</div>',
    unsafe_allow_html=True,
)
