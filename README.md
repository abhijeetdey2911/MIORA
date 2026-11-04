# Project JobHunter

> **AI-Powered Autonomous Job Hunting Platform**  
> *Phase 1: Foundational Infrastructure*

---

## 1. Project Introduction

**Project JobHunter** is an autonomous, personal AI-powered platform designed to streamline, personalize, and accelerate the job hunting process. From discovery across multiple job boards to automated resume alignment, cover letter customization, application submission, and interview tracking, JobHunter transforms the modern job search.

This repository represents **Phase 1 (Foundational Infrastructure)** of an 8-phase development roadmap. Phase 1 establishes the rock-solid architectural foundation:
- A responsive, dark-themed **React** application shell with real-time backend connectivity telemetry.
- An asynchronous **FastAPI** backend with structured configuration, CORS, versioned routing, and comprehensive health monitoring.
- A **PostgreSQL** database layer configured via **SQLAlchemy 2.0** and **Alembic** migrations.
- Complete **Docker** and **Docker Compose** containerization with health checks and persistent storage.

---

## 2. Technology Stack

### Frontend
- **Framework:** React 19
- **Build Tool:** Vite 8
- **Language:** TypeScript 5
- **Styling:** Tailwind CSS v4
- **Routing:** React Router v7
- **Icons:** Lucide React

### Backend
- **Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Configuration & Validation:** Pydantic v2 & Pydantic Settings
- **ORM:** SQLAlchemy 2.0
- **Database Driver:** Psycopg 3 (Binary)
- **Testing:** Pytest & HTTPX

### Database & Migrations
- **Database:** PostgreSQL 16
- **Migrations:** Alembic

### Infrastructure & DevOps
- **Containers:** Docker (Multi-stage builds)
- **Orchestration:** Docker Compose
- **Web Server:** Nginx (Alpine)

---

## 3. Folder Structure

```
project-jobhunter/
├── frontend/                     # React + Vite + TypeScript frontend
│   ├── public/                   # Static assets & favicon
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/           # Header, Sidebar, Footer, StatusBadge
│   │   │   ├── dashboard/        # HealthCard, SystemMetrics, PhaseRoadmap
│   │   │   └── layout/           # AppLayout shell
│   │   ├── pages/                # DashboardPage, SettingsPage, NotFoundPage
│   │   ├── services/             # API client & health check callers
│   │   ├── types/                # TypeScript interfaces & types
│   │   ├── App.tsx               # Route definitions
│   │   ├── main.tsx              # React DOM entry point
│   │   └── index.css             # Tailwind v4 root styling
│   ├── Dockerfile                # Multi-stage production container build
│   ├── nginx.conf                # Nginx SPA & reverse proxy configuration
│   ├── package.json              # NPM dependencies & scripts
│   ├── tsconfig.json             # TypeScript configuration
│   └── vite.config.ts            # Vite build & dev proxy settings
├── backend/                      # FastAPI Python backend
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/    # Route controllers (health.py)
│   │   │       └── router.py     # Aggregated v1 router
│   │   ├── core/
│   │   │   └── config.py         # Pydantic Settings environment configuration
│   │   ├── db/
│   │   │   ├── base.py           # SQLAlchemy 2.0 DeclarativeBase
│   │   │   └── session.py        # Connection pooling, sessionmaker & db checks
│   │   ├── models/               # ORM models (reserved for Phase 2)
│   │   ├── schemas/              # Pydantic validation schemas (health.py)
│   │   ├── services/             # Business logic (health.py)
│   │   └── main.py               # FastAPI application & middleware
│   ├── alembic/                  # Database migration scripts & environment
│   │   ├── versions/             # Migration version files
│   │   └── env.py                # Alembic runner integrated with app settings
│   ├── tests/                    # Automated pytest suite
│   ├── alembic.ini               # Alembic configuration
│   ├── requirements.txt          # Python dependencies
│   └── Dockerfile                # Python 3.12-slim production container
├── infrastructure/               # Container scripts & infrastructure manifests
│   └── docker/
│       └── postgres/
│           └── init.sql          # PostgreSQL container initialization
├── docs/                         # Architecture & phase specifications
│   ├── ARCHITECTURE.md           # System design & data flow documentation
│   └── PHASE1_FOUNDATION.md      # Phase 1 verification matrix
├── docker-compose.yml            # Multi-container orchestration
├── .env.example                  # Root environment variable template
├── .gitignore                    # Git tracking ignore rules
└── README.md                     # Project documentation
```

