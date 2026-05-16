from typing import Protocol, runtime_checkable

from app.schemas.pii import PIIEntity


@runtime_checkable
class PIIDetectionService(Protocol):
    def detect(self, text: str) -> list[PIIEntity]: ...
