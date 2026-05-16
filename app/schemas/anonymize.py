from pydantic import BaseModel, Field


class AnonymizeRequest(BaseModel):
    image_base64: str = Field(..., description="Document image encoded as base64 string")


class AnonymizeResponse(BaseModel):
    ocr_text: str
    anonymized_text: str
