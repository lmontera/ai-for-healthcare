import base64
import binascii
import html
import json
import os
import re
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


PLACEHOLDER_COLORS = {
    "FIRSTNAME": ("#fecaca", "#991b1b"),
    "LASTNAME": ("#fecaca", "#991b1b"),
    "NAME": ("#fecaca", "#991b1b"),
    "PERSON": ("#fecaca", "#991b1b"),
    "PATIENT": ("#fecaca", "#991b1b"),
    "DATE": ("#fbcfe8", "#9d174d"),
    "DOB": ("#fbcfe8", "#9d174d"),
    "TIME": ("#fbcfe8", "#9d174d"),
    "EMAIL": ("#bbf7d0", "#166534"),
    "PHONE": ("#bfdbfe", "#1e40af"),
    "FAX": ("#bfdbfe", "#1e40af"),
    "ADDRESS": ("#fde68a", "#92400e"),
    "CITY": ("#fde68a", "#92400e"),
    "ZIP": ("#fde68a", "#92400e"),
    "URL": ("#ddd6fe", "#5b21b6"),
    "ID": ("#c7d2fe", "#3730a3"),
    "SSN": ("#c7d2fe", "#3730a3"),
    "MRN": ("#c7d2fe", "#3730a3"),
    "ACCOUNT": ("#c7d2fe", "#3730a3"),
}

_PLACEHOLDER_RE = re.compile(r"\[([A-Z][A-Z0-9_]*)\]")


def _highlight_placeholders(text: str) -> str:
    escaped = html.escape(text)

    def repl(m: re.Match) -> str:
        label = m.group(1)
        bg, fg = PLACEHOLDER_COLORS.get(label, ("#e5e7eb", "#374151"))
        return (
            f'<span style="background:{bg};color:{fg};padding:2px 6px;'
            f'border-radius:4px;font-weight:600;font-size:0.82em;'
            f'letter-spacing:0.4px;margin:0 2px;">[{label}]</span>'
        )

    return _PLACEHOLDER_RE.sub(repl, escaped).replace("\n", "<br/>")