---

## 4. Prerequisites

Before running the project, ensure you have installed:
- **Node.js** (v20+ recommended, v22 installed) & **npm** (v10+)
- **Python** (v3.11, v3.12, or v3.14)
- **Docker** & **Docker Compose** (Docker Desktop on Windows/macOS)
- **Git**

---

## 5. Environment Variable Setup

1. Copy the example configuration to a `.env` file in the root directory:
   ```bash
   cp .env.example .env
   ```

2. (Optional) For independent local backend development, copy into `backend/.env`:
   ```bash
   cp backend/.env.example backend/.env
   ```

### Default Environment Parameters:
| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `Project JobHunter` | Name of the platform |
| `VERSION` | `0.1.0` | Application release version |
| `ENVIRONMENT` | `development` | Runtime environment mode |
| `DEBUG` | `true` | Debug flag |
| `API_V1_STR` | `/api/v1` | URL prefix for version 1 API |
| `POSTGRES_SERVER` | `localhost` (or `db` in Docker) | Database hostname |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_USER` | `postgres` | Database username |
| `POSTGRES_PASSWORD` | `postgres_secure_password` | Database password |
| `POSTGRES_DB` | `jobhunter` | Database name |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed origins for CORS |
| `VITE_API_URL` | `http://localhost:8000` | Base URL used by React client |

---

## 6. Docker Startup Instructions (Recommended)

Docker Compose starts all 3 services (Frontend, Backend, PostgreSQL) with a single command:

### Start all services in the background:
```bash
docker compose up -d --build
```

### View container status & health:
```bash
docker compose ps
```

### Stream container logs:
```bash
docker compose logs -f
```

### Stop all services:
```bash
docker compose down
```

### Stop all services and erase persistent database volume:
```bash
docker compose down -v
```

Once running:
- **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173)
- **Backend API Docs:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **Backend Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **PostgreSQL Database:** `localhost:5432`

---

## 7. Local Development Setup (Without Docker)

If you prefer to run services individually on your host machine:

### A. Run PostgreSQL
Ensure PostgreSQL is running locally on port `5432` with a database named `jobhunter`.

### B. Run Backend
1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows:
   python -m venv .venv
   .\.venv\Scripts\activate

   # Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the development server with auto-reload:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

### C. Run Frontend
1. Open a second terminal and navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start Vite dev server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 8. Testing and Validation

### Running Backend Automated Tests:
```bash
cd backend
pytest -v
```

### Running Frontend Build Validation:
```bash
cd frontend
npm run build
```

### Testing Backend Health Endpoints via Curl:
```bash
# Test root health endpoint
curl -X GET http://localhost:8000/health

# Test versioned API v1 health endpoint
curl -X GET http://localhost:8000/api/v1/health
```

### Sample Health Response (`GET /api/v1/health`):
```json
{
  "status": "healthy",
  "project": "Project JobHunter",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-11-03T03:25:00.000000Z",
  "services": {
    "database": {
      "status": "connected",
      "latency_ms": 1.45,
      "dialect": "postgresql",
      "error": null
    },
    "api": {
      "status": "operational",
      "uptime_seconds": 45.2
    }
  },
  "system": {
    "python_version": "3.14.2",
    "environment": "development"
  }
}
```

---

## 9. Next Steps: Roadmap to Phase 2

Phase 1 completes the full architectural skeleton. Phase 2 will introduce:
- Database schema design & declarative ORM models (`Job`, `Resume`, `Application`, `Company`).
- Alembic migration generation and automated rollback testing.
- Base CRUD repositories and data access layers.

*Note: Work on Phase 2 will only begin upon explicit user approval.*

