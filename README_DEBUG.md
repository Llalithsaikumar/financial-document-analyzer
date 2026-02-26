# Financial Document Analyzer - Debug Notes

## Bugs Found and Fixes Applied

1. Undefined LLM variable in `agents.py`
- Bug: `llm = llm` caused immediate runtime failure.
- Fix: Implemented `_build_llm()` and explicit provider-based `LLM(...)` construction.

2. Invalid PDF loader usage in `tools.py`
- Bug: `Pdf(...)` was referenced but never imported/defined.
- Fix: Replaced with `pypdf.PdfReader` and robust text extraction via `read_pdf_text(path)`.

3. Hard import crash from `crewai-tools`
- Bug: Eager `SerperDevTool` import failed due to `crewai`/`crewai-tools` incompatibility (`No module named crewai.rag`).
- Fix: Added lazy optional loader `get_search_tool()` with non-fatal warning; app boots without search tool.

4. Wrong/unsafe prompt design
- Bug: Prompts encouraged hallucinations, fake URLs, contradictions, and unsafe advice.
- Fix: Rewrote agent/task prompts to be evidence-based, structured, and non-fabricated.

5. Task/API naming collision
- Bug: Endpoint function and task object used conflicting names.
- Fix: Renamed task object to `analyze_financial_document_task`.

6. Crew kickoff inputs not aligned
- Bug: File content was not consistently injected into task context.
- Fix: Standardized kickoff `inputs` and ensured PDF text is passed into task prompt.

7. FastAPI startup deprecation warning
- Bug: Used deprecated `@app.on_event("startup")`.
- Fix: Migrated to `lifespan` event handler.

8. Uvicorn reload warning for direct script execution
- Bug: `reload=True` with object app in direct `python main.py`.
- Fix: Set `reload=False` for script mode.

9. AIMLAPI provider routing mismatch
- Bug: LiteLLM provider detection failed for bare model names in OpenAI-compatible endpoint.
- Fix: Auto-prefix model with `openai/` for AIMLAPI route and pass both `base_url` and `api_base`.

10. AIMLAPI role validation error (`system` role rejected)
- Bug: Provider returned `Invalid discriminator value... Expected 'user' | 'assistant'`.
- Fix: Set `use_system_prompt=False` on `Agent` so payload conforms to provider.

11. Large document context instability
- Bug: Full extracted PDFs were too large for smaller/free models.
- Fix: Added context trimming with fallback retries (`MAX_DOCUMENT_CHARS`, then 6000, then 3000).

12. Weak production diagnostics
- Bug: Generic "LLM Failed" without actionable cause.
- Fix: Added traceback persistence to `error.log` and surfaced location in API error detail.

13. Output persistence missing
- Bug: Analysis responses were returned but not saved.
- Fix: Added `output/` persistence as JSON files and returned `saved_output_file` path in API response.

14. Requirements file issue
- Bug: Stray `click` token and unclear optional dependency status.
- Fix: Removed stray token and documented `crewai-tools` as optional.

15. README install typo
- Bug: `requirement.txt` typo.
- Fix: Corrected to `requirements.txt`.

16. Database persistence for users and analyses missing
- Bug: No relational storage for user metadata and analysis history.
- Fix: Added PostgreSQL integration (`SQLAlchemy` + `psycopg2-binary`), startup table init, `users` and `analysis_results` models, and write path in `POST /analyze`.

17. Missing API endpoints for stored records
- Bug: No way to retrieve stored users/analyses from API.
- Fix: Added `GET /users` and `GET /analyses` with capped pagination.

18. Server URL mismatch in console output
- Bug: Console displayed `http://0.0.0.0:8000`.
- Fix: Changed Uvicorn host to `127.0.0.1` so local run prints `http://127.0.0.1:8000`.


## Setup Instructions

1. Create and activate virtual environment (PowerShell):
```powershell
cd "c:\Users\Lalith Sai Kumar\Desktop\Project\financial-document-analyzer"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

3. Configure `.env`:
```env
LLM_PROVIDER=aimlapi
AIMLAPI_API_KEY=your_key_here
AIMLAPI_BASE_URL=https://api.aimlapi.com/v1
MODEL=google/gemma-3-4b-it
MAX_DOCUMENT_CHARS=8000
OUTPUT_DIR=output
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/financial_analyzer
```

4. Prepare PostgreSQL:
- Create database `financial_analyzer`.
- Optional: run manual schema SQL:
```powershell
psql -U postgres -d financial_analyzer -f .\sql\init_postgres.sql
```
- Note: tables are also auto-created on app startup via SQLAlchemy.

5. Start API:
```powershell
python main.py
```

6. Open docs:
- http://127.0.0.1:8000/docs


## Usage Instructions

### Swagger UI
1. Open `/docs`.
2. Select `POST /analyze`.
3. Upload a PDF file.
4. Optionally set:
- `query`
- `user_name`
- `user_email`
5. Execute.

### cURL Example (`POST /analyze`)
```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@TSLA-Q2-2025-Update.pdf;type=application/pdf" \
  -F "query=Analyze this financial document for investment insights." \
  -F "user_name=Lalith" \
  -F "user_email=lalith@example.com"
```

### List stored users
```bash
curl "http://127.0.0.1:8000/users?limit=20"
```

### List stored analyses
```bash
curl "http://127.0.0.1:8000/analyses?limit=20"
```

### Output Files
- Successful responses are saved under `output/` as JSON.
- API response includes `saved_output_file`.
- Analysis metadata is also stored in PostgreSQL.


## API Documentation

### `GET /`
- Purpose: Health check.
- Response:
```json
{
  "message": "Financial Document Analyzer API is running"
}
```

### `POST /analyze`
- Content type: `multipart/form-data`
- Fields:
- `file` (required): PDF file
- `query` (optional): analysis prompt
- `user_name` (optional): display name (default: `Anonymous`)
- `user_email` (optional): used to upsert/find user

- Success response (`200`):
```json
{
  "status": "success",
  "query": "Analyze this financial document for investment insights.",
  "analysis": "...",
  "file_processed": "TSLA-Q2-2025-Update.pdf",
  "saved_output_file": "output/analysis_YYYYMMDD_HHMMSS_xxxxxxxx.json",
  "user": {
    "name": "User",
    "email": "User@example.com"
  },
  "analysis_record_id": "uuid-value"
}
```

- Common errors:
- `400`: missing filename, non-PDF, or empty upload
- `500`: LLM/provider/runtime failure or database write failure (check `error.log`)

### `GET /users`
- Query param: `limit` (default 50, max 500)
- Returns recent users.

### `GET /analyses`
- Query param: `limit` (default 50, max 500)
- Returns recent analysis metadata.


## Troubleshooting

### PostgreSQL password authentication failed
If you see:
- `FATAL: password authentication failed for user "postgres"`

Your app is using an incorrect password in `DATABASE_URL`.

Update `.env` with the real PostgreSQL credentials:
```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_REAL_PASSWORD@127.0.0.1:5432/financial_analyzer
```

Then restart:
```powershell
python main.py
```

Notes:
- The API now starts even when DB connection fails (`STRICT_DB_STARTUP=false` by default).
- In that state, analysis still works and file output is saved, but DB endpoints return `503`.
- Set `STRICT_DB_STARTUP=true` if you want startup to fail when DB is unavailable.
