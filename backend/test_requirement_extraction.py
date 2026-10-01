from app.services.ai_requirement_extractor import (
    extract_requirements_with_ai
)
from app.services.ai_requirement_extractor import (
    extract_requirements_with_ai
)

from app.db.database import SessionLocal


pages = [
    {
        "page_number": 1,
        "text": """
        The bidder must have an annual turnover of Rs. 10 Crore.

        The bidder must possess a valid GST registration.

        The bidder must submit PAN details.

        OEM authorization certificate is mandatory.
        """
    }
]


db = SessionLocal()

requirements = extract_requirements_with_ai(
    pages,
    1,
    db
)

for requirement in requirements:

    print({
        "requirement_type": requirement.requirement_type,
        "description": requirement.description,
        "required_value": requirement.required_value,
        "mandatory": requirement.mandatory,
        "source_page": requirement.source_page,
    })