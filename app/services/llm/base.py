from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMService(Protocol):
    def chat(self, messages: list[dict], max_new_tokens: int = 1024) -> str: ...
