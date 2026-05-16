from app.services.anonymization.base import AnonymizationService


class StubAnonymizationService(AnonymizationService):
    def anonymize(self, text: str) -> str:
        return f"[stub-anon] {text}"
