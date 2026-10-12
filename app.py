import base64
import hmac
import html
import re
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from pypdf import PdfReader

MAX_PAGES = 30
CHUNK_CHARS = 3000
READ_PAGES = 5      # word search: how many pages to read from the match
MAX_RESULTS = 50

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
      .stat {
        border-radius: 14px; padding: 14px; text-align: center; color: white;
        font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.12);
      }
      .stat .n { font-size: 1.7rem; display: block; }
      .stat .l { font-size: 0.85rem; opacity: 0.95; }
      .st1 { background: linear-gradient(135deg,#6366F1,#8B5CF6); }
      .st2 { background: linear-gradient(135deg,#EC4899,#F43F5E); }
      .st3 { background: linear-gradient(135deg,#10B981,#059669); }
      .hit { background: #F5F3FF; border-left: 5px solid #7C3AED; border-radius: 12px;
             padding: 10px 14px; margin-bottom: 8px; color: #1F2937; font-size: 0.92rem; }
      .hit b { color: #7C3AED; }
      mark { background: #FDE047; padding: 0 3px; border-radius: 4px; }
      .footer { text-align: center; color: #6B7280; font-size: 0.85rem; margin-top: 30px; }
    </style>
    <div class="hero">
      <h1>🎧 Smart PDF App</h1>
      <p>Upload a PDF, search any word and listen from there.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- Login ----------
def get_users():
    try:
        return {k: str(v) for k, v in st.secrets["users"].items()}, False
    except Exception:
        return {"student": "pdf123"}, True  # demo login


def check_login(u, p):
    users, _ = get_users()
    return u in users and hmac.compare_digest(users[u], p)


if "user" not in st.session_state:
    st.markdown("### 🔐 Login")
    _, demo = get_users()
    if demo:
        st.info("Demo login: username `student`, password `pdf123`")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Login")
    if ok:
        if check_login(u.strip(), p):
            st.session_state["user"] = u.strip()
            st.rerun()
        else:
            st.error("❌ Wrong username or password.")
    st.stop()

t1, t2 = st.columns([3, 1])
t1.markdown(f"👋 Welcome, **{st.session_state['user']}**")
if t2.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()


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


@st.cache_data(show_spinner=False)
def extract_pages(data):
    reader = PdfReader(BytesIO(data))
    return [(p.extract_text() or "") for p in reader.pages]


def snippet(t, s, e, width=80):
    a, b = max(0, s - width), min(len(t), e + width)
    before = html.escape(t[a:s]).replace("\n", " ")
    mid = html.escape(t[s:e])
    after = html.escape(t[e:b]).replace("\n", " ")
    return ("…" if a > 0 else "") + before + "<mark>" + mid + "</mark>" + after + ("…" if b < len(t) else "")


def plain_snippet(t, s, e, width=35):
    a, b = max(0, s - width), min(len(t), e + width)
    return t[a:b].replace("\n", " ")


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
  .legend { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; font-size: 0.8rem; }
  .legend span { display: flex; align-items: center; gap: 5px; }
  .dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
  .tip { font-size: 0.8rem; opacity: 0.85; margin-top: 8px; }
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
  <div class="legend">
    <span><i class="dot" style="background:#10B981"></i>Play = Start</span>
    <span><i class="dot" style="background:#F59E0B"></i>Pause = Wait</span>
    <span><i class="dot" style="background:#EF4444"></i>Stop = End</span>
    <span><i class="dot" style="background:#3B82F6"></i>10s = Skip</span>
  </div>
  <div class="tip">⚡ Speed = reading speed &nbsp;|&nbsp; 🔊 Boost = louder voice</div>
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
    pages = extract_pages(pdf.getvalue())
    total = len(pages)

    mode = st.radio(
        "How do you want to read?",
        ["📑 Page range", "🔍 Search a word"],
        horizontal=True,
    )

    if mode == "📑 Page range":
        c1, c2 = st.columns(2)
        start = c1.number_input("From page", 1, total, 1)
        end = c2.number_input("To page", 1, total, min(total, 5))

        if end < start:
            st.error("'To page' should be greater than or equal to 'From page'.")
            st.stop()
        if end - start + 1 > MAX_PAGES:
            st.warning(f"Maximum {MAX_PAGES} pages at a time.")
            st.stop()

        text = "\n".join(pages[start - 1:end]).strip()

    else:
        word = st.text_input("🔍 Type a word", placeholder="ex: overfitting")
        if not word.strip():
            st.info("Type a word and I will show you which pages it appears on.")
            st.stop()

        pat = re.compile(re.escape(word.strip()), re.IGNORECASE)
        hits = []
        for pno, t in enumerate(pages, 1):
            for m in pat.finditer(t):
                hits.append((pno, m.start(), m.end()))
                if len(hits) >= MAX_RESULTS:
                    break
            if len(hits) >= MAX_RESULTS:
                break

        if not hits:
            st.warning(f"'{word}' was not found in this PDF.")
            st.stop()

        found_pages = sorted({h[0] for h in hits})
        more = "+" if len(hits) >= MAX_RESULTS else ""
        st.success(f"✅ Found {len(hits)}{more} matches. Pages: {', '.join(map(str, found_pages))}")

        for n, (pno, s, e) in enumerate(hits[:10], 1):
            st.markdown(
                f'<div class="hit"><b>#{n} • Page {pno}</b><br>{snippet(pages[pno - 1], s, e)}</div>',
                unsafe_allow_html=True,
            )
        if len(hits) > 10:
            st.caption("Only the first 10 results are shown above. You can pick any match below.")

        choice = st.selectbox(
            "📍 Where should the reading start?",
            range(len(hits)),
            format_func=lambda k: f"#{k + 1} • Page {hits[k][0]} • …{plain_snippet(pages[hits[k][0] - 1], hits[k][1], hits[k][2])}…",
        )
        pno, s, e = hits[choice]
        line_start = pages[pno - 1].rfind("\n", 0, s) + 1
        first = pages[pno - 1][line_start:]
        rest = pages[pno:pno + READ_PAGES - 1]
        text = "\n".join([first] + rest).strip()
        st.info(f"▶️ Reading {min(READ_PAGES, total - pno + 1)} pages, starting from page {pno}.")

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
    st.success("🎉 Voice ready!")

    tab1, tab2 = st.tabs(["🎧 Listen", "📖 Extracted Text"])
    with tab1:
        parts_js = "[" + ",".join(f'"{p}"' for p in parts) + "]"
        components.html(PLAYER_HTML.replace("__PARTS__", parts_js), height=340)
    with tab2:
        st.text_area("PDF Text", text, height=300)

st.markdown(
    '<div class="footer">Made with ❤️ using Python • Streamlit • gTTS • pypdf</div>',
    unsafe_allow_html=True,
)
