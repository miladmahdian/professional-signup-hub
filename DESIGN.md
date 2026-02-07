# Technical Design Document — NewtonX Professional Sign-Up Unification

## 1. Overview

### Problem

Professional sign-ups currently happen through multiple disconnected sources (website direct, partner referrals, internal additions). There is no unified view to manage or filter them.

### Solution

Build a prototype with a Django REST Framework backend and a React frontend that:

- Collects professional details from multiple sources via API
- Displays all professionals in a single table view
- Supports filtering by signup source
- Supports bulk upsert with partial success reporting

---

## 2. Architecture

```
┌─────────────────────┐        ┌──────────────────────────┐
│   React Frontend    │  HTTP  │   Django REST Framework   │
│   (Vite + React)    │◄──────►│   Backend API             │
│                     │        │                           │
│  - React Router     │        │  - SQLite (dev)           │
│  - TanStack Query   │        │  - DRF Serializers        │
│  - Tailwind CSS     │        │  - Professional Model     │
└─────────────────────┘        └──────────────────────────┘
     localhost:5173                  localhost:8000
```

### Tech Stack

| Layer     | Technology                      | Rationale                                                                                  |
| --------- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| Backend   | Django 5.x + DRF 3.x            | Required by spec                                                                           |
| Filtering | django-filter                   | Declarative filtering; same behavior as manual code but extensible without rewriting views |
| Database  | SQLite                          | Zero-setup for reviewers; note Postgres for production                                     |
| Frontend  | React 18 + Vite                 | Fast dev server, modern tooling                                                            |
| Routing   | React Router v6                 | Multi-page SPA with clean URLs                                                             |
| Data      | TanStack Query (React Query) v5 | Server-state caching, auto-refetch, less boilerplate                                       |
| Styling   | Tailwind CSS                    | Rapid, consistent UI without custom CSS files                                              |
| API Calls | fetch (native)                  | No need for axios in a small prototype                                                     |

---

## 3. Backend Design

### 3.1 Model: `Professional`

```python
class Professional(models.Model):
    class Source(models.TextChoices):
        DIRECT = 'direct', 'Direct'
        PARTNER = 'partner', 'Partner'
        INTERNAL = 'internal', 'Internal'

    full_name   = models.CharField(max_length=255)
    email       = models.EmailField(unique=True, null=True, blank=True)
    phone       = models.CharField(max_length=20, unique=True)
    company_name = models.CharField(max_length=255, blank=True, default='')
    job_title   = models.CharField(max_length=255, blank=True, default='')
    source      = models.CharField(max_length=10, choices=Source.choices)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
```

**Key decisions:**

- `email` is **nullable** — because the bulk endpoint can use phone as the fallback key, implying some records may not have an email.
- `phone` is **required and unique** — serves as the secondary identifier.
- `company_name` and `job_title` are **optional** — the spec lists them on the model and form but not in the POST field list. We include them everywhere for consistency.
- `id` is the auto-generated primary key (default Django behavior). Neither email nor phone is the PK.

### 3.2 Endpoints

#### `POST /api/professionals/` — Create Single Professional

| Aspect     | Detail                                                                                        |
| ---------- | --------------------------------------------------------------------------------------------- |
| Input      | JSON body: `full_name`, `email`, `phone`, `source`, `company_name` (opt), `job_title` (opt)   |
| Validation | Unique email, unique phone, source in [`direct`, `partner`, `internal`], `full_name` required |
| Response   | `201 Created` with serialized professional                                                    |
| Error      | `400 Bad Request` with field-level error messages                                             |

#### `POST /api/professionals/bulk` — Bulk Upsert

| Aspect     | Detail                                                     |
| ---------- | ---------------------------------------------------------- |
| Input      | JSON body: list of professional objects                    |
| Upsert key | Primary: `email`. Fallback: `phone` (when email is absent) |
| Behavior   | For each item: validate → lookup → create or update        |
| Response   | `200 OK` (or `207 Multi-Status`) with detailed results     |

**Response format:**

```json
{
  "created": [
    { "index": 0, "professional": { "id": 1, "full_name": "Alice", ... } }
  ],
  "updated": [
    { "index": 2, "professional": { "id": 5, "full_name": "Bob", ... } }
  ],
  "errors": [
    { "index": 1, "data": { "email": "bad" }, "errors": { "email": ["Enter a valid email."] } }
  ]
}
```

**Upsert algorithm (per item):**

