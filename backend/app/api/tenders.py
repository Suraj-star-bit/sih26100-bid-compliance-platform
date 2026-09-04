from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
import pymupdf
import os

from app.db.database import get_db
from app.models.tender import Tender

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

    extracted_text = ""

    for page in pdf:
        extracted_text += page.get_text()

    pdf.close()

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