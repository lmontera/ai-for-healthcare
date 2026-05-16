import base64
import json
import os
from collections import Counter

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://api:8000")
TIMEOUT = int(os.getenv("API_TIMEOUT", "300"))

ENTITY_COLORS = {
    "private_person": "#fecaca",
    "private_email": "#bbf7d0",
    "private_phone": "#bfdbfe",
    "private_address": "#fde68a",
    "private_url": "#ddd6fe",
    "private_date": "#fbcfe8",
    "account_number": "#c7d2fe",
    "secret": "#fca5a5",
}

ENTITY_TEXT_COLORS = {
    "private_person": "#991b1b",
    "private_email": "#166534",
    "private_phone": "#1e40af",
    "private_address": "#92400e",
    "private_url": "#5b21b6",
    "private_date": "#9d174d",
    "account_number": "#3730a3",
    "secret": "#7f1d1d",
}


def _color(label: str) -> str:
    return ENTITY_COLORS.get(label.lower(), "#e5e7eb")


def _text_color(label: str) -> str:
    return ENTITY_TEXT_COLORS.get(label.lower(), "#374151")


def _highlight(text: str, entities: list[dict]) -> str:
    spans = sorted(entities, key=lambda e: e["start"], reverse=True)
    rendered = text
    for ent in spans:
        start, end = ent["start"], ent["end"]
        bg = _color(ent["label"])
        fg = _text_color(ent["label"])
        chunk = rendered[start:end]
        replacement = (
            f'<mark style="background-color:{bg};color:{fg};padding:3px 8px;'
            f'border-radius:6px;font-weight:500;box-shadow:0 1px 2px rgba(0,0,0,0.06);">'
            f'{chunk}<span style="margin-left:6px;font-size:0.65em;'
            f'opacity:0.85;text-transform:uppercase;letter-spacing:0.5px;font-weight:700;">'
            f'{ent["label"].replace("private_", "")}</span></mark>'
        )
        rendered = f"{rendered[:start]}{replacement}{rendered[end:]}"
    return rendered.replace("\n", "<br/>")


def _check_health() -> tuple[bool, str]:
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        return r.ok, r.text
    except requests.RequestException as e:
        return False, str(e)