```
for index, item in enumerate(request_data):
    1. Validate fields via serializer
       → if invalid, append to errors[] with index & field errors, continue

    2. Determine lookup key:
       - if item.email exists → lookup by email
       - elif item.phone exists → lookup by phone
       - else → append to errors[] ("email or phone required"), continue

    3. Try to find existing record:
       - Found → update fields, save → append to updated[]
       - Not found → create new record → append to created[]

    4. Catch IntegrityError (unique constraint violation during save):
       → append to errors[] with details, continue
```

**Important:** Each item is processed independently. One failure does not roll back others (partial success).

#### `GET /api/professionals/` — List Professionals

| Aspect   | Detail                                                      |
| -------- | ----------------------------------------------------------- |
| Params   | `?source=direct\|partner\|internal` (optional filter)       |
| Response | `200 OK` with list of all professionals (filtered if param) |
| Ordering | By `-created_at` (newest first)                             |

**Filtering implementation:** Uses `django-filter` with a declarative `FilterSet` rather than manual `query_params` checking in the view. This implements exactly the spec's `?source=` filter, but the pattern is naturally extensible — adding another filter later is a one-line addition to the filterset, not a rewrite of the queryset logic.

```python
import django_filters

class ProfessionalFilter(django_filters.FilterSet):
    class Meta:
        model = Professional
        fields = ['source']

class ProfessionalListCreateView(generics.ListCreateAPIView):
    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer
    filterset_class = ProfessionalFilter
```

### 3.3 Serializers

Two serializers:

1. **`ProfessionalSerializer`** — used for single create and list responses. Standard ModelSerializer with all fields. Validates email uniqueness, phone uniqueness, source choices.

