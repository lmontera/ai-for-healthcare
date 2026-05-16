import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import anonymize, pii, transcribe
from app.whisperlive_server import start_whisperlive_background

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_whisperlive_background()
    yield


app = FastAPI(title="AI for Healthcare", version="0.1.0", lifespan=lifespan)

app.include_router(anonymize.router)
app.include_router(pii.router)
app.include_router(transcribe.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
