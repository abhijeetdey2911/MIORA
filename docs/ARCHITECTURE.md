# Project JobHunter — System Architecture (Phase 1)

## 1. Architectural Overview

Project JobHunter is designed as a distributed, decoupled, modular system. Phase 1 provides the foundational skeleton across three primary layers:

```
[ Frontend: React 19 + Vite + Tailwind CSS ]
                     │  (HTTP / JSON REST)
                     ▼
       [ Backend: FastAPI + Uvicorn ]
                     │  (SQLAlchemy 2.0 / psycopg v3)
                     ▼
        [ Database: PostgreSQL 16 ]
```

---

## 2. Layer Architecture

### 2.1 Frontend Shell (`/frontend`)
- **Framework**: React 19 with Vite 8 and TypeScript 5.
- **Styling**: Tailwind CSS v4 with dark mode ambient theming.
- **Routing**: React Router v7 with single-page layout structure.
- **Component Design**:
  - `components/common`: Reusable presentation primitives (`Header`, `Sidebar`, `Footer`, `StatusBadge`).
  - `components/dashboard`: Foundation monitoring panels (`HealthCard`, `SystemMetrics`, `PhaseRoadmap`).
  - `components/layout`: Top-level application shell (`AppLayout`) orchestrating real-time status polling.
  - `services/api.ts`: Centralized fetch client with automatic multi-endpoint fallback and latency timing.

### 2.2 Backend Service (`/backend`)
- **Framework**: FastAPI with Uvicorn ASGI server.
- **Configuration**: Pydantic Settings (`BaseSettings`) loading validated variables from `.env` with type coercions.
- **Database Layer**:
  - SQLAlchemy 2.0 ORM with connection pooling (`pool_pre_ping=True`, pool size 5, max overflow 10).
  - Modern `psycopg` (v3) PostgreSQL adapter.
  - Session dependency generator (`get_db()`) ensuring proper cleanup via context lifecycles.
- **API Versioning**: Root router mounts `/api/v1` prefix.
- **Exception Handling**: Global handlers for HTTP exceptions, request validation errors, and unhandled 500s.
- **Database Migrations**: Alembic initialized with automatic settings integration (`env.py` binds to application configuration).

### 2.3 Database Engine (`PostgreSQL 16`)
- Relational storage for all upcoming entities.
- Persistent volume storage mapped to `jobhunter_postgres_data`.
- Automated initialization script executing `infrastructure/docker/postgres/init.sql`.

---

## 3. Communication Pathways

1. **Frontend to Backend**:
   - In Local Development: Requests route to `http://localhost:8000` or through the Vite proxy (`/api` -> `http://127.0.0.1:8000`).
   - In Docker Compose: Nginx container reverse-proxies `/api/` and `/health` to `http://backend:8000/`.
2. **Backend to Database**:
   - Connection URL: `postgresql+psycopg://<user>:<password>@<host>:<port>/<dbname>`
   - In Local Development: Connects to `localhost:5432`.
   - In Docker Compose: Connects to internal service DNS `db:5432`.
3. **Health Check Pipeline**:
   - Request invokes `GET /api/v1/health` or `GET /health`.
   - `HealthService` executes a `SELECT 1` query to verify database connection live and measures millisecond latency.
   - If database is reachable: returns `status: "healthy"` and database details.
   - If database is offline/unreachable: returns `status: "degraded"` with error diagnostics without crashing the application.

---

## 4. Architectural Boundaries for Phase 1

To preserve codebase modularity and prevent premature complexity:
- **No AI agents** or agent orchestration engines are created in Phase 1.
- **No scraping or resume parsing** routines are included.
- **No business entity tables** are created yet; schema models will be added in Phase 2 via Alembic.
