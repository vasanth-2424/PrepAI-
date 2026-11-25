# PrepAI

AI-powered interview preparation platform. Upload a PDF resume, extract and analyze skills and projects, generate personalized technical interview questions, practice standard or adaptive voice/text mock interviews, and receive AI answer evaluations and final performance reports.

## Tech Stack

| Layer    | Technology                                    |
| -------- | --------------------------------------------- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS      |
| Backend  | Python, FastAPI, Uvicorn, SQLAlchemy, Alembic |
| PDF      | pypdf                                         |
| AI       | Groq API (OpenAI-compatible fallback)         |
| Database | PostgreSQL (Supabase in prod, Docker in dev)  |
| Auth     | JWT (`python-jose`) + Argon2 (`argon2-cffi`)  |

## Project Structure

```text
PrepAI/
├── frontend/
│   ├── vercel.json             # Vercel SPA rewrites for React Router
│   └── src/
│       ├── auth/               # AuthContext, ProtectedRoute, tokenStorage
│       ├── components/         # Layout, landing, resume, interview UI
│       ├── config/             # Environment variable config (VITE_API_BASE_URL)
│       ├── hooks/              # Web Speech TTS/STT hook
│       ├── pages/              # Landing, Login, Signup, Resume, Interview
│       └── services/           # API client
├── backend/
│   ├── alembic/                # Database migrations
│   ├── app/
│   │   ├── db/                 # SQLAlchemy engine, Base, ORM models
│   │   ├── models/             # Pydantic domain schemas
│   │   ├── routers/            # health, auth, users, resume, questions, interview
│   │   ├── schemas/            # Auth, user, interview schemas
│   │   ├── services/           # Parser, analyzer, LLM client, interview/evaluation
│   │   └── utils/              # Security & exception handlers
│   ├── tests/                  # pytest suite
│   ├── main.py                 # Uvicorn entrypoint (respects PORT, disables reload in prod)
│   └── Procfile                # Process command for PaaS platforms
├── docker-compose.yml          # Local PostgreSQL service for development
└── render.yaml                 # Render Blueprint for backend deployment
```

## Local Development

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+ (3.9+ supported locally)
- **PostgreSQL** (via Docker Compose or Supabase)
- **Groq API key** (or OpenAI-compatible API key)

### 1. Local Database (Docker Compose)

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Fill in DATABASE_URL, GROQ_API_KEY, JWT_SECRET_KEY
alembic upgrade head
python main.py
```

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

- App: `http://localhost:5173`
- Leave `VITE_API_BASE_URL` empty in local development so Vite proxies `/api` requests to `http://localhost:8000`.

## Environment Variables

### Backend (`backend/.env` locally, Render Dashboard in production)

| Variable                      | Required | Default / Dev Value                             | Production Notes                                                                  |
| ----------------------------- | -------- | ----------------------------------------------- | --------------------------------------------------------------------------------- |
| `APP_NAME`                    | No       | `PrepAI`                                        | Application display name                                                          |
| `APP_ENV`                     | Yes      | `development`                                   | Set to `production`                                                               |
| `DEBUG`                       | Yes      | `true`                                          | Set to `false` (disables FastAPI debug mode and Uvicorn reload)                   |
| `HOST`                        | No       | `0.0.0.0`                                       | Bind address                                                                      |
| `PORT`                        | Auto     | `8000`                                          | Injected automatically by Render                                                  |
| `CORS_ORIGINS`                | Yes      | `http://localhost:5173,http://127.0.0.1:5173`   | Comma-separated deployed frontend origins (e.g. `https://your-app.vercel.app`)    |
| `DATABASE_URL`                | Yes      | `postgresql+psycopg://prepai:prepai@localhost:5432/prepai` | Supabase PostgreSQL connection string (`postgresql://...` or `postgresql+psycopg://...`) |
| `JWT_SECRET_KEY`              | Yes      | `change-me-in-production`                       | Set a strong random secret in production                                          |
| `JWT_ALGORITHM`               | No       | `HS256`                                         | JWT signing algorithm                                                             |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | `60`                                            | Access token lifetime in minutes                                                  |
| `GROQ_API_KEY`                | Yes      | —                                               | Server-side Groq API key                                                          |
| `GROQ_MODEL`                  | No       | `openai/gpt-oss-120b`                           | Groq model ID                                                                     |
| `OPENAI_API_KEY`              | No       | *(empty)*                                       | Optional fallback; leave empty when using Groq                                    |
| `OPENAI_MODEL`                | No       | `gpt-4o-mini`                                   | Used only if `OPENAI_API_KEY` is set                                              |
| `OPENAI_BASE_URL`             | No       | `https://api.openai.com/v1`                     | Used only if `OPENAI_API_KEY` is set                                              |
| `LLM_MAX_RETRIES`             | No       | `2`                                             | Retries on invalid LLM JSON output                                                |
| `MAX_UPLOAD_SIZE_MB`          | No       | `5`                                             | Max PDF upload size in MB                                                         |

### Frontend (`frontend/.env` locally, Vercel Dashboard in production)

| Variable            | Required in Prod | Default / Dev Value | Production Notes                                                                  |
| ------------------- | ---------------- | ------------------- | --------------------------------------------------------------------------------- |
| `VITE_API_BASE_URL` | Yes              | *(empty)*           | Deployed Render backend URL with no trailing slash (e.g. `https://your-backend.onrender.com`) |

## Deployment (Supabase + Render + Vercel)

### 1. Database (Supabase PostgreSQL)

1. Ensure your Supabase project is active and copy the PostgreSQL connection string (URL-encode any special characters in the password).
2. Run database migrations before or during backend startup:
   ```bash
   cd backend
   alembic upgrade head
   ```

### 2. Backend (Render)

You can deploy using the included `render.yaml` Blueprint or configure a Render **Web Service** manually:

- **Root Directory:** `backend`
- **Runtime:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/api/v1/health`
- **Environment Variables:** Set `APP_ENV=production`, `DEBUG=false`, `DATABASE_URL`, `GROQ_API_KEY`, `GROQ_MODEL`, `JWT_SECRET_KEY`, and `CORS_ORIGINS` (update `CORS_ORIGINS` once your Vercel URL is known).

Verify the backend deployment by opening `https://<your-render-service>.onrender.com/api/v1/health`.

### 3. Frontend (Vercel)

Create a new Vercel project importing this repository:

- **Root Directory:** `frontend`
- **Framework Preset:** Vite
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Environment Variable:** Set `VITE_API_BASE_URL` to your Render backend URL (no trailing slash).

`frontend/vercel.json` is already configured with a rewrite rule so React `BrowserRouter` paths (`/login`, `/signup`, `/resume`, `/interview`) resolve cleanly on refresh.

### 4. Finalize CORS & Verify

1. Copy the deployed Vercel URL (e.g. `https://your-app.vercel.app`).
2. Set `CORS_ORIGINS` on Render to that exact URL (or comma-separated URLs if you also have a custom domain), then redeploy/restart the Render service.
3. Verify in production over HTTPS:
   - Sign up / log in
   - Upload and analyze a text-based PDF resume
   - Generate personalized questions and run a voice/text mock interview

## Testing

### Backend

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm run lint
npm run build
```

## License

Private project — all rights reserved.
