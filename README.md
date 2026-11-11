# 🍎 Apple Worm Adventure

**Apple Worm Adventure (AWA)** is a full-stack, browser-based puzzle game where players control a worm, collect apples, navigate obstacles, and solve challenging levels using strategic movement.

The application is built with **React, TypeScript, Django REST Framework, and PostgreSQL**, with Docker-based deployment support and live hosting on Render.

---

## 🔗 Project Links

| Resource | Link |
|---|---|
| 🌐 Live Frontend | [Open Apple Worm Adventure](https://awa-frontend-1ikn.onrender.com/) |
| ⚙️ Backend API | [AWA Backend](https://awa-backend-wfvo.onrender.com/) |
| ❤️ Backend Health Check | [API Health](https://awa-backend-wfvo.onrender.com/api/health/) |
| 🔌 Frontend API Proxy | [API Health via Frontend](https://awa-frontend-1ikn.onrender.com/api/health/) |
| 💻 GitHub Repository | [Apple Worm Adventure](https://github.com/Aadit23042006/apple-worm-adventure) |
| 🎬 Project Demonstration | [Watch Project Demo](https://drive.google.com/file/d/1HOFCVIMizAZD6oI4qD6mEp9XsG2OZnyd/view?usp=drive_link) |

**Local development URLs**

- Frontend: `http://127.0.0.1:5177/`
- Backend API: `http://127.0.0.1:8002/api/`

*Note: The live services have been deployed on Render. Individual application features should be considered production-verified only after their respective end-to-end tests pass.*

---

## 📌 Project Overview

| Detail | Description |
|---|---|
| Project Name | Apple Worm Adventure |
| Short Name | AWA |
| Frontend | React, TypeScript, Vite |
| Backend | Python, Django REST Framework |
| Database | PostgreSQL |
| Web Server | Nginx |
| Application Server | Gunicorn |
| Authentication | Django Authentication and API Authentication |
| Containerization | Docker |
| Deployment | Render |
| Game Type | Logic-based Puzzle Game |

---

## ✨ Features

### 🎮 Gameplay

- Interactive worm movement.
- Apple collection and scoring.
- Grid-based puzzle gameplay.
- Obstacles and level challenges.
- Multiple game levels.
- Move tracking and score calculation.
- Game sessions and checkpoints.
- Level completion and progress tracking.

### 👤 User Management

- User registration and login.
- Authentication-protected API endpoints.
- User-specific game sessions.
- Player profile management.
- Game progress tracking.

### 🏆 Progress and Rewards

- Leaderboard functionality.
- Achievement system.
- Stars and level progress.
- Hints and revive functionality where enabled.
- Reward and wallet functionality.
- Reward transaction tracking and validation.

### 🔐 Security

- Backend-side game validation.
- Authentication and authorization.
- Server-side reward verification.
- Reward idempotency protections.
- Environment-based configuration.
- Production security settings.
- HTTPS and secure-cookie support.

### 🐳 Deployment

- Dockerized backend.
- Dockerized frontend.
- PostgreSQL database.
- Nginx frontend and API proxy.
- Docker Compose configuration.
- Production Docker Compose configuration.
- Render Blueprint deployment configuration.
- Caddy reverse proxy configuration for supported self-hosted deployments.

---

## 🏗️ Technology Stack

### Frontend

- React
- TypeScript / JavaScript
- Vite
- Nginx

### Backend

- Python
- Django
- Django REST Framework
- Gunicorn

### Database

- PostgreSQL

### Infrastructure and DevOps

- Docker
- Docker Compose
- Caddy
- Git
- GitHub
- Render

---

## 📁 Project Structure

```text
apple-worm-adventure/
│
├── backend/
│   ├── config/
│   ├── core/
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── package-lock.json
│   ├── nginx.conf
│   ├── nginx.conf.template
│   └── Dockerfile
│
├── scripts/
│   ├── PREPARE-PRODUCTION.ps1
│   ├── VALIDATE-PRODUCTION.ps1
│   ├── RUN-ALL-TESTS.ps1
│   └── RUN-FINAL-PRODUCTION-VERIFICATION.ps1
│
├── caddy/
│   └── Caddyfile
│
├── docs/
│   ├── DEPLOYMENT.md
│   └── RENDER_DEPLOYMENT.md
│
├── docker-compose.yml
├── docker-compose.production.yml
├── render.yaml
├── .env.example
├── .env.production.example
├── .gitignore
├── README.md
└── TLS_DEPLOYMENT_GUIDE.md
```

*This structure highlights the main project components. Additional application files, migrations, tests, and configuration files are maintained in their respective directories.*

---

## ⚙️ Prerequisites

Install the following tools:

1. Git
2. Docker Desktop
3. Docker Compose
4. Node.js (version required by the frontend package)
5. Python (version required by backend dependencies)

Verify the installations:

```bash
git --version
docker --version
docker compose version
node --version
npm --version
python --version
```

---

## 🚀 Run Locally Using Docker

### Step 1: Clone the repository

```bash
git clone https://github.com/Aadit23042006/apple-worm-adventure.git
```

### Step 2: Navigate to the project directory

```bash
cd apple-worm-adventure
```

### Step 3: Configure environment variables

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

Review `.env` and configure the required local development values.

Never upload `.env` or production credentials to GitHub.

### Step 4: Start Docker Desktop

Ensure Docker Desktop is running.

### Step 5: Build and start the application

```bash
docker compose up -d --build
```

### Step 6: Check running containers

```bash
docker compose ps
```

### Step 7: Check backend logs

```bash
docker compose logs -f backend
```

### Step 8: Check frontend logs

```bash
docker compose logs -f frontend
```

### Step 9: Stop the application

```bash
docker compose down
```

---

## 🌐 Local Application Access

After successfully starting the local application:

| Component | URL |
|---|---|
| Frontend | http://127.0.0.1:5177/ |
| Backend API | http://127.0.0.1:8002/api/ |

These are documented local development addresses. Actual port mappings depend on the Docker Compose configuration.

---

## 🧪 Testing

The project includes scripts for source audits and production verification.

### Run the complete automated test suite

**Windows PowerShell:**

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force

& ".\scripts\RUN-ALL-TESTS.ps1"
```

### Run final production verification

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force

& ".\scripts\RUN-FINAL-PRODUCTION-VERIFICATION.ps1"
```

### Django application checks

Run inside the backend environment:

```bash
python manage.py check
```

### Django production security checks

```bash
python manage.py check --deploy
```

Automated tests should be executed in an appropriate test environment. A successful local test run does not independently prove that every external production service or integration is working.

---

## 🔒 Environment Variables and Security

The application uses environment variables for sensitive configuration.

Important configuration includes:

- Django secret key.
- PostgreSQL database credentials.
- Allowed hosts.
- CORS and CSRF trusted origins.
- Email and SMTP configuration.
- Rewarded-ad provider configuration, where applicable.
- Webhook signing secrets.
- HTTPS and secure-cookie settings.

Example configuration files:

```text
.env.example
.env.production.example
```

### Security Guidelines

- Never commit `.env` files.
- Never publish database passwords.
- Never expose Django secret keys.
- Never publish webhook signing secrets.
- Rotate credentials if accidentally exposed.
- Use HTTPS in production.
- Keep reward verification on the backend.
- Never hardcode production credentials in source code.

---

## ☁️ Production Deployment

The repository includes production deployment configurations for Docker Compose and Render.

### Prepare production environment

```powershell
.\scripts\PREPARE-PRODUCTION.ps1
```

### Validate production configuration

```powershell
.\scripts\VALIDATE-PRODUCTION.ps1
```

### Start production Docker deployment

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
```

### Check production containers

```bash
docker compose -f docker-compose.production.yml --env-file .env.production ps
```

Additional deployment documentation:

- `docs/DEPLOYMENT.md`
- `TLS_DEPLOYMENT_GUIDE.md`

---

## ☁️ Live Render Deployment

Apple Worm Adventure has separate frontend and backend services deployed on Render.

### Frontend

**Live URL:**

https://awa-frontend-1ikn.onrender.com/

The frontend is served through Nginx and proxies API requests to the backend.

### Backend

**Live URL:**

https://awa-backend-wfvo.onrender.com/

### API Health Check

Direct backend health endpoint:

https://awa-backend-wfvo.onrender.com/api/health/

Frontend-proxied health endpoint:

https://awa-frontend-1ikn.onrender.com/api/health/

### Render Configuration

The repository includes:

```text
render.yaml
```

The Blueprint defines the frontend, backend, and PostgreSQL resources.

Deployment documentation:

```text
docs/RENDER_DEPLOYMENT.md
```

### Production Deployment Verification

After deployment, verify:

- Backend service status.
- Frontend service status.
- Docker build logs.
- Nginx startup.
- Environment variable configuration.
- PostgreSQL connectivity.
- Database migration output.
- API health endpoint.
- Frontend-to-backend API proxy.
- Registration and login.
- Gameplay and progress persistence.

A live homepage or health endpoint alone does not establish that all application features have passed production testing.

---

## 📊 Production Readiness Checklist

| Area | Verification |
|---|---|
| Frontend Deployment | Live frontend availability |
| Backend Deployment | Live backend availability |
| API Health | Health endpoint response |
| Database | PostgreSQL connectivity |
| Database Migrations | Successful migration execution |
| Authentication | Registration and login tests |
| Gameplay | Level and game logic tests |
| Progress | Database persistence tests |
| Security | Django production security checks |
| Ad Integration | Actual provider verification, if configured |

Individual items should be marked complete only after their corresponding tests pass.

---

## 📢 Advertising Integration

The project contains an ad and reward-related architecture.

Real ad-provider integration requires a supported provider, an appropriately configured account, provider credentials, and any required approval.

Reward verification should be handled securely by the backend.

**Note:** The presence of ad-related application code does not by itself establish that real ad delivery or monetization is active.

---

## 🤝 Contributing

Contributions, suggestions, and improvements are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Run the relevant tests.
5. Commit your changes.
6. Submit a pull request.

Example:

```bash
git checkout -b feature/your-feature

git add .

git commit -m "Add: your feature"

git push origin feature/your-feature
```

---

## 📄 License

Add the project's applicable open-source license before distributing the source code.

---

## 👨‍💻 Project Information

**Project:** Apple Worm Adventure

**Short Name:** AWA

**GitHub Repository:**

https://github.com/Aadit23042006/apple-worm-adventure

**Live Application:**

https://awa-frontend-1ikn.onrender.com/

**Backend API:**

https://awa-backend-wfvo.onrender.com/

**Project Demonstration:**

[Watch the Full Project Video](https://drive.google.com/file/d/1HOFCVIMizAZD6oI4qD6mEp9XsG2OZnyd/view?usp=drive_link)

---

*Built with Python, Django REST Framework, React, PostgreSQL, Docker, and Render.*

**Apple Worm Adventure — Think Strategically. Move Smartly. Complete Every Level! 🍎**