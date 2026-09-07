from pydantic import BaseModel, Field
from typing import Optional


class ExtractedRequirement(BaseModel):
    requirement_type: str

    description: str

    required_value: Optional[str] = None

    mandatory: bool

    source_page: int

    source_section: Optional[str] = None

    evidence_text: str

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
