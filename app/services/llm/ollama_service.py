import json
import logging
import urllib.error
import urllib.request
from collections.abc import Iterator

from app.core.settings import settings
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class OllamaLLMService(LLMService):
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        keep_alive: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._host = (host or settings.ollama_host).rstrip("/")
        self._model = model or settings.ollama_model
        self._keep_alive = keep_alive or settings.ollama_keep_alive
        self._timeout = timeout if timeout is not None else settings.ollama_timeout
        logger.info(
            "[llm] ollama service host=%s model=%s keep_alive=%s",
            self._host,
            self._model,
            self._keep_alive,
        )

    def chat(
        self,
        messages: list[dict],
        max_new_tokens: int = 1024,
        json_mode: bool = False,
        think: bool = True,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "keep_alive": self._keep_alive,
            "options": {
                "num_predict": max_new_tokens,
                "temperature": 0,
            },
        }
        if json_mode:
            payload["format"] = "json"
        if not think:
            payload["think"] = False
        url = f"{self._host}/api/chat"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error("[llm] ollama HTTP %s: %s", e.code, err_body)
            raise
        except urllib.error.URLError as e:
            logger.error("[llm] ollama unreachable at %s: %s", url, e)
            raise

        parsed = json.loads(body)
        return parsed.get("message", {}).get("content", "")

    def chat_stream(
        self,
        messages: list[dict],
        max_new_tokens: int = 1024,
        json_mode: bool = True,
        think: bool = True,
    ) -> Iterator[str]:
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "keep_alive": self._keep_alive,
            "options": {
                "num_predict": max_new_tokens,
                "temperature": 0,
            },
        }
        if json_mode:
            payload["format"] = "json"
        if not think:
            payload["think"] = False
        url = f"{self._host}/api/chat"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            for line in resp:
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                delta = obj.get("message", {}).get("content", "")
                if delta:
                    yield delta
                if obj.get("done"):
                    break
