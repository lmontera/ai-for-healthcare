import logging
import time
from collections.abc import Iterator
from io import BytesIO

from faster_whisper import WhisperModel

from app.schemas.transcription import TranscriptionSegment
from app.services.transcription.base import TranscriptionService

logger = logging.getLogger(__name__)

_MODEL_NAME = "ReportAId/medwhisper-large-v3-ita-ct2"


class FasterWhisperTranscriptionService(TranscriptionService):
    def __init__(
        self,
        model_name: str = _MODEL_NAME,
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        logger.info(
            "[whisper] loading model name=%s device=%s compute_type=%s",
            model_name,
            device,
            compute_type,
        )
        t0 = time.perf_counter()
        self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
        logger.info("[whisper] model loaded in %.2fs", time.perf_counter() - t0)

    def transcribe(self, audio_bytes: bytes) -> Iterator[TranscriptionSegment]:
        logger.info("[whisper] transcribe start: audio_bytes=%d", len(audio_bytes))
        t0 = time.perf_counter()
        segments, info = self._model.transcribe(BytesIO(audio_bytes))
        logger.info(
            "[whisper] decode started: lang=%s prob=%.2f duration=%.2fs",
            getattr(info, "language", "?"),
            getattr(info, "language_probability", 0.0),
            getattr(info, "duration", 0.0),
        )

        count = 0
        for s in segments:
            count += 1
            logger.info(
                "[whisper] segment #%d [%.2fs -> %.2fs] %s",
                count,
                s.start,
                s.end,
                s.text.strip(),
            )
            yield TranscriptionSegment(
                start=float(s.start),
                end=float(s.end),
                text=s.text,
            )

        logger.info(
            "[whisper] transcribe done: segments=%d elapsed=%.2fs",
            count,
            time.perf_counter() - t0,
        )
