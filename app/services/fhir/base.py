from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FHIRStructuringService(Protocol):
    def structure(self, text: str) -> tuple[dict[str, Any] | None, str]: ...
