from pydantic import BaseModel
from typing import Optional


class ExtractedRequirement(BaseModel):
    requirement_type: str
    description: str
    required_value: Optional[str] = None
    mandatory: bool
    source_page: int
    evidence_text: str