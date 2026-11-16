# Plickers School Response System — Database Server

Secure, multi-tenant FastAPI backend for the ArUco-based classroom response system.

---

## Architecture

```
Internet / LAN
      ↓
  FastAPI  (port 8000)
      ↓
  PostgreSQL  (internal network only)

Scanner flow:
  CardDetector (OpenCV)
        ↓ marker_id + rotation → answer
  POST /api/v1/scanner/responses
        ↓ validate + store
  WebSocket /ws/quiz/{session_id}
        ↓ broadcast
  Teacher Dashboard (live)
```

---

## Quick Start

### 1. Clone and configure

```bash
cd school-response-server
cp .env.example .env
# Edit .env — set real secrets for JWT_SECRET_KEY and POSTGRES_PASSWORD
```

### 2. Start with Docker

```bash
# Production mode
docker compose up -d

# Development mode (includes pgAdmin at http://localhost:5050)
docker compose --profile dev up -d
```

The backend automatically runs `alembic upgrade head` on startup.

### 3. Seed development data

```bash
docker compose exec backend python scripts/seed.py
```

This creates:
- 1 school (`DEMO-HS`)
- 1 academic year (2026-2027)
- 2 classes, 2 sections
- **50 students** (exact names from `output/cards.json`)
- **50 cards** (marker_id == card_number, matching ArUco DICT_6X6_250)
- 2 teachers
- 1 sample question set with 5 questions

### 4. Open Swagger UI

→ http://localhost:8000/docs

---

## Development Credentials (seed data — CHANGE IN PRODUCTION)

| Username     | Password        | Role         |
|---|---|---|
| superadmin   | SuperAdmin@1234 | SUPER_ADMIN  |
| schooladmin  | SchoolAdmin@1234| SCHOOL_ADMIN |
| teacher_anil | Teacher@1234    | TEACHER      |
| teacher_maya | Teacher@1234    | TEACHER      |

---

## API Reference

All versioned under `/api/v1/`.

| Route | Description |
|---|---|
| `POST /api/v1/auth/login` | Get JWT access token |
| `GET  /api/v1/auth/me` | Current user info |
| `POST /api/v1/schools` | Create school (SUPER_ADMIN) |
| `GET  /api/v1/schools/{id}/students` | List students |
| `POST /api/v1/schools/{id}/students` | Create student |
| `POST /api/v1/schools/{id}/students/import` | Bulk Excel/CSV import |
| `GET  /api/v1/schools/{id}/cards/search?marker_id=17` | Find card by marker |
| `POST /api/v1/schools/{id}/cards/{id}/assign` | Assign card to student |
| `POST /api/v1/schools/{id}/cards/{id}/replace` | Replace lost card |
| `POST /api/v1/scanner/responses` | Submit scanner detection |
| `WS   /api/v1/schools/{id}/quiz-sessions/ws/quiz/{id}` | Live dashboard WebSocket |
| `GET  /api/v1/schools/{id}/reports/quiz-sessions/{id}/scores` | Quiz scores |

---

## Card System

The card system is **fully compatible with the existing generator**:

```
card_number  ==  marker_id  ==  ArUco ID  (DICT_6X6_250)
```

Orientation → Answer mapping (matches `card_config.py` and `orientation.py`):

| Physical rotation | Answer |
|---|---|
| 0°  (A label UP) | A |
| 90° (B label UP) | B |
| 180° (C label UP)| C |
| 270° (D label UP)| D |

Scanner sends:
```json
{
    "quiz_session_id": 1,
    "question_id": 1,
    "marker_id": 17,
    "rotation": 90,
    "answer": "B",
    "detected_at": "2026-09-29T08:00:00Z"
}
```

---

## Student Import (Excel / CSV)

Upload an `.xlsx` or `.csv` file matching the existing `50_sample_students_plickers.xlsx` format:

```
S.No | Student Name | Student ID | Card ID
  1  | Arun Kumar   | STU001     | 1
  2  | Priya Sharma | STU002     | 2
```

```bash
curl -X POST "http://localhost:8000/api/v1/schools/1/students/import" \
  -H "Authorization: Bearer <token>" \
  -F "file=@50_sample_students_plickers.xlsx"
```

Returns:
```json
{
  "success": true,
  "data": {
    "total_records": 50,
    "successful": 50,
    "failed": 0,
    "errors": []
  }
}
```

---

## Security

- **Argon2id** password hashing (64 MB memory cost)
- **JWT HS256** tokens — role always server-determined, never trusted from frontend
- **Tenant isolation** — school_id FK on every row; cross-school access → 403
- **RBAC** — SUPER_ADMIN, SCHOOL_ADMIN, TEACHER, STUDENT
- **Audit log** — every sensitive action recorded; passwords/tokens never logged
- **Rate limiting** — 10 req/min on auth endpoints
- **Request size limit** — configurable (default 10 MB)
- **Secure HTTP headers** — X-Content-Type-Options, X-Frame-Options, XSS-Protection
- **CORS** — restricted to configured origins
- **SQL injection** — prevented by SQLAlchemy ORM (parameterised queries)
- **PostgreSQL not exposed** — only accessible within Docker network

---

## Database Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Running Tests

```bash
pip install -r requirements.txt
pytest                         # all tests
pytest tests/test_auth.py      # specific file
pytest -v --cov=app            # with coverage
```

Tests use an **in-memory SQLite** database — no PostgreSQL needed for testing.

---

## Project Structure

```
school-response-server/
│
├── app/
│   ├── main.py                 ← FastAPI app factory, middleware, CORS
│   ├── api/v1/
│   │   ├── auth.py             ← POST /auth/login, GET /auth/me
│   │   ├── schools.py          ← School CRUD
│   │   ├── academic_years.py   ← Years, Classes, Sections
│   │   ├── teachers.py         ← Teacher management
│   │   ├── students.py         ← Student CRUD + Excel/CSV import
│   │   ├── cards.py            ← Card lifecycle + assignment
│   │   ├── questions.py        ← Question sets and questions
│   │   ├── quiz_sessions.py    ← Session lifecycle + WebSocket
│   │   ├── scanner.py          ← POST /scanner/responses
│   │   └── reports.py          ← Scores and analytics
│   ├── models/                 ← SQLAlchemy ORM models
│   ├── schemas/                ← Pydantic v2 schemas
│   ├── services/               ← Business logic
│   ├── core/                   ← Config, security, deps, logging
│   ├── db/                     ← Engine, session factory
│   └── websocket/              ← WS connection manager
│
├── alembic/                    ← Database migrations
├── scripts/seed.py             ← Dev seed (50 students from roster)
├── tests/                      ← Pytest test suite
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```
