from typing import Protocol, runtime_checkable


@runtime_checkable
class ImageClassificationService(Protocol):
    def classify(
        self, image_bytes: bytes, candidate_labels: list[str]
    ) -> list[dict]: ...
