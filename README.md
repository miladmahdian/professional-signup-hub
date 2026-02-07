# Professional Sign-Up Hub

A full-stack prototype for managing professional sign-ups from multiple sources. The backend provides a REST API for creating, listing, and bulk-upserting professional records, while the frontend offers a clean interface for viewing and adding professionals.

## Tech Stack

| Layer    | Technology                                              |
| -------- | ------------------------------------------------------- |
| Backend  | Django 5, Django REST Framework, django-filter          |
| Frontend | React 18, React Router v6, TanStack Query, Tailwind CSS |
| Database | SQLite (zero-config for prototyping)                    |
| Tooling  | Vite 5, Python 3.12+, Node 20+                          |

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

| Method | Path                      | Description                                         |
| ------ | ------------------------- | --------------------------------------------------- |
| GET    | `/api/professionals/`     | List all professionals (optional `?source=` filter) |
| POST   | `/api/professionals/`     | Create a single professional                        |
| POST   | `/api/professionals/bulk` | Bulk upsert professionals (partial success)         |

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

- **SQLite** is used for zero-friction setup. In production, PostgreSQL would be the natural choice for concurrent write access and stronger constraint enforcement. Our upsert logic runs row-by-row in Python (for partial success), so we don't rely on Postgres-specific features like `ON CONFLICT`, but Postgres would still be preferred for reliability under load.
- **No authentication.** The prototype is open-access. In production, the right auth strategy depends on who consumes each endpoint. The frontend (whether it's an internal admin tool or a public sign-up page) would likely use Django's built-in session auth — it's simple, secure, and already part of the framework. The bulk API, which is consumed by partner integrations or internal scripts, would use API key or token auth (`Authorization: Token <key>`) since there's no browser session involved. If the organization uses an identity provider (Okta, Google Workspace, etc.), SSO via OAuth2/OIDC would sit in front of both.
- **No pagination.** The list endpoint returns all records. For a prototype this is fine. In production, offset-based pagination (e.g., `?page=2`) would be the simplest addition.
- **Email is nullable** to support phone-only professionals in the bulk upsert flow. The spec says to fall back to phone when email isn't provided, which implies some records won't have an email. Making email nullable at the database level is the cleanest way to support this.
- **Phone is on the form** even though the spec's form field list doesn't include it. The API requires phone as a unique field, so it must be collected somewhere. Adding it to the form is the most straightforward path. This is a known deviation from the spec's form fields.
- **Bulk response uses HTTP 200** even when some items fail. This follows the partial-success pattern — 400 would imply the entire request was invalid, and 207 Multi-Status (from WebDAV) is uncommon in REST APIs and may confuse consumers. A 200 with a structured `{ created, updated, errors }` body lets the caller inspect exactly what happened.
- **Invalid source filter** returns an empty list rather than a 400. Filters narrow results — if nothing matches, you get nothing. We explicitly use a `CharFilter` instead of `django-filter`'s default `ChoiceFilter` to avoid strict validation on filter params. This is a deliberate design choice: filter parameters should behave like search, not like form validation.

## Time Spent

Approximately 2 hours total:

- ~45 min: Design and architecture planning — data model decisions (nullable email, phone as fallback key), bulk upsert algorithm, API response design, PDF extension discussion
- ~15 min: Backend — Django project setup, model, serializers, views for all three endpoints
- ~15 min: Frontend — React app with routing, list page with filter, form page with validation
- ~30 min: Testing — 30 backend test cases, manual curl verification of all endpoints
- ~15 min: Documentation and polish

## What I'd Improve With More Time

- **Authentication** — session auth for the frontend, API key/token auth for the bulk endpoint, as described in the trade-offs above.
- **`updated_at` field** on the Professional model to track when records were last modified via bulk upsert. Useful for syncing and auditing.
- **Pagination** on the list endpoint and frontend table. Offset-based (`?page=2`) would be the first step.
- **Phone normalization** using E.164 format (via `django-phonenumber-field`) to prevent near-duplicate phone numbers (e.g., "555-0001" vs "+15550001" being treated as different).
- **Error boundary** in the frontend React app so a component crash doesn't take down the whole page.
- **Loading skeletons** instead of plain "Loading..." text for better perceived performance on the list page.

## Design Document

See [DESIGN.md](DESIGN.md) for the full technical design — architecture decisions, data model rationale, upsert algorithm, edge case analysis, and the PDF resume upload extension discussion.
