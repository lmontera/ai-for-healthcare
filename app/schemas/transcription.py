from pydantic import BaseModel


class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str
