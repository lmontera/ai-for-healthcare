import logging
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_started = False


def start_whisperlive_background(host: str = "0.0.0.0", port: int = 9090) -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True

    thread = threading.Thread(
        target=_run,
        args=(host, port),
        daemon=True,
        name="whisperlive",
    )
    thread.start()


def _run(host: str, port: int) -> None:
    from whisper_live.server import TranscriptionServer

    logger.info("[whisperlive] starting server on %s:%d (single_model=True)", host, port)
    try:
        server = TranscriptionServer()
        server.run(host, port=port, backend="faster_whisper", single_model=True)
    except Exception:
        logger.exception("[whisperlive] server crashed")