st.set_page_config(
    page_title="AI for Healthcare",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
  /* Global — broader selectors to survive Streamlit DOM changes */
  html, body, .stApp, [data-testid="stAppViewContainer"], .main, .block-container {
    background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%) !important;
  }
  .block-container {
    padding-top: 2rem !important;
    max-width: 1200px;
  }

  /* Sidebar — multiple selector variants */
  section[data-testid="stSidebar"],
  [data-testid="stSidebar"] > div,
  aside[aria-label="sidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
  }
  section[data-testid="stSidebar"] *,
  [data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
  }

  /* Hide default Streamlit chrome */
  #MainMenu { visibility: hidden; }
  footer { visibility: hidden; }

  /* Sidebar radio overrides */
  section[data-testid="stSidebar"] .stRadio label {
    background: rgba(255,255,255,0.04);
    padding: 10px 14px;
    border-radius: 10px;
    margin-bottom: 6px;
    border: 1px solid rgba(255,255,255,0.06);
    transition: all 0.2s ease;
    cursor: pointer;
  }
  section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(99,102,241,0.18);
    border-color: rgba(99,102,241,0.4);
    transform: translateX(2px);
  }

  /* Headings */
  h1 {
    background: linear-gradient(90deg, #4f46e5 0%, #06b6d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
  }

  /* Cards */
  .hc-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 22px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(15,23,42,0.06);
    border: 1px solid rgba(226,232,240,0.8);
    margin-bottom: 16px;
  }
  .hc-card-title {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
    margin-bottom: 10px;
  }

  /* Metric chips */
  .hc-metric {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #334155;
    margin: 4px 6px 4px 0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }
  .hc-metric .dot {
    width: 8px; height: 8px; border-radius: 50%;
    display: inline-block;
  }

  /* Status pill */
  .hc-status {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
  }
  .hc-status.online { background: rgba(16,185,129,0.15); color: #059669; }
  .hc-status.offline { background: rgba(239,68,68,0.15); color: #dc2626; }
  .hc-status .pulse {
    width: 8px; height: 8px; border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 0 0 currentColor;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(16,185,129,0.6); }
    70% { box-shadow: 0 0 0 8px rgba(16,185,129,0); }
    100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
  }

  /* Buttons */
  .stButton > button {
    border-radius: 10px;
    font-weight: 600;
    padding: 10px 22px;
    transition: all 0.2s ease;
    border: 1px solid transparent;
  }
  .stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #4f46e5 0%, #6366f1 100%);
    border: none;
    box-shadow: 0 4px 12px rgba(79,70,229,0.3);
  }
  .stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(79,70,229,0.4);
  }

  /* Inputs */
  .stTextArea textarea, .stTextInput input {
    border-radius: 10px !important;
    border: 1px solid #e2e8f0 !important;
    font-family: ui-sans-serif, system-ui, sans-serif;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
  }

  /* File uploader */
  [data-testid="stFileUploader"] section {
    border: 2px dashed #cbd5e1;
    border-radius: 14px;
    background: #ffffff;
    transition: all 0.2s ease;
  }
  [data-testid="stFileUploader"] section:hover {
    border-color: #6366f1;
    background: #f5f3ff;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #ffffff;
    padding: 6px;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    color: #64748b;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #4f46e5 0%, #6366f1 100%) !important;
    color: #fff !important;
  }

  /* Transcript box */
  .hc-segment {
    padding: 10px 14px;
    background: #f8fafc;
    border-left: 3px solid #6366f1;
    border-radius: 0 8px 8px 0;
    margin-bottom: 8px;
    font-size: 0.92rem;
  }
  .hc-segment .ts {
    font-family: ui-monospace, monospace;
    font-size: 0.75rem;
    color: #6366f1;
    font-weight: 700;
    margin-right: 10px;
  }

  /* Highlighted text container */
  .hc-text-output {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px 20px;
    line-height: 1.9;
    font-size: 0.95rem;
    color: #1e293b;
  }

  /* Hero header */
  .hc-hero {
    padding: 8px 0 24px 0;
    border-bottom: 1px solid #e2e8f0;
    margin-bottom: 28px;
  }
  .hc-hero .subtitle {
    color: #64748b;
    font-size: 1.05rem;
    margin-top: -8px;
  }
</style>
""",
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown(
        """
