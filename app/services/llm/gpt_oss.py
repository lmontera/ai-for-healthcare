import logging
import time

from transformers import pipeline

from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

_MODEL_NAME = "openai/gpt-oss-20b"


class GPTOSS20BService(LLMService):
    def __init__(self, model_name: str = _MODEL_NAME) -> None:
        logger.info("[llm] loading model name=%s", model_name)
        t0 = time.perf_counter()
        self._pipeline = pipeline(
            "text-generation",
            model=model_name,
            torch_dtype="auto",
            device_map="auto",
        )
        logger.info("[llm] model loaded in %.2fs", time.perf_counter() - t0)

    def chat(self, messages: list[dict], max_new_tokens: int = 1024) -> str:
        outputs = self._pipeline(messages, max_new_tokens=max_new_tokens)
        generated = outputs[0]["generated_text"]
        if isinstance(generated, list):
            return generated[-1].get("content", "")
        return str(generated)
