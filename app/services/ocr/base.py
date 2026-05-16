from typing import Protocol, runtime_checkable


@runtime_checkable
class OCRService(Protocol):
    def extract_text(self, image_bytes: bytes) -> str: ...
