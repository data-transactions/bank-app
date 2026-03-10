# NexaBank — Fintech Online Banking MVP

A production-architectured, containerized fintech banking web app built with **FastAPI**, **MySQL**, **Alembic**, **Cloudinary**, and a **Tailwind CSS CLI + Vanilla JS** frontend.

## 🚀 Structure

The project follows a clean separation of concerns:
- `frontend/`: Static assets, UI components, and Tailwind CLI configuration.
- `backend/`: FastAPI application, database migrations, and Docker configurations.

## 🚀 Quick Start

### 1. Set up environment variables
```bash
cp backend/.env.example backend/.env
# Edit backend/.env and fill in your Cloudinary credentials + a strong SECRET_KEY
```

### 2. Install & Build Frontend
```bash
cd frontend
npm install
npm run build
```

### 3. Start Docker services (from root)
```bash
docker compose up --build -d
```

### 4. Run database migrations
```bash
docker compose exec backend alembic upgrade head
```

### 5. Access the application
| Service | URL |
|---|---|
| **App** | http://localhost:8000 |
| **API docs** | http://localhost:8000/docs |
| **phpMyAdmin** | http://localhost:8080 |

---

## 📁 Project Structure

```
bank-app/
├── docker-compose.yml            # Root orchestrator
├── frontend/                     # FRONTED SEPARATION
│   ├── index.html
│   ├── login/index.html
│   ├── signup/index.html
│   ├── dashboard/index.html
│   ├── assets/
│   │   ├── css/                  # input.css, output.css, main.css
│   │   └── js/                   # api.js, auth.js, ui.js
│   └── package.json              # Tailwind CLI build scripts
└── backend/                      # BACKEND SEPARATION
    ├── app/                      # FastAPI source
    ├── migrations/               # Alembic migrations
    ├── docker/                   # Dockerfile & requirements.txt
    ├── alembic.ini
    └── .env
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, Tailwind CSS **CLI (v4)**, Vanilla JS |
| Backend | FastAPI (Python 3.12) |
| Database | MySQL 8 |
| Migrations | Alembic |
| Auth | JWT + bcrypt |
| Containerization | Docker + Docker Compose |
