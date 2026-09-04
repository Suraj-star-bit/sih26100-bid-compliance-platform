from fastapi import FastAPI
from sqlalchemy import text

from app.db.database import Base, engine
from app.models import (
    Tender,
    Requirement,
    Bidder,
    Document,
    ExtractedEvidence,
    ComplianceResult,
)

from app.api.tenders import router as tender_router


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="SIH26100 Bid Compliance Platform",
    version="0.1.0"
)


app.include_router(tender_router)


@app.get("/")
def root():
    return {
        "message": "SIH26100 Bid Compliance Platform API"
    }


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }