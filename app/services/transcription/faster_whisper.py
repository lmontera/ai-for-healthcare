import logging
import time
from collections.abc import Iterator
from datetime import datetime
from io import BytesIO

from faster_whisper import WhisperModel

from app.core.device import torch_device, whisper_compute_type
from app.schemas.transcription import TranscriptionSegment
from app.services.transcription.base import TranscriptionService

logger = logging.getLogger(__name__)

_MODEL_NAME = "ReportAId/medwhisper-large-v3-ita-ct2"


class FasterWhisperTranscriptionService(TranscriptionService):
    def __init__(
        self,
        model_name: str = _MODEL_NAME,
        device: str | None = None,
        compute_type: str | None = None,
    ) -> None:
        self._device = device or torch_device()
        compute_type = compute_type or whisper_compute_type()
        logger.info("[whisper] device=%s", self._device.upper())
        self._model = WhisperModel(model_name, device=self._device, compute_type=compute_type)

    def transcribe(self, audio_bytes: bytes) -> Iterator[TranscriptionSegment]:
        start_dt = datetime.now()
        t0 = time.perf_counter()
        logger.info("[whisper] start=%s device=%s", start_dt.strftime("%H:%M:%S"), self._device.upper())

        segments, _info = self._model.transcribe(BytesIO(audio_bytes), language="it")

        results: list[TranscriptionSegment] = []
        for s in segments:
            seg = TranscriptionSegment(start=float(s.start), end=float(s.end), text=s.text)
            results.append(seg)
            yield seg

        finish_dt = datetime.now()
        logger.info(
            "[whisper] finish=%s elapsed=%.2fs",
            finish_dt.strftime("%H:%M:%S"),
            time.perf_counter() - t0,
        )
