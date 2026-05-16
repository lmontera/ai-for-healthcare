from functools import lru_cache


@lru_cache(maxsize=1)
def has_cuda() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


def torch_device() -> str:
    return "cuda" if has_cuda() else "cpu"


def whisper_compute_type() -> str:
    return "float16" if has_cuda() else "int8"


def pipeline_device() -> int:
    return 0 if has_cuda() else -1