2. **`BulkProfessionalItemSerializer`** — used for each item in the bulk endpoint. Same fields but with relaxed unique validators (uniqueness is handled manually in the upsert logic, not by DRF's built-in unique validator, to distinguish "create" from "update").

### 3.4 URL Structure

```
/api/professionals/       GET    → list
/api/professionals/       POST   → create single
/api/professionals/bulk   POST   → bulk upsert
```

### 3.5 Dependencies

```
# requirements.txt
django>=5.0,<6.0
djangorestframework>=3.14,<4.0
django-filter>=24.0
django-cors-headers>=4.0
```

### 3.6 CORS

Use `django-cors-headers` to allow requests from `localhost:5173` (Vite dev server).

---

## 4. Frontend Design

### 4.1 Page Structure

```
/                        → Redirect to /professionals
/professionals           → ProfessionalsList (table + filter)
/professionals/new       → AddProfessional (form)
```

**Navigation bar** on all pages with links to both views.

### 4.2 Component Tree

```
<App>
  <QueryClientProvider>
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Navigate to="/professionals" />} />
        <Route path="/professionals" element={<ProfessionalsList />} />
        <Route path="/professionals/new" element={<AddProfessional />} />
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
</App>
```

### 4.3 ProfessionalsList Page

- **Source filter dropdown** at the top: options are "All", "Direct", "Partner", "Internal"
- Changing the dropdown updates the `source` state → triggers React Query refetch with `?source=` param
- **Table columns:** Full Name, Email, Phone, Company, Job Title, Source, Created At
- Loading and error states handled by `useQuery`
- Empty state message when no results

```js
const { data, isLoading, error } = useQuery({
  queryKey: ['professionals', source],
  queryFn: () => fetchProfessionals(source),
});
```

### 4.4 AddProfessional Page

- **Form fields:** Full Name*, Email, Phone*, Company Name, Job Title, Source\* (dropdown)
- Client-side validation: required fields marked, email format check
- On submit → `useMutation` calls `POST /api/professionals/`
- On success → invalidate `['professionals']` query cache → navigate to `/professionals`
- On error → display server-side validation errors inline under each field

```js
const mutation = useMutation({
  mutationFn: createProfessional,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['professionals'] });
    navigate('/professionals');
  },
});
```

### 4.5 API Client

A centralized `api/client.js` helper handles base URL, headers, and error parsing in one place. Endpoint-specific functions in `api/professionals.js` stay thin and focused.

**`api/client.js` — shared fetch helper:**

```js
const API_BASE = 'http://localhost:8000/api';

export async function apiCall(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw error;
  }
  return res.json();
}
```

**`api/professionals.js` — endpoint functions:**

```js
import { apiCall } from './client';

export function fetchProfessionals(source) {
  const params = source ? `?source=${source}` : '';
  return apiCall(`/professionals/${params}`);
}

export function createProfessional(data) {
  return apiCall('/professionals/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
```

### 4.6 Styling Approach

Tailwind CSS for all styling:

- Clean, minimal table with hover states
- Form with proper spacing, labels, and inline error messages
- Responsive layout (works on smaller screens)
- Consistent color scheme using Tailwind's built-in palette

---

## 5. Edge Cases & Testing Plan

### 5.1 Single Create Endpoint

| #   | Test Case                                | Expected Result                                      |
| --- | ---------------------------------------- | ---------------------------------------------------- |
| 1   | Valid data, all fields                   | `201`, professional created                          |
| 2   | Missing `full_name`                      | `400`, error on `full_name`                          |
| 3   | Missing `source`                         | `400`, error on `source`                             |
| 4   | Invalid `source` value (e.g., "unknown") | `400`, error on `source`                             |
| 5   | Duplicate `email`                        | `400`, "professional with this email already exists" |
| 6   | Duplicate `phone`                        | `400`, "professional with this phone already exists" |
| 7   | Invalid email format                     | `400`, "enter a valid email address"                 |
| 8   | Email is empty string vs null vs omitted | Should all be acceptable (phone-only professional)   |
| 9   | Very long `full_name` (>255 chars)       | `400`, max length exceeded                           |
| 10  | Create with only required fields         | `201`, optional fields default to empty string       |

### 5.2 Bulk Upsert Endpoint

| #   | Test Case                                               | Expected Result                                        |
| --- | ------------------------------------------------------- | ------------------------------------------------------ |
| 11  | All valid, all new records                              | All in `created[]`, empty `errors[]`                   |
| 12  | All valid, all existing records (by email)              | All in `updated[]`                                     |
| 13  | Mix of new and existing                                 | Correct split across `created[]` and `updated[]`       |
| 14  | One invalid record among valid ones                     | Valid ones succeed, invalid one in `errors[]`          |
| 15  | Record with email matching A, phone matching B          | Error: unique constraint on phone when updating A      |
| 16  | Record with no email — falls back to phone lookup       | Finds and updates by phone                             |
| 17  | Record with no email and no phone                       | Error: "email or phone required"                       |
| 18  | Two items in same batch with same email                 | First creates, second updates (or deduplicate upfront) |
| 19  | Empty list `[]`                                         | `200` with empty created/updated/errors                |
| 20  | Single item in list                                     | Works like single create but with bulk response format |
| 21  | Upsert updates `full_name` but keeps other fields       | Only provided fields change, others remain             |
| 22  | No email, phone lookup, but update includes taken email | Error on that record, others unaffected                |
| 23  | All records fail validation                             | `200` with all in `errors[]`, nothing created          |

### 5.3 List Endpoint

| #   | Test Case                    | Expected Result                               |
| --- | ---------------------------- | --------------------------------------------- |
| 24  | No query param               | Returns all professionals                     |
| 25  | `?source=direct`             | Returns only direct-source professionals      |
| 26  | `?source=invalid`            | Returns empty list (or 400 — document choice) |
| 27  | No professionals in database | Returns empty list `[]`                       |
| 28  | Check ordering               | Newest first (by `created_at`)                |

### 5.4 Frontend

| #   | Test Case                                     | Expected Result                               |
| --- | --------------------------------------------- | --------------------------------------------- |
| 29  | Submit form with valid data                   | Success, redirects to list, new entry visible |
| 30  | Submit form with server-side validation error | Errors shown inline under relevant fields     |
| 31  | Filter dropdown changes                       | Table updates to show filtered results        |
| 32  | Navigate from form → list → back to form      | Form is reset (not pre-filled with old data)  |
| 33  | List page with no data                        | Shows "No professionals found" message        |
| 34  | Loading state                                 | Spinner/skeleton while fetching               |
| 35  | Network error                                 | Error message displayed                       |

---

## 6. Extension Discussion: PDF Resume Upload

> This section is a design discussion as requested by the spec, not implemented in the prototype.

The spec describes a PDF resume uploaded via `POST /api/professionals/` — the same endpoint that creates the professional. This suggests the file is part of the creation request, and there is no separate step where the user reviews extracted data before the record is saved. Without human review, extraction accuracy is critical, which drives the architecture toward an LLM-based approach with async processing.

### 6.1 How would the system process and interpret the content of the uploaded PDF?

The PDF is sent to a multimodal LLM (e.g., GPT-4o, Claude) with a structured prompt asking it to extract `full_name`, `email`, `phone`, `company_name`, and `job_title` as JSON. Modern multimodal models accept PDFs natively, handling OCR, layout understanding, and semantic interpretation in a single step. There is no need for an intermediate text-extraction library — the LLM sees the full PDF including layout, columns, and section headers, which helps it identify the correct fields.

LLM-based extraction is chosen over pattern matching (regex/heuristics) because the spec places the file upload on the creation endpoint, meaning extracted data is saved directly without user review. In that context, accuracy is the priority: an LLM achieves roughly 95% accuracy across varied resume formats, whereas regex-based extraction drops to 60–70% for less structured fields like job title and company name. Silently saving incorrect data 30–40% of the time is a worse outcome than taking a few extra seconds to process.

**Merge strategy:** Extracted fields only fill in blanks. Any field the user explicitly provided on the form takes priority and is never overwritten by the extraction result. For example, if the user typed a company name but left job title blank, only job title is filled from the resume.

**Failure handling:** If the LLM call fails or returns unparseable output, the task retries with exponential backoff (up to 3 attempts). On permanent failure, the record is marked with `processing_status: failed` so it can be identified and edited manually.

### 6.2 What is the proposed method for handling the actual file upload?

The file is uploaded to S3 using a presigned URL, keeping the file transfer off the Django server. The flow has three steps:

1. **Get an upload URL.** The frontend requests a presigned PUT URL from Django before submitting the form. Django generates a time-limited (5 min), scoped URL via the S3 API that restricts the upload to a specific S3 key, enforces `application/pdf` content type, and caps file size at 5MB.
2. **Upload to S3.** The frontend uploads the PDF directly to S3 using the presigned URL. Django is not involved in this transfer, so no server worker is tied up during the upload.
3. **Submit the form.** The frontend sends the professional data to `POST /api/professionals/` with the S3 key included in the payload. Django creates the professional immediately with the user-provided fields, stores the S3 key on the record, and dispatches a background task for resume processing.

**Why presigned URLs:** Since the LLM processing happens asynchronously in a background worker, the worker needs to access the file after the HTTP request is complete. Storing the file in S3 gives the worker a reliable location to fetch it from. Additionally, routing the file through Django would tie up a server worker for the entire upload duration — unnecessary when Django doesn't need to process the file bytes itself.

**Async processing:** The professional is created immediately and the API returns `201` without waiting for extraction. The LLM processing runs in the background via Django-Q2, a lightweight task queue that uses the existing database as its message broker. Django-Q2 requires no additional infrastructure — no Redis, no separate message queue. A Q cluster process (started alongside the Django server) polls the database for pending tasks and executes them. The polling interval (a few seconds by default) is negligible compared to the 5–15 second LLM processing time. At higher scale (thousands of tasks per minute), Celery with Redis would replace Django-Q2 for instant task delivery and higher throughput, but that is not warranted for the volumes this spec implies.

### 6.3 What additional functionalities or elements would be incorporated into the frontend?

**On the Add Professional form:**

- A file input area (drag-and-drop zone or file picker), restricted to `.pdf` and max 5MB, shown alongside the existing form fields.
- When the user selects a file, the frontend requests a presigned URL from Django and uploads the file to S3 in the background. A progress indicator shows upload status. On success, the file input displays the filename with a remove/replace option, and the S3 key is stored in component state.
- The user fills in whatever fields they already know (perhaps just name and source) and submits the form. The S3 key is included in the payload. The form works identically whether or not a resume is attached — the resume is optional and additive.

**After form submission:**

- If a resume was included, the professionals list shows a "Processing resume..." indicator on that record.
- The frontend polls the professional's detail endpoint every 2–3 seconds until `processing_status` changes from `pending`.
- On `completed`: the record updates to show the LLM-extracted fields (job title, company, etc.) filled in.
- On `failed`: a message indicates extraction could not be completed, and the user can edit the fields manually.

### 6.4 Alternative: Synchronous Extraction with User Review

If the UX were redesigned so the user reviews extracted data before the professional is created, the architecture simplifies significantly. This would require a separate extraction endpoint (e.g., `POST /api/professionals/extract-resume/`) outside of what the spec describes, but is worth noting as an alternative.

In this flow, the user selects a PDF on the form, the frontend sends it to the extraction endpoint via `multipart/form-data`, and the backend extracts fields synchronously using `pdfplumber` and regex/heuristics — returning the result in under a second. The form is pre-filled with the extracted data, the user reviews and corrects any mistakes, then submits the creation endpoint as usual.

This eliminates the need for S3, presigned URLs, background task queues, and LLMs. The lower extraction accuracy (~70%) is acceptable because the user is present to catch and correct errors. The tradeoff is that it requires an additional endpoint not described in the spec and only works for interactive form-based uploads — not for bulk or API-driven use cases where no user is reviewing the results.

### Summary

|                                            | Recommended: LLM + Async | Alternative: pdfplumber + Sync               |
| ------------------------------------------ | ------------------------ | -------------------------------------------- |
| Matches spec's `POST /api/professionals/`? | Yes                      | No — requires a separate extraction endpoint |
| User reviews before save?                  | No                       | Yes                                          |
| Extraction accuracy                        | ~95% (LLM)               | ~70% (regex/heuristics)                      |
| Upload method                              | Presigned S3 URL         | `multipart/form-data` to Django              |
| Processing                                 | Async via Django-Q2      | Synchronous in the request                   |
| Infrastructure                             | Django + S3 + Django-Q2  | Just Django                                  |
| Works for bulk/API?                        | Yes                      | No — requires a user on the form             |

---

## 7. Project Structure

```
newtonx/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                  # Django project settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── professionals/           # Django app
│       ├── models.py
│       ├── serializers.py
│       ├── filters.py
│       ├── views.py
│       ├── urls.py
│       └── tests.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   ├── client.js
│       │   └── professionals.js
│       ├── components/
│       │   └── Navbar.jsx
│       └── pages/
│           ├── ProfessionalsList.jsx
│           └── AddProfessional.jsx
├── DESIGN.md
└── README.md
```

---

## 8. Design Philosophy

Build exactly what the spec asks for — no extra fields, no speculative features. But when there are two ways to implement the same requirement, choose the pattern that doesn't paint us into a corner. The deliverable is identical; the internal quality is higher.

Concrete examples of this in the design:

- **`django-filter` over manual `if` blocks** — same `?source=` filter the spec requests, but implemented with a declarative filterset instead of hardcoded queryset logic. Adding a future filter is a one-line change, not a view rewrite.
- **Centralized API client over scattered `fetch` calls** — same HTTP requests, but common concerns (base URL, headers, error parsing) are defined once. Adding auth headers later means changing one file, not every call site.
- **React Query over manual `useState`** — same data flow, but with caching and invalidation built in. The list page shows instantly when navigating back instead of re-fetching every time.
- **React Router over conditional rendering** — same two pages the spec asks for, but each has a URL and the pattern supports adding more pages without restructuring.

Things we explicitly chose _not_ to add (but would note in the README as future improvements):

- `updated_at` timestamp — useful for upserts but not in the spec's model definition
- Soft delete / `is_active` flag — not requested
- Pagination — not needed at prototype scale
- Bulk response `summary` counts — consumers can count the arrays themselves
- Authentication — not in scope

---

## 9. Assumptions & Trade-offs

1. **SQLite over Postgres** — Chosen for zero-friction reviewer setup. Production would use Postgres.
2. **No authentication** — Not in spec. Would add token/session auth in production.
3. **No pagination** — Acceptable for prototype scale. Would add cursor-based pagination for production.
4. **Phone stored as string** — No E.164 normalization in prototype. Would use `django-phonenumber-field` in production.
5. **Bulk endpoint processes sequentially** — Not wrapped in a single transaction, enabling partial success. A transaction-per-item approach could be added for data integrity.
6. **Email is nullable** — Required to support phone-only lookups in the bulk endpoint.
7. **Invalid `?source=` filter returns empty list** — Rather than 400, to keep the API lenient. Documented behavior.
8. **Bulk response uses HTTP 200** — Even with partial failures. An alternative is 207 Multi-Status, but 200 with structured body is simpler for the frontend to handle.

---

## 10. Implementation Order

1. Backend setup — Django project, app, model, serializers, filter, CORS, migrations
2. Backend API — List & single create endpoint with curl verification
3. Backend API — Bulk upsert endpoint with curl verification
4. Frontend setup — Vite, React, Tailwind, routing, API client, React Query
5. Frontend — Professionals list page with source filter
6. Frontend — Add professional form page with validation
7. Backend tests — 30 test cases covering all edge cases from Section 5
8. README & documentation
