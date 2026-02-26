import os
import uuid
import traceback
import json
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from crewai import Crew, Process

from agents import financial_analyst
from task import analyze_financial_document_task
from tools import get_search_tool, read_pdf_text

DEFAULT_QUERY = "Analyze this financial document for investment insights."
MAX_DOCUMENT_CHARS = int(os.getenv("MAX_DOCUMENT_CHARS", "12000"))
ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH", "error.log")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")


@asynccontextmanager
async def lifespan(app: FastAPI):
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

        return {
            "status": "success",
            "query": query,
            "analysis": analysis_text,
            "file_processed": file.filename,
            "saved_output_file": output_file,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