<div style="padding: 8px 0 18px 0;">
  <div style="font-size: 1.4rem; font-weight: 800; letter-spacing: -0.02em;">
    🩺 AI for Healthcare
  </div>
  <div style="font-size: 0.78rem; opacity: 0.65; margin-top: 4px;">
    Privacy & speech toolkit
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    ok, info = _check_health()
    status_class = "online" if ok else "offline"
    status_text = "API online" if ok else "API offline"
    st.markdown(
        f'<div class="hc-status {status_class}"><span class="pulse"></span>{status_text}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-size: 0.72rem; opacity: 0.55; margin: 8px 0 18px 0; font-family: ui-monospace, monospace;">{API_URL}</div>',
        unsafe_allow_html=True,
    )
    if not ok:
        st.caption(info)

    st.markdown(
        '<div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.5; margin-bottom: 8px;">Servizi</div>',
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Servizio",
        ["📄 Anonymize Document", "🔍 PII Detect", "🎙️ Transcription", "⚡ Realtime STT"],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("<div style='flex:1; min-height: 40px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
<div style="position: absolute; bottom: 20px; left: 20px; right: 20px; font-size: 0.7rem; opacity: 0.4; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px;">
  FastAPI · LangGraph · WhisperLive
</div>
""",
        unsafe_allow_html=True,
    )


def _hero(title: str, subtitle: str):
    st.markdown(
        f'<div class="hc-hero"><h1 style="margin-bottom:4px;">{title}</h1>'
        f'<div class="subtitle">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


if page == "📄 Anonymize Document":
    _hero(
        "Anonymize Document",
        "Carica un'immagine → OCR (docTR) → anonimizzazione (openai/privacy-filter)",
    )

    uploaded = st.file_uploader(
        "Trascina un documento qui o sfoglia",
        type=["png", "jpg", "jpeg"],
        label_visibility="visible",
    )

    if uploaded is not None:
        col1, col2 = st.columns([1, 1], gap="large")

        with col1:
            st.markdown('<div class="hc-card-title">📷 Documento</div>', unsafe_allow_html=True)
            st.image(uploaded, use_container_width=True)
            run = st.button("🚀 Esegui anonimizzazione", type="primary", use_container_width=True)

        with col2:
            if run:
                image_b64 = base64.b64encode(uploaded.getvalue()).decode("utf-8")
                with st.spinner("🧠 OCR + anonimizzazione in corso..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/anonymize",
                            json={"image_base64": image_b64},
                            timeout=TIMEOUT,
                        )
                        r.raise_for_status()
                        data = r.json()
                    except requests.RequestException as exc:
                        st.error(f"Errore API: {exc}")
                    else:
                        tab1, tab2 = st.tabs(["🔒 Anonimizzato", "📝 OCR grezzo"])
                        with tab1:
                            st.text_area(
                                "Output",
                                data["anonymized_text"],
                                height=320,
                                label_visibility="collapsed",
                            )
                            st.download_button(
                                "⬇️ Scarica testo anonimizzato",
                                data["anonymized_text"],
                                file_name="anonymized.txt",
                                use_container_width=True,
                            )
                        with tab2:
                            st.text_area(
                                "OCR",
                                data["ocr_text"],
                                height=320,
                                label_visibility="collapsed",
                            )
            else:
                st.markdown(
                    '<div class="hc-card" style="text-align:center; color:#94a3b8; padding: 60px 20px;">'
                    '<div style="font-size: 2.5rem; margin-bottom: 8px;">✨</div>'
                    "<div>Premi <b>Esegui anonimizzazione</b> per avviare la pipeline OCR → anonymization</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            '<div class="hc-card" style="text-align:center; color:#94a3b8; padding: 70px 20px;">'
            '<div style="font-size: 3rem; margin-bottom: 12px;">📄</div>'
            '<div style="font-size: 1.05rem; color:#475569; font-weight: 600;">Nessun documento caricato</div>'
            '<div style="font-size: 0.9rem; margin-top: 4px;">Carica un PNG o JPEG per iniziare</div>'
            "</div>",
            unsafe_allow_html=True,
        )


elif page == "🔍 PII Detect":
    _hero(
        "PII Detect",
        "Testo libero → entità PII rilevate (OpenMed Italian medical model)",
    )

    text = st.text_area(
        "Testo da analizzare",
        height=200,
        placeholder="Paziente Marco Bianchi nato il 15/03/1985, email marco.bianchi@email.it...",
    )

    col_a, col_b = st.columns([1, 4])
    with col_a:
        run = st.button(
            "🔍 Analizza",
            type="primary",
            disabled=not text.strip(),
            use_container_width=True,
        )

    if run:
        with st.spinner("Analisi in corso..."):
            try:
                r = requests.post(
                    f"{API_URL}/pii/detect",
                    json={"text": text},
                    timeout=TIMEOUT,
                )
                r.raise_for_status()
                data = r.json()
            except requests.RequestException as exc:
                st.error(f"Errore API: {exc}")
            else:
                entities = data.get("entities", [])
                counts = Counter(e["label"] for e in entities)

                m1, m2, m3 = st.columns(3)
                m1.metric("Entità rilevate", len(entities))
                m2.metric("Tipi distinti", len(counts))
                avg_score = (
                    sum(e.get("score", 0) for e in entities) / len(entities)
                    if entities
                    else 0.0
                )
                m3.metric("Score medio", f"{avg_score:.2%}")

                if counts:
                    chips = "".join(
                        f'<span class="hc-metric"><span class="dot" style="background:{_color(lbl)};"></span>'
                        f'{lbl.replace("private_", "")} · {n}</span>'
                        for lbl, n in counts.most_common()
                    )
                    st.markdown(
                        f'<div style="margin: 8px 0 18px 0;">{chips}</div>',
                        unsafe_allow_html=True,
                    )

                tab1, tab2 = st.tabs(["🖍️ Testo evidenziato", "📊 Dettaglio entità"])
                with tab1:
                    st.markdown(
                        f'<div class="hc-text-output">{_highlight(text, entities)}</div>',
                        unsafe_allow_html=True,
                    )
                with tab2:
                    if entities:
                        st.dataframe(
                            entities,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "label": st.column_config.TextColumn("Tipo", width="medium"),
                                "text": st.column_config.TextColumn("Testo", width="large"),
                                "start": st.column_config.NumberColumn("Inizio", width="small"),
                                "end": st.column_config.NumberColumn("Fine", width="small"),
                                "score": st.column_config.ProgressColumn(
                                    "Score",
                                    format="%.3f",
                                    min_value=0.0,
                                    max_value=1.0,
                                ),
                            },
                        )
                    else:
                        st.info("Nessuna entità rilevata.")


elif page == "🎙️ Transcription":
    _hero(
        "Transcription",
        "Registra audio → trascrizione streaming (medwhisper-large-v3 italiano)",
    )

    st.markdown(
        '<div class="hc-card" style="background: linear-gradient(90deg, #eff6ff 0%, #ede9fe 100%); '
        'border-color: #c7d2fe; color: #4338ca;">'
        '💡 <b>Suggerimento:</b> su CPU large-v3 va più lento del realtime. I segmenti '
        "compaiono progressivamente man mano che il modello li produce."
        "</div>",
        unsafe_allow_html=True,
    )

    audio = st.audio_input("🎙️ Registra audio")

    if audio is not None:
        run = st.button("✨ Trascrivi", type="primary", use_container_width=False)
        if run:
            segments_acc: list[dict] = []
            placeholder = st.empty()
            full_text_holder = st.empty()
            status_holder = st.empty()

            status_holder.markdown(
                '<div class="hc-status online" style="background: rgba(99,102,241,0.15); color:#4f46e5;">'
                '<span class="pulse"></span>Trascrizione in corso...</div>',
                unsafe_allow_html=True,
            )

            try:
                with requests.post(
                    f"{API_URL}/transcribe",
                    files={"audio": ("audio.wav", audio.getvalue(), "audio/wav")},
                    stream=True,
                    timeout=TIMEOUT,
                ) as r:
                    r.raise_for_status()
                    for line in r.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        seg = json.loads(line)
                        segments_acc.append(seg)
                        segments_html = "".join(
                            f'<div class="hc-segment">'
                            f'<span class="ts">[{s["start"]:.1f}s → {s["end"]:.1f}s]</span>'
                            f"{s['text']}</div>"
                            for s in segments_acc
                        )
                        placeholder.markdown(
                            f'<div class="hc-card"><div class="hc-card-title">'
                            f"🎬 Segmenti ({len(segments_acc)})</div>{segments_html}</div>",
                            unsafe_allow_html=True,
                        )
                        full_text_holder.text_area(
                            "📄 Testo completo",
                            " ".join(s["text"].strip() for s in segments_acc),
                            height=160,
                        )
            except requests.RequestException as exc:
                status_holder.error(f"Errore API: {exc}")
            else:
                status_holder.success(
                    f"✅ Trascrizione completata · {len(segments_acc)} segmenti"
                )
                if segments_acc:
                    st.download_button(
                        "⬇️ Scarica trascrizione",
                        " ".join(s["text"].strip() for s in segments_acc),
                        file_name="transcript.txt",
                    )


elif page == "⚡ Realtime STT":
    import streamlit.components.v1 as components

    _hero(
        "Realtime STT",
        "WhisperLive + medwhisper-large-v3 italiano — streaming WebSocket live",
    )

    st.markdown(
        '<div class="hc-card" style="background: linear-gradient(90deg, #fef3c7 0%, #fed7aa 100%); '
        'border-color: #fcd34d; color: #92400e;">'
        '⚠️ <b>Attenzione:</b> su CPU con large-v3 i parziali hanno qualche secondo di lag. '
        "Il primo avvio carica il modello (può richiedere alcuni minuti)."
        "</div>",
        unsafe_allow_html=True,
    )

    ws_url = os.getenv("WHISPERLIVE_URL", "ws://localhost:9090")
    model_name = "ReportAId/medwhisper-large-v3-ita-ct2"

    html = """
<!DOCTYPE html>
<html>
<head>
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    padding: 0; margin: 0;
    background: transparent;
  }
  .panel {
    background: #ffffff;
    border-radius: 16px;
    padding: 20px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(15,23,42,0.06);
  }
  .controls {
    display: flex; gap: 10px; align-items: center; margin-bottom: 16px;
    flex-wrap: wrap;
  }
  button {
    padding: 10px 18px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #ffffff;
    color: #334155;
    transition: all 0.2s ease;
    display: inline-flex; align-items: center; gap: 8px;
  }
  button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  button.primary {
    background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
    color: #fff; border: none;
    box-shadow: 0 4px 12px rgba(239,68,68,0.3);
  }
  button.stop {
    background: linear-gradient(90deg, #475569 0%, #334155 100%);
    color: #fff; border: none;
  }
  #status {
    display: inline-flex; align-items: center; gap: 8px;
    color: #475569; font-size: 13px; font-weight: 500;
    padding: 6px 12px;
    background: #f1f5f9;
    border-radius: 999px;
  }
  #status .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #94a3b8;
  }
  #status.active .dot { background: #10b981; animation: pulse 1.5s infinite; }
  #status.recording .dot { background: #ef4444; animation: pulse 1s infinite; }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.3); }
  }
  #transcript {
    padding: 16px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    min-height: 260px;
    max-height: 380px;
    overflow-y: auto;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #1e293b;
  }
  .segment {
    padding: 8px 12px;
    background: #ffffff;
    border-left: 3px solid #6366f1;
    border-radius: 0 8px 8px 0;
    margin-bottom: 8px;
  }
  .segment .ts {
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 11px;
    color: #6366f1;
    font-weight: 700;
    display: block;
    margin-bottom: 2px;
  }
  .empty {
    text-align: center;
    color: #94a3b8;
    padding: 60px 20px;
    font-size: 14px;
  }
  .empty .icon { font-size: 2rem; margin-bottom: 8px; }
