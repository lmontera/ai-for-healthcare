from typing import Protocol, runtime_checkable


@runtime_checkable
class AnonymizationService(Protocol):
    def anonymize(self, text: str) -> str: ...
