# MIORA — AWS EC2 (Ubuntu 24.04) Production Deployment Guide

This guide provides step-by-step operational instructions for deploying and running MIORA on an AWS EC2 instance running Ubuntu 24.04 LTS (2 vCPU, 2 GB RAM, 20 GB Disk).

---

## 1. System Architecture Overview

```text
                       Client Browser
                             │
                             ▼ (Port 80 HTTP / 443 HTTPS)
                   ┌───────────────────┐
                   │  miora-frontend   │ (Nginx 1.27 + Static SPA)
                   │  (Reverse Proxy)  │
                   └─────────┬─────────┘
                             │
            Internal Docker Bridge Network (miora-network)
            ─────────────────┬────────────────────────────
                             │
           ┌─────────────────┴─────────────────┐
           ▼                                   ▼
  ┌──────────────────┐               ┌──────────────────┐
  │  miora-backend   │               │   miora-worker   │
  │  (FastAPI ASGI)  │               │ (Celery Worker)  │
  └────────┬─────────┘               └────────┬─────────┘
           │                                  │
           ├─────────────────┬────────────────┤
           ▼                 ▼                ▼
  ┌──────────────────┐ ┌───────────┐ ┌──────────────────┐
  │     miora-db     │ │miora-redis│ │  resume_storage  │
  │ (PostgreSQL 16)  │ │ (Redis 7) │ │ (Docker Volume)  │
  └──────────────────┘ └───────────┘ └──────────────────┘
```

**Security Isolation:**
- Only `miora-frontend` exposes port 80 to the host network.
- `miora-db` (5432), `miora-redis` (6379), and `miora-backend` (8000) are internal to `miora-network` and are **not** reachable from the internet.
- Resume uploads are stored in the persistent Docker volume `miora_resume_storage` and survive container rebuilds.

---

## 2. Server Preparation (Ubuntu 24.04)

### Step 2.1: Add 2 GB Swap Space (Crucial for 2 GB RAM Instance)
To protect against Out-Of-Memory (OOM) events during builds or high concurrency:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verify swap is active:
```bash
free -h
```

### Step 2.2: Install Docker & Docker Compose (If not already installed)
```bash
sudo apt update && sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow current user to run Docker without sudo
sudo usermod -aG docker $USER
newgrp docker
```

---

## 3. Deployment Steps

### Step 3.1: Clone the Repository
```bash
git clone https://github.com/abhijeetdey2911/MIORA.git
cd MIORA
```

### Step 3.2: Configure Production Environment Variables
Copy the production environment example:
```bash
cp .env.production.example .env
chmod 600 .env
nano .env
```

Set the required values:
1. `POSTGRES_PASSWORD`: Generate a secure random password (`openssl rand -hex 24`).
2. `AI_PROVIDER` & `GEMINI_API_KEY` (or `OPENAI_API_KEY`): Your LLM API key.
3. `CORS_ORIGINS`: Include `http://<EC2_PUBLIC_IP>` or your domain name.
4. Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

### Step 3.3: Build Docker Containers
```bash
docker compose build
```

### Step 3.4: Apply Database Migrations (Alembic)
Run migrations using a temporary backend runner before starting the web server:
```bash
# Start database and redis first
docker compose up -d db redis

# Wait 5-10 seconds for PostgreSQL to be healthy, then run Alembic migrations
docker compose run --rm backend alembic upgrade head
```

### Step 3.5: Launch All Production Services
```bash
docker compose up -d
```

### Step 3.6: Verify System Health
Check container statuses:
```bash
docker compose ps
```

All 5 containers (`miora-db`, `miora-redis`, `miora-backend`, `miora-celery-worker`, `miora-frontend`) should display `Up` (or `Up (healthy)`).

Test API health through the frontend Nginx reverse proxy:
```bash
curl -i http://localhost/health
```

Expected response:
```json
HTTP/1.1 200 OK
{"status":"healthy","project":"MIORA","version":"0.1.0","environment":"production", ...}
```

---

## 4. Operational Commands & Runbook

### A. Viewing Container Logs
```bash
# View combined live logs
docker compose logs -f

# View specific service logs
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend
docker compose logs -f db
docker compose logs -f redis
```

### B. Restarting Services
```bash
# Restart all services
docker compose restart

# Restart only backend and worker (e.g., after modifying an API key in .env)
docker compose restart backend worker

# Restart frontend (Nginx)
docker compose restart frontend
```

### C. Zero-Downtime Application Updates (Pull & Redeploy)
```bash
# 1. Pull latest code from GitHub
git pull origin main

# 2. Build updated images
docker compose build

# 3. Apply any new database migrations
docker compose run --rm backend alembic upgrade head

# 4. Recreate containers with new images
docker compose up -d --remove-orphans
```

### D. Stopping the Application
```bash
# Stop containers (preserves all data in volumes)
docker compose down

# DO NOT use -v in production unless you want to delete all database & resume data!
```

---

## 5. Backup & Disaster Recovery Procedures

### 5.1: Automated Database Backup (PostgreSQL Dump)
Create a compressed timestamped SQL dump:
```bash
mkdir -p ~/miora_backups

# Dump database
docker compose exec -T db pg_dump -U miora_user -d miora | gzip > ~/miora_backups/miora_db_$(date +%Y%m%d_%H%M%S).sql.gz

# Check backup file
ls -lh ~/miora_backups/
```

### 5.2: Database Restore
```bash
# Uncompress and pipe into PostgreSQL container
gunzip < ~/miora_backups/miora_db_YYYYMMDD_HHMMSS.sql.gz | docker compose exec -T db psql -U miora_user -d miora
```

### 5.3: Backup Uploaded Resumes Volume
```bash
# Create tarball of the persistent resume volume
docker run --rm \
  -v miora_resume_storage:/source:ro \
  -v ~/miora_backups:/backup \
  alpine tar czf /backup/miora_resumes_$(date +%Y%m%d_%H%M%S).tar.gz -C /source .
```

### 5.4: Restore Uploaded Resumes Volume
```bash
docker run --rm \
  -v miora_resume_storage:/target \
  -v ~/miora_backups:/backup \
  alpine sh -c "tar xzf /backup/miora_resumes_YYYYMMDD_HHMMSS.tar.gz -C /target"
```

---

## 6. Security Hardening Checklist for AWS EC2

1. **AWS EC2 Security Group:**
   - Inbound: Port 22 (SSH - restricted to your IP).
   - Inbound: Port 80 (HTTP - `0.0.0.0/0`).
   - Inbound: Port 443 (HTTPS - `0.0.0.0/0`).
   - **BLOCK:** Ports 5432, 6379, and 8000 from inbound public traffic.
2. **File Permissions:**
   - Ensure `.env` is set to `chmod 600 .env`.
3. **SSL / HTTPS (Optional with Certbot):**
   - If using a domain name, install `certbot` on host or place AWS ALB (Application Load Balancer) in front of EC2.