</style>
</head>
<body>
<div class="panel">
  <div class="controls">
    <button id="start" class="primary">● Start recording</button>
    <button id="stop" class="stop" disabled>■ Stop</button>
    <span id="status"><span class="dot"></span><span id="status-text">Pronto</span></span>
  </div>
  <div id="transcript">
    <div class="empty">
      <div class="icon">🎤</div>
      <div>Premi <b>Start recording</b> per iniziare la trascrizione in tempo reale</div>
    </div>
  </div>
</div>
<script>
const WS_URL = "__WS_URL__";
const MODEL_NAME = "__MODEL_NAME__";

const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");
const transcriptEl = document.getElementById("transcript");

let ws = null, audioCtx = null, stream = null, source = null, processor = null;
let segments = [];

function uid() { return Math.random().toString(36).slice(2) + Date.now().toString(36); }
function setStatus(t, cls) {
  statusText.textContent = t;
  statusEl.className = cls || "";
}
function render() {
  if (segments.length === 0) {
    transcriptEl.innerHTML = '<div class="empty"><div class="icon">🎤</div><div>In ascolto...</div></div>';
    return;
  }
  transcriptEl.innerHTML = segments.map(s =>
    `<div class="segment"><span class="ts">[${(+s.start).toFixed(1)}s → ${(+s.end).toFixed(1)}s]</span>${s.text}</div>`
  ).join("");
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

startBtn.onclick = async () => {
  startBtn.disabled = true;
  segments = [];
  render();

  if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    const origin = window.location.origin;
    transcriptEl.innerHTML = `
      <div class="empty" style="text-align:left; color:#7f1d1d; background:#fef2f2; border:1px solid #fecaca; border-radius:10px; padding:18px;">
        <div style="font-weight:700; font-size:15px; margin-bottom:8px;">🔒 Microfono non accessibile</div>
        <div style="color:#475569; font-size:13px; line-height:1.6;">
          Il browser blocca <code>getUserMedia</code> perché stai aprendo Streamlit da
          <code>${origin}</code>, che non è un contesto sicuro (serve <b>https://</b> o <b>localhost</b>).
          <br/><br/>
          <b>Soluzioni:</b>
          <ul style="margin:6px 0 0 18px; padding:0;">
            <li>SSH port-forward: <code>ssh -L 8501:localhost:8501 -L 9090:localhost:9090 user@server</code> e apri <code>http://localhost:8501</code></li>
            <li>Servi Streamlit dietro HTTPS (e usa <code>wss://</code> per WhisperLive)</li>
            <li>Solo dev/Chrome: <code>chrome://flags/#unsafely-treat-insecure-origin-as-secure</code></li>
          </ul>
        </div>
      </div>`;
    setStatus("Contesto non sicuro", "");
    startBtn.disabled = false;
    return;
  }

  setStatus("Apro microfono...", "active");
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
    });
  } catch (e) {
    setStatus("Errore microfono: " + e.message, "");
    startBtn.disabled = false;
    return;
  }

  audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
  source = audioCtx.createMediaStreamSource(stream);
  processor = audioCtx.createScriptProcessor(2048, 1, 1);
  source.connect(processor);
  processor.connect(audioCtx.destination);

  setStatus("Connessione WS...", "active");
  ws = new WebSocket(WS_URL);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    const config = {
      uid: uid(),
      language: "it",
      task: "transcribe",
      model: MODEL_NAME,
      use_vad: true,
      same_output_threshold: 5,
      send_last_n_segments: 10,
      no_speech_thresh: 0.45,
      initial_prompt: "Visita oculistica. Anamnesi e referto in italiano. Termini: visus, acuità visiva, diottrie, miopia, ipermetropia, astigmatismo, presbiopia, cornea, cristallino, retina, macula, fovea, iride, pupilla, sclera, congiuntiva, coroide, nervo ottico, papilla, vitreo, camera anteriore, tonometria, pressione intraoculare, PIO, IOP, glaucoma, cataratta, retinopatia diabetica, maculopatia, degenerazione maculare, distacco di retina, occlusione venosa, edema maculare, neovascolarizzazione, biomicroscopia, oftalmoscopia, OCT, fluorangiografia, angio-OCT, campo visivo, ecografia oculare, FACO, IOL, LASIK, PRK, vitrectomia, blefarite, congiuntivite, uveite, cheratite, ambliopia, strabismo.",
      max_clients: 4,
      max_connection_time: 600
    };
    ws.send(JSON.stringify(config));
    setStatus("Caricamento modello (può richiedere minuti)...", "active");
    stopBtn.disabled = false;
  };

  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch (e) { return; }
    if (msg.message === "SERVER_READY") {
      setStatus("Registrazione · parla in italiano", "recording");
    } else if (msg.message === "DISCONNECT") {
      setStatus("Disconnesso", "");
    } else if (msg.segments) {
      segments = msg.segments;
      render();
    }
  };

  ws.onerror = () => setStatus("Errore WebSocket", "");
  ws.onclose = () => setStatus("Connessione chiusa", "");

  processor.onaudioprocess = (e) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const data = e.inputBuffer.getChannelData(0);
    ws.send(data.buffer);
  };
};

stopBtn.onclick = () => {
  try { processor && processor.disconnect(); } catch (e) {}
  try { source && source.disconnect(); } catch (e) {}
  try { stream && stream.getTracks().forEach(t => t.stop()); } catch (e) {}
  try { audioCtx && audioCtx.close(); } catch (e) {}
  try { ws && ws.close(); } catch (e) {}
  startBtn.disabled = false;
  stopBtn.disabled = true;
  setStatus("Stop", "");
};
</script>
</body>
</html>
""".replace("__WS_URL__", ws_url).replace("__MODEL_NAME__", model_name)

    components.html(html, height=520, scrolling=False)