def _highlight(text: str, entities: list[dict]) -> str:
    spans = sorted(entities, key=lambda e: e["start"], reverse=True)
    rendered = text
    for ent in spans:
        start, end = ent["start"], ent["end"]
        bg = _color(ent["label"])
        fg = _text_color(ent["label"])
        chunk = rendered[start:end]
        replacement = (
            f'<mark style="background-color:{bg};color:{fg};padding:2px 6px;'
            f'border-radius:3px;font-weight:500;">'
            f'{chunk}<span style="margin-left:6px;font-size:0.7em;'
            f'opacity:0.75;text-transform:uppercase;letter-spacing:0.4px;font-weight:600;">'
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
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
  html, body, .stApp, [data-testid="stAppViewContainer"], .main, .block-container {
    background: #fafafa !important;
  }
  .block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1100px;
  }

  section[data-testid="stSidebar"],
  [data-testid="stSidebar"] > div {
    background: #ffffff !important;
    border-right: 1px solid #e5e7eb;
  }
  section[data-testid="stSidebar"] * {
    color: #1f2937 !important;
  }

  #MainMenu { visibility: hidden; }
  footer { visibility: hidden; }
  header[data-testid="stHeader"] { background: transparent; }

  /* Sidebar layout */
  section[data-testid="stSidebar"] .block-container {
    padding-top: 1.75rem !important;
    padding-left: 1.1rem !important;
    padding-right: 1.1rem !important;
  }

  /* Sidebar nav (radio) */
  section[data-testid="stSidebar"] .stRadio > div {
    gap: 1px;
  }
  section[data-testid="stSidebar"] .stRadio label {
    position: relative;
    background: transparent;
    padding: 7px 10px 7px 14px;
    border-radius: 4px;
    margin: 0;
    border: none;
    cursor: pointer;
    font-size: 0.875rem;
    color: #4b5563 !important;
    transition: background 0.12s ease, color 0.12s ease;
  }
  section[data-testid="stSidebar"] .stRadio label:hover {
    background: #f3f4f6;
    color: #111827 !important;
  }
  /* Hide the default radio dot */
  section[data-testid="stSidebar"] .stRadio label > div:first-child {
    display: none !important;
  }
  /* Active item: left bar + bold text + light bg */
  section[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: #f3f4f6;
    color: #111827 !important;
    font-weight: 600;
  }
  section[data-testid="stSidebar"] .stRadio label:has(input:checked)::before {
    content: "";
    position: absolute;
    left: 4px;
    top: 8px;
    bottom: 8px;
    width: 2px;
    background: #111827;
    border-radius: 2px;
  }
  section[data-testid="stSidebar"] .stRadio label p {
    font-size: 0.875rem !important;
    color: inherit !important;
  }

  /* Sidebar section heading */
  .hc-nav-heading {
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #9ca3af;
    font-weight: 600;
    margin: 18px 0 6px 14px;
  }

  /* Brand mark */
  .hc-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 2px 4px 18px 4px;
  }
  .hc-brand-mark {
    width: 28px; height: 28px;
    border-radius: 6px;
    background: #111827;
    color: #ffffff;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    flex-shrink: 0;
  }
  .hc-brand-name {
    font-size: 0.92rem;
    font-weight: 600;
    color: #111827;
    line-height: 1.1;
  }
  .hc-brand-tag {
    font-size: 0.7rem;
    color: #6b7280;
    margin-top: 2px;
  }

  /* Sidebar meta block */
  .hc-meta {
    padding: 10px 12px;
    background: #fafafa;
    border: 1px solid #e5e7eb;
    border-radius: 5px;
    margin: 4px 0 8px 0;
  }
  .hc-meta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.74rem;
  }
  .hc-meta-label {
    color: #6b7280;
    font-weight: 500;
  }
  .hc-meta-value {
    color: #111827;
    font-family: ui-monospace, monospace;
    font-size: 0.7rem;
    max-width: 130px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hc-meta-dot {
    width: 6px; height: 6px; border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
    vertical-align: middle;
  }
  .hc-meta-dot.online { background: #16a34a; }
  .hc-meta-dot.offline { background: #dc2626; }

  /* Sidebar footer */
  .hc-foot {
    margin-top: 28px;
    padding-top: 12px;
    border-top: 1px solid #e5e7eb;
    font-size: 0.68rem;
    color: #9ca3af;
    line-height: 1.5;
  }
  .hc-foot strong {
    color: #6b7280;
    font-weight: 600;
  }

  h1, h2, h3 {
    color: #111827 !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
  }
  h1 {
    font-size: 1.6rem !important;
    margin-bottom: 0.25rem !important;
  }

  .hc-subtitle {
    color: #6b7280;
    font-size: 0.95rem;
    margin-bottom: 1.75rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .hc-card {
    background: #ffffff;
    border-radius: 6px;
    padding: 18px 20px;
    border: 1px solid #e5e7eb;
    margin-bottom: 14px;
  }
  .hc-card-title {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6b7280;
    margin-bottom: 10px;
  }

  .hc-metric {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
    color: #374151;
    margin: 3px 4px 3px 0;
  }
  .hc-metric .dot {
    width: 6px; height: 6px; border-radius: 50%;
    display: inline-block;
  }

  .hc-status {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 9px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
    border: 1px solid;
  }
  .hc-status.online { background: #f0fdf4; color: #15803d; border-color: #bbf7d0; }
  .hc-status.offline { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
  .hc-status .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: currentColor;
  }

  .stButton > button {
    border-radius: 5px;
    font-weight: 500;
    padding: 6px 16px;
    font-size: 0.88rem;
    border: 1px solid #d1d5db;
    background: #ffffff;
    color: #374151;
    transition: background 0.15s ease, border-color 0.15s ease;
  }
  .stButton > button:hover {
    background: #f9fafb;
    border-color: #9ca3af;
  }
  .stButton > button[kind="primary"] {
    background: #1f2937;
    border-color: #1f2937;
    color: #ffffff;
  }
  .stButton > button[kind="primary"]:hover {
    background: #111827;
    border-color: #111827;
  }

  .stTextArea textarea, .stTextInput input {
    border-radius: 5px !important;
    border: 1px solid #d1d5db !important;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 0.9rem !important;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #6b7280 !important;
    box-shadow: 0 0 0 1px #6b7280 !important;
  }

  [data-testid="stFileUploader"] section {
    border: 1px dashed #d1d5db;
    border-radius: 6px;
    background: #ffffff;
  }
  [data-testid="stFileUploader"] section:hover {
    border-color: #9ca3af;
    background: #fafafa;
  }

  .stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: transparent;
    padding: 0;
    border-bottom: 1px solid #e5e7eb;
    border-radius: 0;
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 0;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 0.88rem;
    color: #6b7280;
    border-bottom: 2px solid transparent;
  }
  .stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #111827 !important;
    border-bottom: 2px solid #111827 !important;
  }

  .hc-segment {
    padding: 8px 12px;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-left: 2px solid #6b7280;
    border-radius: 0 3px 3px 0;
    margin-bottom: 6px;
    font-size: 0.9rem;
    color: #1f2937;
  }
  .hc-segment .ts {
    font-family: ui-monospace, monospace;
    font-size: 0.72rem;
    color: #6b7280;
    font-weight: 600;
    margin-right: 10px;
  }

  .hc-text-output {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 16px 18px;
    line-height: 1.8;
    font-size: 0.92rem;
    color: #1f2937;
  }

  .hc-empty {
    background: #ffffff;
    border: 1px dashed #e5e7eb;
    border-radius: 6px;
    padding: 48px 20px;
    text-align: center;
    color: #9ca3af;
    font-size: 0.9rem;
  }

  .hc-note {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-left: 3px solid #9ca3af;
    border-radius: 0 4px 4px 0;
    padding: 10px 14px;
    color: #4b5563;
    font-size: 0.85rem;
    margin-bottom: 16px;
  }
</style>
""",
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown(
        """
<div class="hc-brand">
  <div class="hc-brand-mark">AI</div>
  <div>
    <div class="hc-brand-name">AI for Healthcare</div>
    <div class="hc-brand-tag">Privacy &amp; speech toolkit</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    ok, info = _check_health()
    status_class = "online" if ok else "offline"
    status_label = "Online" if ok else "Offline"
    st.markdown(
        f"""
<div class="hc-meta">
  <div class="hc-meta-row">
    <span class="hc-meta-label"><span class="hc-meta-dot {status_class}"></span>API {status_label}</span>
    <span class="hc-meta-value" title="{API_URL}">{API_URL}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    if not ok:
        st.caption(info)

    st.markdown('<div class="hc-nav-heading">Servizi</div>', unsafe_allow_html=True)

    page = st.radio(
        "Servizio",
        [
            "Anonimizza documento",
            "Anonymization with LLM",
            "Rilevamento PII",
            "Trascrizione",
            "Trascrizione live",
            "Real-time STT + EHR",
            "Strutturazione FHIR",
            "Classificazione immagine",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown(
        """
<div class="hc-foot">
  <div><strong>Stack</strong></div>
  <div>FastAPI · LangGraph · WhisperLive</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _hero(title: str, subtitle: str):
    st.markdown(
        f'<h1>{title}</h1><div class="hc-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


if page == "Anonimizza documento":
    _hero(
        "Anonimizza documento",
        "OCR (docTR) e anonimizzazione (openai/privacy-filter) su immagini di documenti clinici.",
    )

    uploaded = st.file_uploader(
        "Trascina un documento o sfoglia",
        type=["png", "jpg", "jpeg"],
        label_visibility="visible",
    )

    if uploaded is not None:
        col1, col2 = st.columns([1, 1], gap="large")

        with col1:
            st.markdown('<div class="hc-card-title">Documento</div>', unsafe_allow_html=True)
            st.image(uploaded, use_container_width=True)
            run = st.button("Esegui anonimizzazione", type="primary", use_container_width=True)

        with col2:
            if run:
                image_b64 = base64.b64encode(uploaded.getvalue()).decode("utf-8")
                with st.spinner("Elaborazione in corso..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/anonymize/masked",
                            json={"image_base64": image_b64},
                            timeout=TIMEOUT,
                        )
                        r.raise_for_status()
                        data = r.json()
                    except requests.RequestException as exc:
                        st.error(f"Errore API: {exc}")
                    else:
                        tab_img, tab_txt, tab_ocr = st.tabs(
                            ["Immagine anonimizzata", "Anonimizzato", "OCR grezzo"]
                        )
                        with tab_img:
                            masked_b64 = data.get("masked_image_base64", "")
                            n_ent = data.get("entities_count", 0)
                            if masked_b64:
                                try:
                                    masked_bytes = base64.b64decode(masked_b64)
                                except (binascii.Error, ValueError):
                                    masked_bytes = b""
                                if masked_bytes:
                                    st.image(masked_bytes, use_container_width=True)
                                    st.caption(f"PII coperti: {n_ent}")
                                    st.download_button(
                                        "Scarica immagine anonimizzata (PNG)",
                                        data=masked_bytes,
                                        file_name="anonymized.png",
                                        mime="image/png",
                                        use_container_width=True,
                                    )
                                else:
                                    st.warning("Immagine anonimizzata non disponibile.")
                            else:
                                st.warning("Immagine anonimizzata non restituita dall'API.")
                        with tab_txt:
                            st.markdown(
                                f'<div class="hc-text-output">'
                                f'{_highlight_placeholders(data.get("anonymized_text", ""))}'
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                            st.download_button(
                                "Scarica testo anonimizzato",
                                data.get("anonymized_text", ""),
                                file_name="anonymized.txt",
                                use_container_width=True,
                            )
                        with tab_ocr:
                            st.text_area(
                                "OCR",
                                data.get("ocr_text", ""),
                                height=320,
                                label_visibility="collapsed",
                            )
            else:
                st.markdown(
                    '<div class="hc-empty">Premi <b>Esegui anonimizzazione</b> per avviare la pipeline OCR e anonimizzazione.</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            '<div class="hc-empty">Nessun documento caricato. Carica un PNG o JPEG per iniziare.</div>',
            unsafe_allow_html=True,
        )


elif page == "Anonymization with LLM":
    _hero(
        "Anonymization with LLM",
        "OCR del documento + anonimizzazione testuale tramite gpt-oss-20b via Ollama.",
    )

    uploaded_llm = st.file_uploader(
        "Carica un documento medico",
        type=["png", "jpg", "jpeg"],
        key="anonllm_uploader",
    )

    if uploaded_llm is not None:
        col_doc, col_out = st.columns([1, 1], gap="large")
        with col_doc:
            st.markdown('<div class="hc-card-title">Documento</div>', unsafe_allow_html=True)
            st.image(uploaded_llm, use_container_width=True)
            run_llm = st.button(
                "Anonimizza con LLM",
                type="primary",
                use_container_width=True,
                key="anonllm_btn",
            )

        with col_out:
            if run_llm:
                image_b64 = base64.b64encode(uploaded_llm.getvalue()).decode("utf-8")
                with st.spinner("OCR + PII + LLM in corso..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/anonymize-llm/masked",
                            json={"image_base64": image_b64},
                            timeout=TIMEOUT,
                        )
                        r.raise_for_status()
                        data = r.json()
                    except requests.RequestException as exc:
                        st.error(f"Errore API: {exc}")
                    else:
                        tab_img, tab_txt, tab_ocr = st.tabs(
                            ["Immagine anonimizzata", "Anonimizzato (LLM)", "OCR grezzo"]
                        )
                        with tab_img:
                            masked_b64 = data.get("masked_image_base64", "")
                            n_ent = data.get("entities_count", 0)
                            if masked_b64:
                                try:
                                    masked_bytes = base64.b64decode(masked_b64)
                                except (binascii.Error, ValueError):
                                    masked_bytes = b""
                                if masked_bytes:
                                    st.image(masked_bytes, use_container_width=True)
                                    st.caption(f"PII coperti: {n_ent}")
                                    st.download_button(
                                        "Scarica immagine anonimizzata (PNG)",
                                        data=masked_bytes,
                                        file_name="anonymized_llm.png",
                                        mime="image/png",
                                        use_container_width=True,
                                    )
                                else:
                                    st.warning("Immagine anonimizzata non disponibile.")
                            else:
                                st.warning("Immagine anonimizzata non restituita dall'API.")
                        with tab_txt:
                            st.markdown(
                                f'<div class="hc-text-output">'
                                f'{_highlight_placeholders(data.get("anonymized_text", ""))}'
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                            st.download_button(
                                "Scarica testo anonimizzato",
                                data.get("anonymized_text", ""),
                                file_name="anonymized_llm.txt",
                                use_container_width=True,
                            )
                        with tab_ocr:
                            st.text_area(
                                "OCR",
                                data.get("ocr_text", ""),
                                height=320,
                                label_visibility="collapsed",
                            )
            else:
                st.markdown(
                    '<div class="hc-empty">Premi <b>Anonimizza con LLM</b> per avviare la pipeline OCR + PII + LLM.</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            '<div class="hc-empty">Nessun documento caricato. Carica un PNG/JPEG per iniziare.</div>',
            unsafe_allow_html=True,
        )


elif page == "Rilevamento PII":
    _hero(
        "Rilevamento PII",
        "Estrazione di entità sensibili da testo libero (OpenMed Italian medical model).",
    )

    text = st.text_area(
        "Testo da analizzare",
        height=200,
        placeholder="Paziente Marco Bianchi nato il 15/03/1985, email marco.bianchi@email.it...",
    )

    col_a, col_b = st.columns([1, 4])
    with col_a:
        run = st.button(
            "Analizza",
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

                tab1, tab2 = st.tabs(["Testo evidenziato", "Dettaglio entità"])
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


elif page == "Trascrizione":
    _hero(
        "Trascrizione",
        "Trascrizione audio streaming con medwhisper-large-v3 italiano.",
    )

    st.markdown(
        '<div class="hc-note">Su CPU large-v3 è più lento del realtime. I segmenti compaiono progressivamente.</div>',
        unsafe_allow_html=True,
    )

    audio = st.audio_input("Registra audio")

    if audio is not None:
        run = st.button("Trascrivi", type="primary", use_container_width=False)
        if run:
            segments_acc: list[dict] = []
            placeholder = st.empty()
            full_text_holder = st.empty()
            status_holder = st.empty()

            status_holder.markdown(
                '<div class="hc-status online"><span class="dot"></span>Trascrizione in corso</div>',
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
                            f"Segmenti ({len(segments_acc)})</div>{segments_html}</div>",
                            unsafe_allow_html=True,
                        )
                        full_text_holder.text_area(
                            "Testo completo",
                            " ".join(s["text"].strip() for s in segments_acc),
                            height=160,
                        )
            except requests.RequestException as exc:
                status_holder.error(f"Errore API: {exc}")
            else:
                status_holder.success(
                    f"Trascrizione completata · {len(segments_acc)} segmenti"
                )
                if segments_acc:
                    st.download_button(
                        "Scarica trascrizione",
                        " ".join(s["text"].strip() for s in segments_acc),
                        file_name="transcript.txt",
                    )


elif page == "Trascrizione live":
    import streamlit.components.v1 as components

    _hero(
        "Trascrizione live",
        "WhisperLive con medwhisper-large-v3 italiano via WebSocket.",
    )

    st.markdown(
        '<div class="hc-note">Su CPU con large-v3 i parziali hanno qualche secondo di lag. Il primo avvio carica il modello (può richiedere alcuni minuti).</div>',
        unsafe_allow_html=True,
    )

    ws_url = os.getenv("WHISPERLIVE_URL", "ws://localhost:9090")
    model_name = "ReportAId/medwhisper-large-v3-ita-ct2"

    html = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 0; margin: 0; background: transparent; color: #1f2937; }
  .panel { background: #ffffff; border-radius: 6px; padding: 18px; border: 1px solid #e5e7eb; }
  .controls { display: flex; gap: 8px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
  button { padding: 6px 14px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid #d1d5db; border-radius: 5px; background: #ffffff; color: #374151; }
  button:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  button.primary { background: #1f2937; color: #ffffff; border-color: #1f2937; }
  button.primary:hover:not(:disabled) { background: #111827; border-color: #111827; }
  #status { display: inline-flex; align-items: center; gap: 6px; color: #6b7280; font-size: 12px; font-weight: 500; padding: 3px 10px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 4px; }
  #status .dot { width: 6px; height: 6px; border-radius: 50%; background: #9ca3af; }
  #status.active .dot { background: #6b7280; }
  #status.recording .dot { background: #dc2626; }
  #transcript { padding: 14px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 5px; min-height: 260px; max-height: 380px; overflow-y: auto; font-size: 13px; line-height: 1.6; }
  .segment { padding: 7px 11px; background: #ffffff; border: 1px solid #e5e7eb; border-left: 2px solid #6b7280; border-radius: 0 3px 3px 0; margin-bottom: 6px; }
  .segment .ts { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 10.5px; color: #6b7280; font-weight: 600; display: block; margin-bottom: 2px; }
  .empty { text-align: center; color: #9ca3af; padding: 60px 20px; font-size: 13px; }
</style>
</head>
<body>
<div class="panel">
  <div class="controls">
    <button id="start" class="primary">Avvia registrazione</button>
    <button id="stop" disabled>Ferma</button>
    <span id="status"><span class="dot"></span><span id="status-text">Pronto</span></span>
  </div>
  <div id="transcript">
    <div class="empty">Premi <b>Avvia registrazione</b> per iniziare.</div>
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
function setStatus(t, cls) { statusText.textContent = t; statusEl.className = cls || ""; }
function render() {
  if (segments.length === 0) { transcriptEl.innerHTML = '<div class="empty">In ascolto...</div>'; return; }
  transcriptEl.innerHTML = segments.map(s =>
    `<div class="segment"><span class="ts">[${(+s.start).toFixed(1)}s → ${(+s.end).toFixed(1)}s]</span>${s.text}</div>`
  ).join("");
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

startBtn.onclick = async () => {
  startBtn.disabled = true;
  segments = []; render();
  setStatus("Apro microfono...", "active");
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
    });
  } catch (e) { setStatus("Errore microfono: " + e.message, ""); startBtn.disabled = false; return; }

  audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
  source = audioCtx.createMediaStreamSource(stream);
  processor = audioCtx.createScriptProcessor(2048, 1, 1);
  source.connect(processor); processor.connect(audioCtx.destination);

  ws = new WebSocket(WS_URL); ws.binaryType = "arraybuffer";
  ws.onopen = () => {
    ws.send(JSON.stringify({
      uid: uid(), language: "it", task: "transcribe", model: MODEL_NAME,
      use_vad: true, same_output_threshold: 5, send_last_n_segments: 10,
      no_speech_thresh: 0.45,
      initial_prompt: "Visita medica in italiano clinico.",
      max_clients: 4, max_connection_time: 600
    }));
    setStatus("Caricamento modello...", "active"); stopBtn.disabled = false;
  };
  ws.onmessage = (ev) => {
    let msg; try { msg = JSON.parse(ev.data); } catch (e) { return; }
    if (msg.message === "SERVER_READY") setStatus("Registrazione attiva", "recording");
    else if (msg.message === "DISCONNECT") setStatus("Disconnesso", "");
    else if (msg.segments) { segments = msg.segments; render(); }
  };
  ws.onerror = () => setStatus("Errore WebSocket", "");
  ws.onclose = () => setStatus("Connessione chiusa", "");
  processor.onaudioprocess = (e) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(e.inputBuffer.getChannelData(0).buffer);
  };
};

stopBtn.onclick = () => {
  try { processor && processor.disconnect(); } catch (e) {}
  try { source && source.disconnect(); } catch (e) {}
  try { stream && stream.getTracks().forEach(t => t.stop()); } catch (e) {}
  try { audioCtx && audioCtx.close(); } catch (e) {}
  try { ws && ws.close(); } catch (e) {}
  startBtn.disabled = false; stopBtn.disabled = true; setStatus("Stop", "");
};
</script>
</body>
</html>
""".replace("__WS_URL__", ws_url).replace("__MODEL_NAME__", model_name)

    components.html(html, height=520, scrolling=False)


elif page == "Real-time STT + EHR":
    import streamlit.components.v1 as components

    _hero(
        "Real-time STT + EHR",
        "Trascrizione live + compilazione automatica dei questionari (loop debounce + LLM).",
    )

    st.markdown(
        '<div class="hc-note">Mentre parli, il sistema accumula la trascrizione e ogni ~3 secondi (debounce) la passa al LLM per aggiornare le proposte di compilazione. Nessun pulsante da premere durante la visita.</div>',
        unsafe_allow_html=True,
    )

    EHR_SPECIALTY_GLOSSARIES = {
        "Oculistica": "visus, acuità visiva, diottrie, miopia, ipermetropia, astigmatismo, presbiopia, cornea, cristallino, retina, macula, fovea, iride, pupilla, sclera, congiuntiva, coroide, nervo ottico, papilla, vitreo, camera anteriore, tonometria, pressione intraoculare, PIO, IOP, glaucoma, cataratta, retinopatia diabetica, maculopatia, degenerazione maculare, distacco di retina, FACO, IOL, LASIK, PRK, vitrectomia, blefarite, congiuntivite, uveite, cheratite, ambliopia, strabismo",
        "Cardiologia": "ECG, frequenza cardiaca, ritmo sinusale, fibrillazione atriale, ipertensione, infarto miocardico, angina, scompenso cardiaco, ecocardiogramma, frazione di eiezione, holter, pacemaker, troponina, BNP",
        "Generale": "anamnesi, sintomi, terapia in atto, diagnosi, esame obiettivo, prescrizione, dosaggio",
    }
    EHR_DEFAULT_QUESTIONNAIRES = {
        "Oculistica": [
            {"id": 1, "name": "Anamnesi", "fields": [
                {"name": "allergie", "description": "Allergie note"},
                {"name": "motivo_visita", "description": "Motivo principale della visita"},
                {"name": "terapia_preesistente", "description": "Terapie già in corso"},
            ], "existing_data": {}},
            {"id": 2, "name": "Esame Obiettivo Oculistico", "fields": [
                {"name": "cornea_od", "description": "Aspetto cornea OD"},
                {"name": "cristallino_od", "description": "Aspetto cristallino OD"},
                {"name": "sfera_od", "description": "Refrazione sferica OD (diottrie)", "type": "number"},
                {"name": "cilindro_od", "description": "Refrazione cilindrica OD (diottrie)", "type": "number"},
                {"name": "asse_od", "description": "Asse del cilindro OD (gradi)", "type": "number"},
                {"name": "pressione_oculare_od", "description": "Tono oculare OD (mmHg)", "type": "number"},
                {"name": "pressione_oculare_os", "description": "Tono oculare OS (mmHg)", "type": "number"},
            ], "existing_data": {}},
            {"id": 3, "name": "Diagnosi e Terapia", "fields": [
                {"name": "diagnosi", "description": "Diagnosi clinica (max 150 caratteri)"},
                {"name": "terapia", "description": "Terapia prescritta oggi"},
            ], "existing_data": {}},
        ],
        "Cardiologia": [
            {"id": 1, "name": "Anamnesi", "fields": [
                {"name": "motivo_visita", "description": "Motivo della visita"},
                {"name": "fattori_rischio", "description": "Fattori di rischio cardiovascolare (fumo, dislipidemia, diabete, familiarità)"},
                {"name": "terapia_in_atto", "description": "Terapie in corso"},
            ], "existing_data": {}},
            {"id": 2, "name": "Esame Obiettivo", "fields": [
                {"name": "pa_sistolica", "description": "PA sistolica (mmHg)", "type": "number"},
                {"name": "pa_diastolica", "description": "PA diastolica (mmHg)", "type": "number"},
                {"name": "fc", "description": "Frequenza cardiaca (bpm)", "type": "number"},
                {"name": "ritmo", "description": "Ritmo cardiaco"},
                {"name": "toni", "description": "Toni cardiaci"},
            ], "existing_data": {}},
            {"id": 3, "name": "Diagnosi e Terapia", "fields": [
                {"name": "diagnosi", "description": "Diagnosi"},
                {"name": "terapia", "description": "Terapia prescritta"},
            ], "existing_data": {}},
        ],
        "Generale": [
            {"id": 1, "name": "Anamnesi", "fields": [
                {"name": "allergie", "description": "Allergie note"},
                {"name": "motivo_visita", "description": "Motivo della visita"},
                {"name": "anamnesi_patologica", "description": "Patologie pregresse o in corso"},
                {"name": "terapia_in_atto", "description": "Farmaci attualmente assunti"},
            ], "existing_data": {}},
            {"id": 2, "name": "Diagnosi e Terapia", "fields": [
                {"name": "diagnosi", "description": "Diagnosi conclusiva"},
                {"name": "terapia", "description": "Terapia prescritta"},
            ], "existing_data": {}},
        ],
    }

    col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 1])
    with col_a:
        ehr_specialty = st.selectbox(
            "Specialità",
            list(EHR_DEFAULT_QUESTIONNAIRES.keys()),
            key="ehr_specialty",
        )
    with col_b:
        ehr_debounce_s = st.number_input(
            "Debounce LLM (s)",
            min_value=1.0, max_value=15.0, value=3.0, step=0.5,
            key="ehr_debounce",
            help="Quanto attendere dopo l'ultimo aggiornamento di trascrizione prima di chiamare l'LLM.",
        )
    with col_c:
        ehr_min_chars = st.number_input(
            "Soglia testo",
            min_value=10, max_value=500, value=30, step=5,
            key="ehr_min_chars",
            help="Sotto questa lunghezza non chiamo l'LLM (evita allucinazioni su saluti).",
        )
    with col_d:
        ehr_sensitivity = st.slider(
            "Sensibilità mic",
            min_value=1, max_value=5, value=2,
            key="ehr_sensitivity",
            help="1 = ignora rumori e silenzi (anti-allucinazione). 5 = cattura tutto.",
        )

    EHR_SENS_PARAMS = {
        1: {"rms": 0.020, "vad_threshold": 0.70, "no_speech": 0.85, "min_speech_ms": 500, "min_silence_ms": 800},
        2: {"rms": 0.012, "vad_threshold": 0.60, "no_speech": 0.75, "min_speech_ms": 350, "min_silence_ms": 600},
        3: {"rms": 0.008, "vad_threshold": 0.50, "no_speech": 0.60, "min_speech_ms": 250, "min_silence_ms": 400},
        4: {"rms": 0.004, "vad_threshold": 0.40, "no_speech": 0.50, "min_speech_ms": 200, "min_silence_ms": 300},
        5: {"rms": 0.000, "vad_threshold": 0.35, "no_speech": 0.40, "min_speech_ms": 150, "min_silence_ms": 200},
    }
    ehr_sens = EHR_SENS_PARAMS[ehr_sensitivity]

    ehr_context = st.text_area(
        "Glossario / contesto clinico",
        value=EHR_SPECIALTY_GLOSSARIES.get(ehr_specialty, ""),
        height=80,
        key=f"ehr_ctx_{ehr_specialty}",
    )

    ehr_schema_key = f"ehr_schema_{ehr_specialty}"
    if ehr_schema_key not in st.session_state:
        st.session_state[ehr_schema_key] = json.dumps(
            EHR_DEFAULT_QUESTIONNAIRES[ehr_specialty], indent=2, ensure_ascii=False
        )
    ehr_schema = st.text_area(
        "Schema questionari (JSON, modificabile)",
        key=ehr_schema_key,
        height=220,
    )

    api_url_for_browser = os.getenv("API_URL_BROWSER", os.getenv("API_URL", "http://localhost:8080"))
    ws_url = os.getenv("WHISPERLIVE_URL", "ws://localhost:9090")
    model_name = "ReportAId/medwhisper-large-v3-ita-ct2"

    # NB: il glossario NON va nell'initial_prompt di Whisper (causa hallucination
    # da "prompt leak" durante i silenzi). Va invece SOLO al LLM via CONTEXT.
    initial_prompt = f"Visita {ehr_specialty.lower()} in italiano."

    ehr_html = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 0; margin: 0; background: transparent; color: #1f2937; font-size: 13px; }
  .wrap { display: grid; grid-template-columns: 1fr 1.2fr; gap: 14px; }
  .card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 14px; }
  .controls { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
  button { padding: 6px 14px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid #d1d5db; border-radius: 5px; background: #ffffff; color: #374151; }
  button:hover:not(:disabled) { background: #f9fafb; }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  button.primary { background: #1f2937; color: #ffffff; border-color: #1f2937; }
  button.primary:hover:not(:disabled) { background: #111827; }
  button.mini { padding: 2px 8px; font-size: 12px; }
  button.ok { background: #ecfdf5; border-color: #6ee7b7; color: #065f46; }
  button.ok.active { background: #10b981; color: #ffffff; border-color: #10b981; }
  button.no { background: #fef2f2; border-color: #fca5a5; color: #991b1b; }
  button.no.active { background: #ef4444; color: #ffffff; border-color: #ef4444; }
  #status { display: inline-flex; align-items: center; gap: 6px; color: #6b7280; font-size: 12px; font-weight: 500; padding: 3px 10px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 4px; }
  #status .dot { width: 6px; height: 6px; border-radius: 50%; background: #9ca3af; }
  #status.active .dot { background: #6b7280; }
  #status.recording .dot { background: #dc2626; }
  #status.llm .dot { background: #2563eb; }
  #transcript { padding: 10px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 5px; min-height: 220px; max-height: 320px; overflow-y: auto; line-height: 1.55; }
  .seg { padding: 5px 8px; background: #ffffff; border: 1px solid #e5e7eb; border-left: 2px solid #6b7280; border-radius: 0 3px 3px 0; margin-bottom: 4px; }
  .seg .ts { font-family: ui-monospace, Menlo, monospace; font-size: 10px; color: #9ca3af; }
  .ehr-q { margin-bottom: 16px; }
  .ehr-q h4 { margin: 0 0 8px 0; font-size: 13px; color: #1f2937; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }
  .field-row { display: grid; grid-template-columns: 1fr 1fr auto auto; gap: 6px; align-items: center; padding: 5px 0; border-bottom: 1px dashed #f3f4f6; }
  .field-row .fname { font-family: ui-monospace, Menlo, monospace; font-size: 11.5px; color: #4b5563; }
  .field-row .fval { background: #f9fafb; padding: 4px 8px; border-radius: 3px; font-family: ui-monospace, Menlo, monospace; font-size: 11.5px; color: #111827; max-width: 100%; overflow-x: auto; }
  .field-row.accepted .fval { background: #ecfdf5; }
  .field-row.rejected .fval { background: #fef2f2; text-decoration: line-through; color: #6b7280; }
  .empty { text-align: center; color: #9ca3af; padding: 40px 20px; }
  .meta { font-size: 11px; color: #6b7280; margin-top: 6px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="controls">
      <button id="start" class="primary">Avvia</button>
      <button id="stop" disabled>Ferma</button>
      <span id="status"><span class="dot"></span><span id="status-text">Pronto</span></span>
    </div>
    <div id="transcript"><div class="empty">In attesa…</div></div>
    <div class="meta" id="meta"></div>
  </div>
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <strong>Proposte EHR</strong>
      <button id="download" class="mini" disabled>Scarica JSON accettati</button>
    </div>
    <div id="ehr"><div class="empty">Le proposte compaiono qui mentre parli.</div></div>
  </div>
</div>
<script>
const WS_URL = "__WS_URL__";
const API_URL = "__API_URL__";
const MODEL_NAME = "__MODEL_NAME__";
const INITIAL_PROMPT = __INITIAL_PROMPT_JSON__;
const QUESTIONNAIRES = __QUESTIONNAIRES_JSON__;
const CONTEXT = __CONTEXT_JSON__;
const DEBOUNCE_MS = __DEBOUNCE_MS__;
const MIN_CHARS = __MIN_CHARS__;
const SENS = __SENS_JSON__;

const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const downloadBtn = document.getElementById("download");
const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");
const transcriptEl = document.getElementById("transcript");
const ehrEl = document.getElementById("ehr");
const metaEl = document.getElementById("meta");

let ws = null, audioCtx = null, stream = null, source = null, processor = null;
let segments = [];                  // ultimi segmenti da WhisperLive
let fullTranscript = "";            // testo cumulativo
let hasNewData = false;
let llmRunning = false;
let debounceTimer = null;
let llmRuns = 0;
// proposalsState[qid][fieldName] = { value, status: 'pending'|'accepted'|'rejected' }
const proposalsState = new Map();
// nomi questionario id -> label
const qNameById = new Map();
QUESTIONNAIRES.forEach(q => qNameById.set(String(q.id), q.name));

function uid() { return Math.random().toString(36).slice(2) + Date.now().toString(36); }
function setStatus(t, cls) { statusText.textContent = t; statusEl.className = cls || ""; }

function renderTranscript() {
  if (segments.length === 0) { transcriptEl.innerHTML = '<div class="empty">In ascolto…</div>'; return; }
  transcriptEl.innerHTML = segments.map(s =>
    `<div class="seg"><span class="ts">[${(+s.start).toFixed(1)}s]</span> ${s.text}</div>`
  ).join("");
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function renderEHR() {
  if (proposalsState.size === 0) {
    ehrEl.innerHTML = '<div class="empty">Le proposte compaiono qui mentre parli.</div>';
    downloadBtn.disabled = true;
    return;
  }
  let html = "";
  for (const [qid, fields] of proposalsState.entries()) {
    const qname = qNameById.get(String(qid)) || ("Questionario " + qid);
    html += `<div class="ehr-q"><h4>${qname}</h4>`;
    for (const [fname, info] of fields.entries()) {
      const status = info.status || "pending";
      const valStr = typeof info.value === "string" ? info.value : JSON.stringify(info.value);
      html += `<div class="field-row ${status}">
        <div class="fname">${fname}</div>
        <div class="fval">${valStr}</div>
        <button class="mini ok ${status === 'accepted' ? 'active' : ''}" data-qid="${qid}" data-f="${fname}" data-act="accepted">✓</button>
        <button class="mini no ${status === 'rejected' ? 'active' : ''}" data-qid="${qid}" data-f="${fname}" data-act="rejected">✗</button>
      </div>`;
    }
    html += `</div>`;
  }
  ehrEl.innerHTML = html;
  ehrEl.querySelectorAll("button[data-qid]").forEach(btn => {
    btn.onclick = () => {
      const qid = btn.dataset.qid, f = btn.dataset.f, act = btn.dataset.act;
      const fields = proposalsState.get(qid);
      if (!fields) return;
      const info = fields.get(f);
      if (!info) return;
      info.status = (info.status === act) ? "pending" : act;
      renderEHR();
    };
  });
  downloadBtn.disabled = ![...proposalsState.values()].some(fs =>
    [...fs.values()].some(i => i.status === "accepted")
  );
}

function mergeProposals(newProps) {
  // newProps: { qid: { field: value } }
  for (const [qid, fields] of Object.entries(newProps || {})) {
    if (!proposalsState.has(qid)) proposalsState.set(qid, new Map());
    const cur = proposalsState.get(qid);
    for (const [fname, value] of Object.entries(fields)) {
      // valori vuoti: skip
      if (value === null || value === "" || value === "-" || value === "—") continue;
      if (Array.isArray(value) && value.length === 0) continue;
      const prev = cur.get(fname);
      if (prev) {
        // preservo lo stato utente; aggiorno solo il valore se è cambiato
        prev.value = value;
      } else {
        cur.set(fname, { value, status: "pending" });
      }
    }
  }
  renderEHR();
}

function scheduleLLM() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => maybeRunLLM(), DEBOUNCE_MS);
}

async function maybeRunLLM() {
  if (llmRunning) return;
  if (!hasNewData) return;
  if (fullTranscript.trim().length < MIN_CHARS) return;
  llmRunning = true;
  while (hasNewData) {
    hasNewData = false;
    const snapshot = fullTranscript;
    try {
      setStatus("LLM in elaborazione…", "llm");
      const t0 = performance.now();
      const r = await fetch(API_URL.replace(/\\/$/, "") + "/transcription/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: snapshot, questionnaires: QUESTIONNAIRES, context: CONTEXT })
      });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      mergeProposals(data.questionnaires || {});
      llmRuns += 1;
      const ms = (performance.now() - t0).toFixed(0);
      metaEl.textContent = `Run #${llmRuns} · ${ms} ms · transcript ${snapshot.length} char`;
      setStatus(ws && ws.readyState === WebSocket.OPEN ? "Registrazione attiva" : "Ferma", "recording");
    } catch (e) {
      setStatus("Errore LLM: " + e.message, "");
    }
  }
  llmRunning = false;
}

downloadBtn.onclick = () => {
  const accepted = {};
  for (const [qid, fields] of proposalsState.entries()) {
    const acc = {};
    for (const [fname, info] of fields.entries()) {
      if (info.status === "accepted") acc[fname] = info.value;
    }
    if (Object.keys(acc).length > 0) accepted[qid] = acc;
  }
  const blob = new Blob([JSON.stringify(accepted, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ehr_accettati.json";
  a.click();
};

startBtn.onclick = async () => {
  startBtn.disabled = true;
  segments = []; fullTranscript = ""; hasNewData = false;
  proposalsState.clear(); renderEHR(); renderTranscript();
  metaEl.textContent = "";

  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    setStatus("Contesto non sicuro (serve localhost o https)", "");
    startBtn.disabled = false;
    return;
  }
  setStatus("Apro microfono…", "active");
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true, sampleRate: 16000 }
    });
  } catch (e) { setStatus("Errore microfono: " + e.message, ""); startBtn.disabled = false; return; }

  audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000, latencyHint: "interactive" });
  source = audioCtx.createMediaStreamSource(stream);
  processor = audioCtx.createScriptProcessor(4096, 1, 1);
  source.connect(processor); processor.connect(audioCtx.destination);

  ws = new WebSocket(WS_URL); ws.binaryType = "arraybuffer";
  ws.onopen = () => {
    ws.send(JSON.stringify({
      uid: uid(), language: "it", task: "transcribe", model: MODEL_NAME,
      use_vad: true, same_output_threshold: 3, send_last_n_segments: 6,
      no_speech_thresh: SENS.no_speech,
      vad_parameters: {
        threshold: SENS.vad_threshold,
        min_speech_duration_ms: SENS.min_speech_ms,
        min_silence_duration_ms: SENS.min_silence_ms,
        speech_pad_ms: 200
      },
      initial_prompt: INITIAL_PROMPT,
      max_clients: 4, max_connection_time: 1800
    }));
    setStatus("Caricamento modello…", "active"); stopBtn.disabled = false;
  };
  ws.onmessage = (ev) => {
    let msg; try { msg = JSON.parse(ev.data); } catch (e) { return; }
    if (msg.message === "SERVER_READY") setStatus("Registrazione attiva", "recording");
    else if (msg.message === "DISCONNECT") setStatus("Disconnesso", "");
    else if (msg.segments) {
      segments = msg.segments;
      // ricostruisco fullTranscript dai segmenti (WhisperLive manda gli ultimi N segmenti completi)
      const joined = segments.map(s => (s.text || "").trim()).filter(Boolean).join(" ");
      if (joined !== fullTranscript) {
        fullTranscript = joined;
        hasNewData = true;
        renderTranscript();
        scheduleLLM();
      } else {
        renderTranscript();
      }
    }
  };
  ws.onerror = () => setStatus("Errore WebSocket", "");
  ws.onclose = () => setStatus("Connessione chiusa", "");
  processor.onaudioprocess = (e) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const data = e.inputBuffer.getChannelData(0);
    if (SENS.rms > 0) {
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
      const rms = Math.sqrt(sum / data.length);
      if (rms < SENS.rms) return;  // chunk troppo silenzioso → non inviare
    }
    ws.send(data.buffer);
  };
};

stopBtn.onclick = () => {
  try { processor && processor.disconnect(); } catch (e) {}
  try { source && source.disconnect(); } catch (e) {}
  try { stream && stream.getTracks().forEach(t => t.stop()); } catch (e) {}
  try { audioCtx && audioCtx.close(); } catch (e) {}
  try { ws && ws.close(); } catch (e) {}
  startBtn.disabled = false; stopBtn.disabled = true; setStatus("Stop", "");
  // run finale per recuperare l'ultimo testo
  hasNewData = true;
  scheduleLLM();
};
</script>
</body>
</html>
""".replace("__WS_URL__", ws_url) \
   .replace("__API_URL__", api_url_for_browser) \
   .replace("__MODEL_NAME__", model_name) \
   .replace("__INITIAL_PROMPT_JSON__", json.dumps(initial_prompt, ensure_ascii=False)) \
   .replace("__CONTEXT_JSON__", json.dumps(ehr_context, ensure_ascii=False)) \
   .replace("__DEBOUNCE_MS__", str(int(ehr_debounce_s * 1000))) \
   .replace("__MIN_CHARS__", str(int(ehr_min_chars))) \
   .replace("__SENS_JSON__", json.dumps(ehr_sens)) \
   .replace("__QUESTIONNAIRES_JSON__", st.session_state[ehr_schema_key])

    components.html(ehr_html, height=760, scrolling=True)

    st.caption(
        f"API LLM: `{api_url_for_browser}/transcription/extract` · "
        f"WhisperLive: `{ws_url}` · "
        f"Specialità: **{ehr_specialty}** · "
        f"Debounce: {ehr_debounce_s}s · Soglia: {ehr_min_chars} char"
    )


elif page == "Strutturazione FHIR":
    _hero(
        "Strutturazione FHIR",
        "Pipeline OCR → anonimizzazione → strutturazione FHIR R4 via LLM (gpt-oss-20b).",
    )

    uploaded = st.file_uploader(
        "Carica documento",
        type=["png", "jpg", "jpeg"],
        key="fhir_uploader",
    )

    col_l, col_r = st.columns([1, 1])

    if uploaded is not None:
        col_l.image(uploaded, use_container_width=True)

        if col_l.button("Struttura in FHIR", type="primary", key="fhir_btn"):
            image_b64 = base64.b64encode(uploaded.getvalue()).decode("utf-8")

            tabs = col_r.tabs(["FHIR", "OCR"])
            with tabs[0]:
                status_ph = st.empty()
                fhir_ph = st.empty()
                download_ph = st.empty()
            with tabs[1]:
                ocr_ph = st.empty()

            status_ph.info("OCR in corso…")
            ocr_text = ""
            fhir_raw = ""
            fhir_parsed = None

            try:
                with requests.post(
                    f"{API_URL}/fhir/document/stream",
                    json={"image_base64": image_b64},
                    timeout=TIMEOUT,
                    stream=True,
                ) as r:
                    r.raise_for_status()
                    for line in r.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        kind = event.get("event")
                        if kind == "ocr":
                            ocr_text = event.get("text", "")
                            ocr_ph.text_area(
                                "Testo OCR",
                                ocr_text,
                                height=320,
                                label_visibility="collapsed",
                                key="ocr_stream",
                            )
                            status_ph.info("LLM in streaming…")
                        elif kind == "fhir_delta":
                            fhir_raw += event.get("delta", "")
                            fhir_ph.code(fhir_raw, language="json")
                        elif kind == "fhir_done":
                            fhir_parsed = event.get("fhir")
                            fhir_raw = event.get("raw", fhir_raw)
                            if fhir_parsed is None:
                                status_ph.warning(
                                    "JSON non valido — mostro l'output grezzo."
                                )
                                fhir_ph.code(fhir_raw, language="text")
                            else:
                                status_ph.success("Bundle FHIR completato.")
                                fhir_ph.json(fhir_parsed, expanded=2)
                                download_ph.download_button(
                                    "Scarica Bundle JSON",
                                    data=json.dumps(
                                        fhir_parsed, indent=2, ensure_ascii=False
                                    ),
                                    file_name="fhir_bundle.json",
                                    mime="application/json",
                                )
                        elif kind == "error":
                            status_ph.error(
                                f"Errore pipeline: {event.get('detail', '')}"
                            )
            except requests.RequestException as exc:
                status_ph.error(f"Errore API: {exc}")


elif page == "Classificazione immagine":
    _hero(
        "Classificazione immagine",
        "Zero-shot classification con openai/clip-vit-base-patch32: medica vs non medica.",
    )

    uploaded = st.file_uploader(
        "Carica un'immagine",
        type=["png", "jpg", "jpeg"],
        key="clip_uploader",
    )

    with st.expander("Etichette personalizzate (opzionale)"):
        labels_raw = st.text_input(
            "Etichette separate da virgola",
            value="medical image, non-medical image",
            key="clip_labels",
        )

    if uploaded is not None:
        col_l, col_r = st.columns([1, 1], gap="large")

        with col_l:
            st.markdown('<div class="hc-card-title">Immagine</div>', unsafe_allow_html=True)
            st.image(uploaded, use_container_width=True)
            run = st.button("Classifica", type="primary", use_container_width=True, key="clip_btn")

        with col_r:
            if run:
                labels = [s.strip() for s in labels_raw.split(",") if s.strip()]
                payload: dict = {
                    "image_base64": base64.b64encode(uploaded.getvalue()).decode("utf-8"),
                }
                if labels:
                    payload["candidate_labels"] = labels

                with st.spinner("Classificazione in corso..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/image/classify",
                            json=payload,
                            timeout=TIMEOUT,
                        )
                        r.raise_for_status()
                        data = r.json()
                    except requests.RequestException as exc:
                        st.error(f"Errore API: {exc}")
                    else:
                        top = data["top_label"]
                        is_medical = data["is_medical"]
                        verdict_class = "online" if is_medical else "offline"
                        verdict_text = "Medica" if is_medical else "Non medica"
                        st.markdown(
                            f'<div class="hc-status {verdict_class}" style="font-size:0.85rem; padding:5px 12px;">'
                            f'<span class="dot"></span>{verdict_text}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div style="margin: 10px 0 16px 0; color:#6b7280; font-size:0.85rem;">'
                            f'Top label: <b style="color:#111827;">{top}</b></div>',
                            unsafe_allow_html=True,
                        )

                        st.dataframe(
                            data["scores"],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "label": st.column_config.TextColumn("Etichetta", width="large"),
                                "score": st.column_config.ProgressColumn(
                                    "Confidenza",
                                    format="%.3f",
                                    min_value=0.0,
                                    max_value=1.0,
                                ),
                            },
                        )
            else:
                st.markdown(
                    '<div class="hc-empty">Premi <b>Classifica</b> per eseguire la classificazione zero-shot.</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            '<div class="hc-empty">Nessuna immagine caricata. Carica un PNG o JPEG per iniziare.</div>',
            unsafe_allow_html=True,
        )


