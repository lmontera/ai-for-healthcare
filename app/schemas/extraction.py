from typing import Any

from pydantic import BaseModel, Field


class FieldOption(BaseModel):
    label: str
    value: str | int | float | bool


class QuestionnaireField(BaseModel):
    name: str
    description: str
    type: str | None = Field(
        default=None,
        description="Es. text, number, select, multiselect, boolean",
    )
    options: list[FieldOption] | None = None


class Questionnaire(BaseModel):
    id: int | str
    name: str
    fields: list[QuestionnaireField]
    existing_data: dict[str, Any] = Field(default_factory=dict)


class ExtractionRequest(BaseModel):
    transcript: str = Field(..., description="Trascrizione cumulativa")
    questionnaires: list[Questionnaire]
    context: str | None = Field(default=None, description="Contesto clinico / specialità")
    max_new_tokens: int = Field(default=2048, ge=64, le=8192)


class ExtractionResponse(BaseModel):
    questionnaires: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Mappa questionnaireId -> { fieldName -> value }",
    )
    raw: str
