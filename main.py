import os
import uuid
import traceback
import json
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from crewai import Crew, Process

from agents import financial_analyst
from database import AnalysisResult, User, get_db, get_db_error, init_db, is_db_available
from task import analyze_financial_document_task
from tools import get_search_tool, read_pdf_text

DEFAULT_QUERY = "Analyze this financial document for investment insights."
MAX_DOCUMENT_CHARS = int(os.getenv("MAX_DOCUMENT_CHARS", "12000"))
ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH", "error.log")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
STRICT_DB_STARTUP = os.getenv("STRICT_DB_STARTUP", "false").lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_initialized = init_db()
    if not db_initialized:
        db_error = get_db_error() or "Unknown database initialization error."
        print(f"Database disabled: {db_error}")
        if STRICT_DB_STARTUP:
            raise RuntimeError(f"Database initialization failed: {db_error}")
    # Trigger optional tool load once to surface compatibility warning early.
    get_search_tool()
    yield


app = FastAPI(title="Financial Document Analyzer", lifespan=lifespan)


def _run_crew(query: str, file_name: str, document_text: str):
    context_limits = []
    for limit in (MAX_DOCUMENT_CHARS, 6000, 3000):
        if limit > 0 and limit not in context_limits:
            context_limits.append(limit)

    last_error = None
    for limit in context_limits:
        try:
            crew = Crew(
                agents=[financial_analyst],
                tasks=[analyze_financial_document_task],
                process=Process.sequential,
                verbose=True,
            )
            return crew.kickoff(
                inputs={
                    "query": query,
                    "file_name": file_name,
                    "document_text": _trim_document_text(document_text, limit),
                }
            )
        except Exception as exc:
            last_error = exc

    raise last_error


def _trim_document_text(document_text: str, max_chars: int) -> str:
    if len(document_text) <= max_chars:
        return document_text

    # Keep both early and late sections to preserve summary + statement details.
    head_len = int(max_chars * 0.7)
    tail_len = max_chars - head_len
    return (
        document_text[:head_len]
        + "\n\n[...document truncated for model context limit...]\n\n"
        + document_text[-tail_len:]
    )


def _save_analysis_output(query: str, file_name: str, analysis: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"analysis_{timestamp}_{uuid.uuid4().hex[:8]}.json")
    payload = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "source_file": file_name,
        "query": query,
        "analysis": analysis,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return output_file


@app.get("/")
async def root():
    return {"message": "Financial Document Analyzer API is running"}


@app.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    query: str = Form(default=DEFAULT_QUERY),
    user_name: str = Form(default="Anonymous"),
    user_email: Optional[str] = Form(default=None),
    db: Optional[Session] = Depends(get_db),
):
    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"

    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="File name is missing.")

        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

        query = (query or DEFAULT_QUERY).strip() or DEFAULT_QUERY

        os.makedirs("data", exist_ok=True)
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        with open(file_path, "wb") as f:
            f.write(content)

        document_text = read_pdf_text(file_path)
        result = _run_crew(query=query, file_name=file.filename, document_text=document_text)
        analysis_text = str(result)
        output_file = _save_analysis_output(
            query=query,
            file_name=file.filename,
            analysis=analysis_text,
        )
        normalized_email = (user_email or "").strip().lower() or None
        normalized_name = (user_name or "").strip() or "Anonymous"
        analysis_record_id = None
        db_warning = None

        if db is not None and is_db_available():
            try:
                user = None
                if normalized_email:
                    user = db.query(User).filter(User.email == normalized_email).first()
                    if user is None:
                        user = User(name=normalized_name, email=normalized_email)
                        db.add(user)
                        db.flush()
                    elif normalized_name and user.name != normalized_name:
                        user.name = normalized_name
                elif normalized_name != "Anonymous":
                    user = User(name=normalized_name, email=None)
                    db.add(user)
                    db.flush()

                analysis_record = AnalysisResult(
                    user_id=user.id if user else None,
                    query=query,
                    source_file=file.filename,
                    analysis=analysis_text,
                    output_file=output_file,
                )
                db.add(analysis_record)
                db.commit()
                analysis_record_id = str(analysis_record.id)
            except SQLAlchemyError:
                db.rollback()
                db_warning = "Analysis completed, but database save failed. Check error.log."
                with open(ERROR_LOG_PATH, "a", encoding="utf-8") as log_file:
                    log_file.write(f"\n--- {uuid.uuid4()} ---\n")
                    log_file.write(traceback.format_exc())
        else:
            db_warning = "Analysis completed, but database is unavailable. Check DATABASE_URL."

        return {
            "status": "success",
            "query": query,
            "analysis": analysis_text,
            "file_processed": file.filename,
            "saved_output_file": output_file,
            "user": {
                "name": normalized_name,
                "email": normalized_email,
            },
            "analysis_record_id": analysis_record_id,
            "db_warning": db_warning,
        }
    except HTTPException:
        raise
    except Exception as exc:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(f"\n--- {uuid.uuid4()} ---\n")
            log_file.write(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error processing financial document: {exc}. Check {ERROR_LOG_PATH} for full traceback.",
        ) from exc
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


@app.get("/users")
async def list_users(limit: int = 50, db: Optional[Session] = Depends(get_db)):
    if db is None or not is_db_available():
        raise HTTPException(status_code=503, detail="Database is unavailable. Check DATABASE_URL.")

    users = db.query(User).order_by(User.created_at.desc()).limit(max(1, min(limit, 500))).all()
    return [
        {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
        for user in users
    ]


@app.get("/analyses")
async def list_analyses(limit: int = 50, db: Optional[Session] = Depends(get_db)):
    if db is None or not is_db_available():
        raise HTTPException(status_code=503, detail="Database is unavailable. Check DATABASE_URL.")

    records = (
        db.query(AnalysisResult)
        .order_by(AnalysisResult.created_at.desc())
        .limit(max(1, min(limit, 500)))
        .all()
    )
    return [
        {
            "id": str(record.id),
            "user_id": str(record.user_id) if record.user_id else None,
            "query": record.query,
            "source_file": record.source_file,
            "output_file": record.output_file,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        for record in records
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
