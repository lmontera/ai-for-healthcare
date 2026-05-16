import base64
import json
import os

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


def _color(label: str) -> str:
    return ENTITY_COLORS.get(label.lower(), "#e5e7eb")


def _highlight(text: str, entities: list[dict]) -> str:
    spans = sorted(entities, key=lambda e: e["start"], reverse=True)
    rendered = text
    for ent in spans:
        start, end = ent["start"], ent["end"]
        color = _color(ent["label"])
        chunk = rendered[start:end]
        replacement = (
            f'<mark style="background-color:{color};padding:2px 4px;border-radius:4px;">'
            f'{chunk}<sub style="margin-left:4px;font-size:0.7em;opacity:0.7;">'
            f'{ent["label"]}</sub></mark>'
        )
        rendered = f"{rendered[:start]}{replacement}{rendered[end:]}"
    return rendered.replace("\n", "<br/>")


def _check_health() -> tuple[bool, str]:
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        return r.ok, r.text
    except requests.RequestException as e:
        return False, str(e)


st.set_page_config(page_title="AI for Healthcare", page_icon="🩺", layout="wide")

st.sidebar.title("AI for Healthcare")
ok, info = _check_health()
st.sidebar.markdown(f"**API**: `{API_URL}`")
st.sidebar.markdown(f"**Status**: {'🟢 online' if ok else '🔴 offline'}")
if not ok:
    st.sidebar.caption(info)

page = st.sidebar.radio(
    "Servizio",
    ["Anonymize Document", "PII Detect", "Transcription", "Realtime STT"],
    index=0,
)


if page == "Anonymize Document":
    st.title("Anonymize Document")
    st.caption("Upload di un'immagine → OCR (docTR) → anonimizzazione (openai/privacy-filter)")

    uploaded = st.file_uploader("Documento", type=["png", "jpg", "jpeg"])
    col1, col2 = st.columns([1, 1])

    if uploaded is not None:
        col1.image(uploaded, use_container_width=True)

    if uploaded is not None and col1.button("Esegui", type="primary"):
        image_b64 = base64.b64encode(uploaded.getvalue()).decode("utf-8")
        with st.spinner("Elaborazione in corso..."):
            try:
                r = requests.post(
                    f"{API_URL}/anonymize",
                    json={"image_base64": image_b64},
                    timeout=TIMEOUT,
                )
                r.raise_for_status()
                data = r.json()
            except requests.RequestException as exc:
                col2.error(f"Errore API: {exc}")
            else:
                col2.subheader("OCR")
                col2.text_area("Testo estratto", data["ocr_text"], height=240)
                col2.subheader("Anonimizzato")
                col2.text_area("Testo anonimizzato", data["anonymized_text"], height=240)


elif page == "PII Detect":
    st.title("PII Detect")
    st.caption("Testo libero → entità PII rilevate (OpenMed Italian medical model)")

    text = st.text_area(
        "Testo",
        height=200,
        placeholder="Paziente Marco Bianchi nato il 15/03/1985, email marco.bianchi@email.it...",
    )

    if st.button("Analizza", type="primary", disabled=not text.strip()):
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
                st.subheader(f"Entità rilevate ({len(entities)})")
                st.markdown(_highlight(text, entities), unsafe_allow_html=True)

                if entities:
                    st.subheader("Dettaglio")
                    st.dataframe(
                        entities,
                        use_container_width=True,
                        column_config={
                            "label": "Tipo",
                            "text": "Testo",
                            "start": "Inizio",
                            "end": "Fine",
                            "score": st.column_config.NumberColumn("Score", format="%.3f"),
                        },
                    )


elif page == "Transcription":
    st.title("Transcription")
    st.caption("Registra audio → trascrizione (medwhisper-large-v3 italiano)")
    st.info(
        "Su CPU large-v3 va più lento del realtime: i segmenti compaiono progressivamente "
        "man mano che il modello li produce, dopo aver premuto Trascrivi."
    )

    audio = st.audio_input("Registra")
    if audio is not None and st.button("Trascrivi", type="primary"):
        placeholder = st.empty()
        full_text = st.empty()
        segments_acc: list[dict] = []
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
                    placeholder.markdown(
                        "\n\n".join(
                            f"`[{s['start']:.1f}s → {s['end']:.1f}s]` {s['text']}"
                            for s in segments_acc
                        )
                    )
                    full_text.text_area(
                        "Testo completo",
                        " ".join(s["text"].strip() for s in segments_acc),
                        height=160,
                    )
        except requests.RequestException as exc:
            st.error(f"Errore API: {exc}")


elif page == "Realtime STT":
    import streamlit.components.v1 as components

    st.title("Realtime STT")
    st.caption("WhisperLive + medwhisper-large-v3 italiano — il browser parla direttamente al server :9090")
    st.warning(
        "Su CPU con large-v3 i parziali hanno qualche secondo di lag. "
        "Il primo avvio carica il modello (può richiedere alcuni minuti)."
    )

    ws_url = os.getenv("WHISPERLIVE_URL", "ws://localhost:9090")
    model_name = "ReportAId/medwhisper-large-v3-ita-ct2"

    html = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 0; margin: 0; }
  .row { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
  button { padding: 10px 16px; font-size: 14px; cursor: pointer; border: 1px solid #ccc; border-radius: 6px; background: #fff; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.primary { background: #ff4b4b; color: #fff; border-color: #ff4b4b; }
  #status { color: #555; font-size: 13px; }
  #transcript { padding: 12px; background: #f5f5f5; border-radius: 6px; min-height: 220px; white-space: pre-wrap; font-family: ui-monospace, monospace; font-size: 13px; }
</style>
</head>
<body>
<div class="row">
  <button id="start" class="primary">● Start</button>
  <button id="stop" disabled>■ Stop</button>
  <span id="status">Pronto.</span>
</div>
<div id="transcript"></div>
<script>
const WS_URL = "__WS_URL__";
const MODEL_NAME = "__MODEL_NAME__";

const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const statusEl = document.getElementById("status");
const transcriptEl = document.getElementById("transcript");

let ws = null, audioCtx = null, stream = null, source = null, processor = null;
let segments = [];

function uid() { return Math.random().toString(36).slice(2) + Date.now().toString(36); }
function setStatus(t) { statusEl.textContent = t; }
function render() {
  transcriptEl.textContent = segments
    .map(s => `[${(+s.start).toFixed(1)}s → ${(+s.end).toFixed(1)}s] ${s.text}`)
    .join("\\n");
}

startBtn.onclick = async () => {
  startBtn.disabled = true;
  segments = [];
  render();
  setStatus("Apro microfono...");
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
    });
  } catch (e) {
    setStatus("Errore microfono: " + e.message);
    startBtn.disabled = false;
    return;
  }

  audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
  source = audioCtx.createMediaStreamSource(stream);
  processor = audioCtx.createScriptProcessor(4096, 1, 1);
  source.connect(processor);
  processor.connect(audioCtx.destination);

  setStatus("Connessione WS a " + WS_URL + "...");
  ws = new WebSocket(WS_URL);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    const config = {
      uid: uid(),
      language: "it",
      task: "transcribe",
      model: MODEL_NAME,
      use_vad: true,
      max_clients: 4,
      max_connection_time: 600
    };
    ws.send(JSON.stringify(config));
    setStatus("Caricamento modello sul server (può richiedere minuti)...");
    stopBtn.disabled = false;
  };

  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch (e) { return; }
    if (msg.message === "SERVER_READY") {
      setStatus("● Pronto. Parla in italiano.");
    } else if (msg.message === "DISCONNECT") {
      setStatus("Disconnesso dal server.");
    } else if (msg.segments) {
      segments = msg.segments;
      render();
    }
  };

  ws.onerror = () => setStatus("Errore WebSocket");
  ws.onclose = () => setStatus("Connessione chiusa");

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
  setStatus("Stop.");
};
</script>
</body>
</html>
""".replace("__WS_URL__", ws_url).replace("__MODEL_NAME__", model_name)

    components.html(html, height=420, scrolling=False)
