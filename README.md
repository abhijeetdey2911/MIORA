# MIORA — Your AI Job Hunting Assistant

**MIORA by MEMORA** is an AI-powered job discovery and application management platform designed to simplify the job-hunting process.

MIORA helps candidates discover relevant opportunities, analyse resume compatibility, identify application routes, manage applications and track recruitment updates.

## Core Features

- **Job Preferences:** Manage multiple job preferences and target locations.
- **Resume Manager:** Upload, manage and organise resumes.
- **AI Resume Intelligence:** Analyse resumes, identify improvements and generate enhanced versions for approval.
- **Agent 1 — Job Discovery:** Discover relevant job opportunities.
- **Agent 2 — Job Matching:** Evaluate jobs against candidate profiles and preferences.
- **Agent 3 — Application Route Discovery:** Identify official application channels.
- **Agent 4 — Application Execution:** Prepare and manage job applications.
- **Agent 5 — Application Tracking:** Monitor application progress and updates.
- **Central Orchestrator:** Coordinate workflows and background execution.
- **Automation Dashboard:** Manage and monitor automation workflows.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, TypeScript |
| Backend | Python, FastAPI |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| AI | LLM API integration |
| Background Tasks | Celery, Redis |
| Browser Automation | Playwright |
| Infrastructure | Docker, Docker Compose |
| Future Deployment | AWS |

## Project Structure

```text
MIORA/
├── frontend/
├── backend/
├── infrastructure/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Run Locally

### 1. Start PostgreSQL

```powershell
docker start jobhunter-db
```

### 2. Run Database Migrations

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### 3. Start FastAPI

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 4. Start Celery Worker

Requires Redis running on port 6379.

```powershell
cd backend
.\.venv\Scripts\celery.exe -A app.services.celery_app.celery_app worker --loglevel=info --pool=solo
```

### 5. Start Frontend

Open another terminal:

```powershell
cd frontend
npm run dev
```

Open the local frontend URL displayed by Vite (currently expected at port 5174).

## Environment Configuration

Copy `.env.example` to `.env` and configure the required values.

Typical configuration includes:

- Database connection
- Redis connection
- AI provider and API key
- Resume storage settings
- Application security settings

Never commit `.env` files, API keys, passwords or private credentials.

## Development Roadmap

- [x] Core platform and dashboard
- [x] Job preferences
- [x] Resume management
- [x] AI resume intelligence
- [x] Multi-agent job-hunting architecture
- [ ] Final end-to-end verification
- [ ] AWS deployment
- [ ] Telegram notifications
- [ ] LinkedIn networking integration
- [ ] HR email outreach

## Safety

MIORA should use approved resumes, legitimate job listings and authorised application channels. Applications and external outreach should follow user approval settings and platform policies.

## Project

**Product:** MIORA  
**Company:** MEMORA  
**Purpose:** AI-powered job discovery and application assistance.

*Built by MEMORA.*
