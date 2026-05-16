import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def has_cuda() -> bool:
    try:
        import torch

        available = torch.cuda.is_available()
        if available:
            name = torch.cuda.get_device_name(0)
            logger.info("[device] CUDA available: %s", name)
        else:
            logger.warning("[device] CUDA NOT available — falling back to CPU")
        return available
    except Exception as exc:
        logger.warning("[device] CUDA check failed (%s) — falling back to CPU", exc)
        return False


def torch_device() -> str:
    return "cuda" if has_cuda() else "cpu"


def whisper_compute_type() -> str:
    return "float16" if has_cuda() else "int8"


def pipeline_device() -> int:
    return 0 if has_cuda() else -1
