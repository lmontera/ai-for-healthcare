from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from app.schemas.transcription import TranscriptionSegment


@runtime_checkable
class TranscriptionService(Protocol):
    def transcribe(self, audio_bytes: bytes) -> Iterator[TranscriptionSegment]: ...
