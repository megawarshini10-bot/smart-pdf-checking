import io
import re
import streamlit as st
from pypdf import PdfReader
from gtts import gTTS

# ---------------- PAGE SETTINGS ----------------

st.set_page_config(
    page_title="Smart PDF to Voice",
    page_icon="📖",
    layout="wide"
)

# ---------------- LANGUAGE SETTINGS ----------------

LANGUAGES = {
    "English": "en",
    "Tamil": "ta",
    "Hindi": "hi",
    "Telugu": "te",
    "Malayalam": "ml"
}

# ---------------- SESSION STATE ----------------

if "pages_text" not in st.session_state:
    st.session_state.pages_text = []

if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = ""

if "search_audio" not in st.session_state:
    st.session_state.search_audio = {}

if "selected_page" not in st.session_state:
    st.session_state.selected_page = 1

# ---------------- PDF EXTRACTION ----------------

def extract_pdf(file):
    reader = PdfReader(file)

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return pages


# ---------------- WORD SEARCH ----------------

def find_word_in_pdf(word, pages):
