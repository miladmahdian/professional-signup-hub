# Professional Sign-Up Hub

A full-stack prototype for managing professional sign-ups from multiple sources. The backend provides a REST API for creating, listing, and bulk-upserting professional records, while the frontend offers a clean interface for viewing and adding professionals.

## Tech Stack

| Layer    | Technology                                          |
| -------- | --------------------------------------------------- |
| Backend  | Django 5, Django REST Framework, django-filter       |
| Frontend | React 18, React Router v6, TanStack Query, Tailwind CSS |
| Database | SQLite (zero-config for prototyping)                 |
| Tooling  | Vite 5, Python 3.12+, Node 20+                      |

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver       # → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # → http://localhost:5173
```

The frontend expects the backend to be running on `localhost:8000`.

### Running Tests

```bash
cd backend
python manage.py test professionals -v 2
```

## API Endpoints

| Method | Path                       | Description                              |
| ------ | -------------------------- | ---------------------------------------- |
| GET    | `/api/professionals/`      | List all professionals (optional `?source=` filter) |
| POST   | `/api/professionals/`      | Create a single professional             |
| POST   | `/api/professionals/bulk`  | Bulk upsert professionals (partial success) |

### Bulk Upsert Details

The bulk endpoint accepts a JSON array of professional objects. For each item:

1. **Lookup key:** Uses `email` as the primary lookup. Falls back to `phone` if no email is provided.
2. **Create or update:** If a matching record exists, it is updated. Otherwise, a new record is created.
3. **Partial success:** Each item is processed independently. Valid items succeed even if others fail.
4. **Response format:** `{ "created": [...], "updated": [...], "errors": [...] }` with index tracking.

### Bulk Upsert Examples

**Create new records (email + phone):**

```bash
curl -s -X POST http://localhost:8000/api/professionals/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {"full_name": "Alice Johnson", "email": "alice@example.com", "phone": "555-1001", "company_name": "Acme Corp", "job_title": "Engineer", "source": "direct"},
    {"full_name": "Bob Smith", "email": "bob@example.com", "phone": "555-1002", "source": "partner"}
  ]' | python3 -m json.tool
```

**Create with phone only (no email — phone is the lookup key):**

```bash
curl -s -X POST http://localhost:8000/api/professionals/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {"full_name": "Charlie No-Email", "phone": "555-2001", "source": "internal"}
  ]' | python3 -m json.tool
```

**Update existing records (re-run after create — matched by email):**

```bash
curl -s -X POST http://localhost:8000/api/professionals/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {"full_name": "Alice Johnson-Updated", "email": "alice@example.com", "phone": "555-1001", "job_title": "Senior Engineer", "source": "direct"},
    {"full_name": "Bob Smith-Updated", "email": "bob@example.com", "phone": "555-1002", "job_title": "Lead Designer", "source": "partner"}
  ]' | python3 -m json.tool
```

**Mixed batch — new, update, and error in one request:**

```bash
curl -s -X POST http://localhost:8000/api/professionals/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {"full_name": "Alice Third Update", "email": "alice@example.com", "phone": "555-1001", "job_title": "VP Engineering", "source": "direct"},
    {"full_name": "Eve Brand New", "email": "eve@example.com", "phone": "555-3001", "source": "direct"},
    {"full_name": "Bad Record", "source": "direct"}
  ]' | python3 -m json.tool
```

Expected: index 0 in `updated[]` (Alice matched by email), index 1 in `created[]` (Eve is new), index 2 in `errors[]` (missing phone).

## Assumptions & Trade-offs

- **SQLite** is used for zero-friction setup. In production, PostgreSQL would be used for concurrent access, better constraint handling, and `ON CONFLICT` upsert support.
- **No authentication.** The prototype is open-access. In production, token-based auth (JWT or DRF tokens) would gate all endpoints.
- **No pagination.** The list endpoint returns all records. For larger datasets, cursor-based pagination would be added.
- **Email is nullable** to support phone-only professionals in the bulk upsert flow. This is a deliberate choice — some data sources may only provide phone numbers.
- **Phone is on the form** even though the spec's form field list doesn't include it. The API requires phone as a unique field, so it's included on the form. This is documented here as a known deviation.
- **Bulk response uses HTTP 200** even when some items fail. This follows the partial-success pattern — a 207 or 400 would be misleading when some records succeeded.
- **Invalid source filter** returns an empty list rather than a 400. Filters narrow results — if nothing matches, you get nothing. This is intentional (we use a `CharFilter` instead of `django-filter`'s default `ChoiceFilter` to avoid strict validation on filter params).

## Time Spent

Approximately 3 hours total:

- ~30 min: Design and architecture planning
- ~45 min: Backend setup, models, serializers, and views
- ~45 min: Frontend setup, list page, and form page
- ~30 min: Testing and debugging
- ~30 min: Documentation and polish

## What I'd Improve With More Time

- **`updated_at` field** on the Professional model to track when records were last modified via bulk upsert.
- **Pagination** with cursor-based navigation for the list endpoint and frontend table.
- **Phone normalization** using E.164 format to prevent near-duplicate phone numbers (e.g., "555-0001" vs "+15550001").
- **Authentication** via JWT or session-based auth to secure all API endpoints.
- **End-to-end tests** for multi-step workflows (e.g., create via bulk → update via bulk → verify via list in a single test run).
- **Error boundary** in the frontend React app for graceful error handling.
- **Loading skeletons** instead of plain "Loading..." text for better perceived performance.

## Extension Discussion: PDF Resume Upload

The design document (`DESIGN.md`) includes a detailed discussion of how PDF resume upload could extend the `POST /api/professionals/` endpoint. Two approaches are analyzed:

**Recommended: LLM + Async Processing**

The PDF is uploaded to S3 via a presigned URL, and the professional record is created immediately. A background task (via Django-Q2) sends the PDF to a multimodal LLM for field extraction. Extracted fields fill in blanks without overwriting user-provided data. This approach matches the spec's single-endpoint design, achieves ~95% extraction accuracy, and keeps the API response fast.

**Alternative: pdfplumber + Synchronous Extraction**

The PDF is uploaded directly to Django, fields are extracted synchronously using `pdfplumber` and regex, and the form is pre-filled for user review before submission. This is simpler (no S3, no task queue, no LLM) but requires a separate extraction endpoint not described in the spec, and extraction accuracy drops to ~70%. Acceptable when users review results before saving.

The LLM + Async approach is recommended because the spec places the file on the creation endpoint (no user review step), making extraction accuracy critical. See `DESIGN.md` Section 6 for the full analysis.
