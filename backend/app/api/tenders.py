import pymupdf

from fastapi import APIRouter, Depends, Form, File, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.tender import Tender
from app.models.requirement import Requirement
from app.services.ai_requirement_extractor import extract_requirements_with_ai
from app.services.ocr_service import extract_text_with_ocr

router = APIRouter(prefix="/tenders", tags=["Tenders"])


@router.post("/upload")
async def upload_tender(
    title: str = Form(...),
    tender_number: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    os.makedirs("uploads/tenders", exist_ok=True)

    file_path = f"uploads/tenders/{file.filename}"

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    pdf = pymupdf.open(file_path)

    pages = []

    for page_number, page in enumerate(pdf, start=1):
        pages.append({
            "page_number": page_number,
            "text": page.get_text()
        })

    pdf.close()

    extracted_text = "\n".join(
        page["text"] for page in pages
    )

    tender = Tender(
    title=title,
    tender_number=tender_number,
    description=extracted_text,
    file_path=file_path
)

    db.add(tender)
    db.commit()
    db.refresh(tender)

    return {
        "id": tender.id,
        "title": tender.title,
        "tender_number": tender.tender_number,
        "message": "Tender uploaded and text extracted successfully"
    }

@router.post("/{tender_id}/extract-requirements")
def extract_tender_requirements(
    tender_id: int,
    db: Session = Depends(get_db)
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()

    if not tender:
        return {
            "error": "Tender not found"
        }

    pdf = pymupdf.open(tender.file_path)

    pages = []

    for page_number, page in enumerate(pdf[:10], start=1):
        text = page.get_text().strip()

        if not text:
            text = extract_text_with_ocr(page)

        if not text:
            print(f"Skipping empty page {page_number}")
            continue

        pages.append({
            "page_number": page_number,
            "text": text
        })
    pdf.close()

    requirements = extract_requirements_with_ai(pages)

    saved_requirements = []

    for requirement in requirements:
        requirement = requirement.model_dump()
        existing = db.query(Requirement).filter(
            Requirement.tender_id == tender.id,
            Requirement.requirement_type == requirement["requirement_type"],
            Requirement.description == requirement["description"],
            Requirement.source_page == requirement["source_page"]
        ).first()

        if existing:
            continue

        new_requirement = Requirement(
            tender_id=tender.id,
            requirement_type=requirement["requirement_type"],
            description=requirement["description"],
            required_value=requirement["required_value"],
            mandatory=requirement["mandatory"],
            source_page=requirement["source_page"],
            evidence_text=requirement["evidence_text"]
        )

        db.add(new_requirement)
        saved_requirements.append(new_requirement)

    db.commit()

    return {
        "tender_id": tender.id,
        "requirements_found": len(saved_requirements),
        "requirements": requirements
    }