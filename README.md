# GOV Tracker

GOV Tracker links GOV.UK publications to parliamentary activity so you can follow a policy topic in one place.

The app lets you:

- Create and manage tracked topics
- Refresh data on demand from GOV.UK and Parliament APIs
- Browse a topic timeline of activity events
- Inspect key actors and connected entities
- Store ingested data in PostgreSQL

## Stack

The repository contains three runtime services and one optional utility service:

- `postgres`: PostgreSQL 16 database
- `api`: FastAPI application and migration runner
- `frontend`: Next.js application
- `migrate`: optional one-off Alembic migration service

Topic refresh is synchronous. When you click `Refresh Data`, the API process runs discovery, ingest, event creation, entity matching, and graph rebuild directly.

## Requirements

For the default Docker workflow:

- Docker Desktop or Docker Engine with `docker compose`

For development without Docker:

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+

## Quick Start

1. Create the environment file.

```powershell
Copy-Item .env.example .env
```

2. Build and start the stack.

```powershell
docker compose up --build
```

3. Open the application.

- App: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health endpoint: http://localhost:8000/api/health

4. Add a topic from the home page.

5. Open the topic and click `Refresh Data` to fetch the latest GOV.UK and Parliament activity.

## How Startup Works

- `postgres` starts first and exposes the database on port `5432`
- `api` waits for Postgres, runs `alembic upgrade head`, then starts Uvicorn on port `8000`
- `frontend` waits for a healthy API, then starts Next.js on port `3000`

Database migrations are applied automatically on API startup, including upgrades for existing database volumes.

## Common Commands

Start in the background:

```powershell
docker compose up --build -d
```

Stop the stack:

```powershell
docker compose down
```

Stop the stack and delete database data:

```powershell
docker compose down -v
```

Run migrations manually:

```powershell
docker compose run --rm migrate
```

Rebuild just one service:

```powershell
docker compose build api
docker compose build frontend
```

View logs:

```powershell
docker compose logs -f api
docker compose logs -f frontend
docker compose logs -f postgres
```

## Environment

The defaults in [.env.example](.env.example) are suitable for the Docker setup in this repository.

Important variables:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `DATABASE_URL_SYNC`
- `CORS_ALLOWED_ORIGINS`
- `API_PROXY_TARGET`
- `SPACY_MODEL`

External API base URLs are configurable too:

- `GOVUK_BASE_URL`
- `PARLIAMENT_MEMBERS_API_URL`
- `PARLIAMENT_BILLS_API_URL`
- `PARLIAMENT_QUESTIONS_API_URL`
- `PARLIAMENT_DIVISIONS_API_URL`

## Development Without Docker

You will need PostgreSQL running separately and a populated `.env` file.

Backend setup:

```powershell
cd backend
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Frontend setup:

```powershell
cd frontend
npm install
npm run dev
```

## Project Layout

- [backend](backend): FastAPI app, Alembic migrations, models, services, tests
- [frontend](frontend): Next.js app, BFF proxy route, topic and entity pages
- [docker-compose.yml](docker-compose.yml): container orchestration
- [.env.example](.env.example): default environment configuration
- [Project Specification.md](Project%20Specification.md): product and data-model notes

## Data Model Notes

The backend uses a layered schema approach:

- `bronze`: raw source payloads
- `silver`: normalized relational entities
- `gold`: graph projection nodes and edges

Tracked topics are global within the running instance. There is no account or ownership layer.

## Testing

Backend tests:

```powershell
cd backend
pytest -q
```

Frontend production build:

```powershell
cd frontend
npm run build
```

## Troubleshooting

If the first build feels slow:

- The backend image downloads the spaCy `en_core_web_sm` model during the build.

If the frontend starts but the API is unavailable:

- Check `docker compose logs api`
- Confirm the API health endpoint responds at http://localhost:8000/api/health

If you want a completely clean database:

```powershell
docker compose down -v
docker compose up --build
```

If ports are already in use:

- `5432` is used by PostgreSQL
- `8000` is used by the API
- `3000` is used by the frontend
