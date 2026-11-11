
# 🍎 Apple Worm Adventure

**Apple Worm Adventure (AWA)** is a full-stack, browser-based puzzle game in which players control a worm, collect apples, navigate obstacles, and solve levels using strategic movement.

The project is built with a React frontend, Django REST API backend, and PostgreSQL database. Docker Compose simplifies local development and deployment.

---

## 🔗 Project Links

| Resource | Link |
|---|---|
| GitHub Repository | [Apple Worm Adventure](https://github.com/Aadit23042006/apple-worm-adventure) |
| Project Demonstration Video | [Watch Project Demo](https://drive.google.com/file/d/1HOFCVIMizAZD6oI4qD6mEp9XsG2OZnyd/view?usp=drive_link) |
| Local Application | [Open Apple Worm Adventure](http://127.0.0.1:5177/) |

---

## 📌 Project Overview

| Detail | Description |
|---|---|
| Project Name | Apple Worm Adventure |
| Short Name | AWA |
| Frontend | React + Vite |
| Backend | Python + Django REST Framework |
| Database | PostgreSQL |
| Deployment | Docker / Docker Compose / Render |
| Web Server | Nginx |
| Authentication | Django authentication and API authentication |
| Game Type | Logic-based puzzle game |

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
- User game sessions.
- Player progress tracking.

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
- Secure cookies and HTTPS support.

### 🐳 Deployment

- Dockerized backend.
- Dockerized frontend.
- PostgreSQL service.
- Nginx frontend and API proxy.
- Production Docker Compose configuration.
- Caddy reverse proxy and automatic HTTPS support.

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
- Git and GitHub
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

*The structure above highlights the main project components. Additional application files, migrations, tests, and configuration files are maintained in their respective directories.*

---

## ⚙️ Prerequisites

Install the following tools:

1. Git
2. Docker Desktop
3. Docker Compose
4. Node.js (version required by the frontend package)
5. Python (version required by backend dependencies)

Verify installation:

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

Navigate into the repository:

```bash
cd apple-worm-adventure
```

### Step 2: Configure environment variables

Copy the example environment file.

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

Review `.env` and configure the local development values.

Never upload `.env` to GitHub.

### Step 3: Start Docker Desktop

Make sure Docker Desktop is running.

### Step 4: Build and start the application

```bash
docker compose up -d --build
```

### Step 5: Check running containers

```bash
docker compose ps
```

### Step 6: Check backend logs

```bash
docker compose logs -f backend
```

### Step 7: Check frontend logs

```bash
docker compose logs -f frontend
```

### Step 8: Stop the application

```bash
docker compose down
```

---

## 🌐 Local Application Access

The frontend is accessible at:

**http://127.0.0.1:5177/**

The backend API is available through the configured API endpoint:

```text
http://127.0.0.1:8002/api/
```

**Note:** These are the documented local development addresses. They work on the computer where the application is running and are not public deployment URLs.

Actual port mappings depend on the Docker Compose configuration.

---

## 🧪 Testing

The project includes scripts for source audits and production verification.

### Run the complete automated test suite

**Windows PowerShell:**

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force

& ".\scripts\RUN-ALL-TESTS.ps1"
```

### Run only final production verification

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force

& ".\scripts\RUN-FINAL-PRODUCTION-VERIFICATION.ps1"
```

### Django checks

Run inside the backend environment:

```bash
python manage.py check
```

Production security check:

```bash
python manage.py check --deploy
```

A successful automated test run does not by itself establish that external production services, HTTPS, email delivery, or real ad-provider callbacks have been verified.

---

## 🔒 Environment Variables and Security

The project uses environment variables for sensitive configuration.

Important configuration includes:

- Django secret key.
- Database credentials.
- Allowed hosts.
- CORS and CSRF trusted origins.
- Email / SMTP credentials.
- Rewarded-ad provider configuration.
- Webhook signing secret.
- HTTPS and secure-cookie settings.

Example files:

```text
.env.example
.env.production.example
```

Copy the appropriate example file and configure real values locally or in your deployment provider.

### Security Rules

- Never commit `.env`.
- Never commit `.env.production`.
- Never publish database passwords.
- Never publish Django secret keys.
- Never expose webhook signing secrets.
- Rotate credentials if they are accidentally exposed.
- Use HTTPS for production.
- Keep reward verification on the backend.
- Do not store production credentials in source code.

---

## ☁️ Production Deployment

The project includes a production Docker Compose configuration.

Before deployment:

1. Configure production environment variables.
2. Set the actual public hostname.
3. Configure PostgreSQL credentials.
4. Configure SMTP credentials.
5. Configure a supported real rewarded-ad provider and signed callback verification if rewarded ads are enabled.
6. Configure DNS.
7. Configure HTTPS.
8. Run production validation.
9. Deploy and verify the application.

### Prepare production environment

```powershell
.\scripts\PREPARE-PRODUCTION.ps1
```

### Validate production configuration

```powershell
.\scripts\VALIDATE-PRODUCTION.ps1
```

### Start production deployment

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
```

### Check production containers

```bash
docker compose -f docker-compose.production.yml --env-file .env.production ps
```

See the following documentation for additional deployment instructions:

- `docs/DEPLOYMENT.md`
- `TLS_DEPLOYMENT_GUIDE.md`

### Render Deployment

A Render Blueprint is included at `render.yaml`, with detailed instructions in:

```text
docs/RENDER_DEPLOYMENT.md
```

The blueprint does not contain production secrets and does not constitute proof of a completed live deployment.

Configure the required environment variables in Render and run the documented smoke tests after deployment.

---

## 📊 Production Verification

The final production verification covers:

| Verification | Requirement |
|---|---|
| Django production security | Django deployment security checks pass |
| Public domain | Public hostname resolves correctly |
| HTTPS certificate | Valid certificate is served |
| Secure browser cookies | Secure cookie flags are verified over HTTPS |
| Production deployment | Services start and application responds successfully |

These checks require a real deployment environment and cannot all be completed through local source-code tests.

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

Add the project's applicable license here before distributing the source code.

---

## 👨‍💻 Project Information

**Project:** Apple Worm Adventure

**Short Name:** AWA

**GitHub Repository:**  
https://github.com/Aadit23042006/apple-worm-adventure

**Project Demonstration:**  
[Watch the Full Project Video](https://drive.google.com/file/d/1HOFCVIMizAZD6oI4qD6mEp9XsG2OZnyd/view?usp=drive_link)

---

*Built with Python, Django, React, PostgreSQL, and Docker.*
