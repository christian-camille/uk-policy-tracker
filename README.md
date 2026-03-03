# GOV Tracker

A full-stack application that tracks UK government policy topics by linking **GOV.UK publications** to **parliamentary activity** — surfacing changes, timelines, and key stakeholders in one place.

## What It Does

GOV Tracker lets you create **topic watchlists** (e.g. "AI Regulation", "Energy Policy") and automatically:

- **Ingests GOV.UK content** — policy papers, consultations, guidance, and news stories matching your topics
- **Pulls parliamentary data** — bills, written questions, divisions (votes), and MP/Lord profiles from the UK Parliament APIs
- **Extracts entities** — uses spaCy NLP to identify people, organisations, and legislation mentioned in documents
- **Builds a knowledge graph** — connects content items to topics, organisations, people, and bills through a relational graph projection
- **Presents unified timelines** — shows all activity for a topic in chronological order, colour-coded by event type
- **Surfaces key actors** — ranks the people most connected to each topic

### Use Cases

- **Policy researchers** tracking legislative progress across multiple topics
- **Journalists** monitoring government activity and identifying key stakeholders
- **Advocacy organisations** keeping up with relevant publications and parliamentary questions
- **Civil servants** maintaining awareness of cross-departmental policy developments

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Next.js   │────▶│   FastAPI    │────▶│  PostgreSQL  │
│  Frontend   │     │   Backend   │     │  (3 schemas) │
│  port 3000  │     │  port 8000  │     │              │
└─────────────┘     └──────┬──────┘     │  bronze (raw)│
                           │            │  silver (norm)│
                    ┌──────┴──────┐     │  gold (graph)│
                    │    Celery   │────▶│              │
                    │   Workers   │     └──────────────┘
                    │  + Beat     │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │    Redis    │
                    │   (broker)  │
                    └─────────────┘
```

### Data Pipeline (Bronze → Silver → Gold)

| Layer | Purpose | Contents |
|-------|---------|----------|
| **Bronze** | Raw API responses | JSON blobs from GOV.UK and Parliament APIs |
| **Silver** | Normalised entities | Topics, ContentItems, Persons, Bills, Questions, Divisions, Organisations, ActivityEvents |
| **Gold** | Knowledge graph | GraphNodes and GraphEdges linking all entities |

### Daily Pipeline

Celery Beat triggers a daily refresh at 06:00 UTC that runs:

1. **Ingest** — fetch new data from GOV.UK and Parliament APIs for all watchlist topics (parallel)
2. **Events** — scan silver tables and create timeline ActivityEvent records
3. **Match** — run spaCy NER to link content items to people, bills, and organisations
4. **Graph** — rebuild the gold-layer graph projection from silver data

On-demand refresh is also available per-topic via the API.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, TanStack React Query |
| Database | PostgreSQL 16 with `pg_trgm` for fuzzy matching |
| Task Queue | Celery 5.4 with Redis broker |
| NLP | spaCy 3.8 (`en_core_web_sm`) with custom EntityRuler patterns |
| HTTP Client | httpx (async + sync) |
| Deployment | Docker Compose |

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- (Optional) Python 3.12+ and Node.js 20+ for local development without Docker

### Quick Start

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd gov-tracker
   ```

2. **Create your environment file**

   ```bash
   cp .env.example .env
   ```

   The defaults work out of the box with Docker Compose. Edit `.env` if you need to change database credentials or API URLs.

3. **Start all services**

   ```bash
   docker compose up --build
   ```

   This starts PostgreSQL, Redis, the API server, Celery worker + beat scheduler, runs database migrations, and launches the frontend.

4. **Open the app**

   - Frontend: [http://localhost:3000](http://localhost:3000)
   - API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

5. **Create your first topic**

   Click "Add Topic" on the home page, enter a label (e.g. "AI Regulation") and comma-separated search queries (e.g. "artificial intelligence, AI regulation, machine learning"). Hit save, then click the refresh button to trigger the first data ingestion.

### Local Development (without Docker)

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
python -m spacy download en_core_web_sm

# Start the API server
uvicorn app.main:app --reload --port 8000

# Start the Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2

# Start the Celery beat scheduler (separate terminal)
celery -A app.tasks.celery_app beat --loglevel=info
```

Requires PostgreSQL and Redis running locally. Update `DATABASE_URL`, `DATABASE_URL_SYNC`, and `REDIS_URL` in your `.env` accordingly.

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api/*` requests to the backend via Next.js rewrites (configured in `next.config.js`).

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check (DB, Redis, data freshness) |
| `GET` | `/topics` | List all watchlist topics |
| `POST` | `/topics` | Create a new topic |
| `GET` | `/topics/{id}` | Get a single topic |
| `DELETE` | `/topics/{id}` | Delete a topic |
| `GET` | `/topics/{id}/timeline` | Paginated activity timeline (supports `?since=` and `?limit=`) |
| `POST` | `/topics/{id}/refresh` | Trigger on-demand data refresh (returns 202) |
| `GET` | `/topics/{id}/actors` | Key people connected to this topic |
| `GET` | `/entities/{node_id}` | Entity detail with graph connections |

Interactive API documentation is available at `/docs` (Swagger UI) when the backend is running.

## Data Sources

| Source | API | Data |
|--------|-----|------|
| [GOV.UK](https://www.gov.uk) | Search API, Content API | Policy papers, consultations, guidance, news stories, organisations |
| [UK Parliament](https://parliament.uk) | Members API | MP and Lord profiles, party, constituency |
| | Bills API | Bill progress, stages, titles |
| | Written Questions API | Questions tabled by members, answers |
| | Commons Votes API | Division results, aye/no counts |

## Running Tests

```bash
cd backend
pip install -e ".[dev]"
python -m pytest tests/ -v
```

The test suite uses **SQLite in-memory** databases with PostgreSQL type adapters, so no external services are needed. Tests cover:

- **API endpoints** — full CRUD for topics, timeline queries, health checks
- **API clients** — GOV.UK and Parliament client request/response handling with mocked HTTP
- **Ingestion service** — bronze/silver upserts, idempotency, organisation extraction, activity events
- **Graph service** — async entity detail queries and sync graph projection builder
- **Celery tasks** — task orchestration with mocked dependencies
- **Schemas** — Pydantic model validation, slug generation
- **NLP extractor** — entity extraction, deduplication, custom patterns (requires Python ≤3.13 / runs in Docker)

## Project Structure

```
gov-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application factory
│   │   ├── config.py            # Pydantic settings
│   │   ├── database.py          # SQLAlchemy engines (async + sync)
│   │   ├── models/
│   │   │   ├── bronze.py        # Raw API response storage
│   │   │   ├── silver.py        # Normalised entity models
│   │   │   └── gold.py          # Graph node/edge models
│   │   ├── routers/
│   │   │   ├── health.py        # Health check endpoint
│   │   │   ├── topics.py        # Topic CRUD + timeline + refresh
│   │   │   └── entities.py      # Entity detail endpoint
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── govuk.py         # GOV.UK API client (async + sync)
│   │   │   ├── parliament.py    # Parliament API client (async + sync)
│   │   │   ├── ingest.py        # Data ingestion and upsert logic
│   │   │   ├── matching.py      # NLP entity matching and resolution
│   │   │   └── graph.py         # Graph queries and projection builder
│   │   ├── nlp/
│   │   │   └── extractor.py     # spaCy NER wrapper with EntityRuler
│   │   └── tasks/
│   │       ├── celery_app.py    # Celery configuration and beat schedule
│   │       ├── ingest.py        # Individual Celery tasks
│   │       └── pipeline.py      # Task orchestration (chains + groups)
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Test suite
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages (App Router)
│   │   ├── components/          # React components
│   │   ├── hooks/               # React Query hooks
│   │   └── lib/                 # API client and types
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `govtracker` | PostgreSQL database name |
| `POSTGRES_USER` | `govtracker` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `govtracker` | PostgreSQL password |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async database connection string |
| `DATABASE_URL_SYNC` | `postgresql+psycopg2://...` | Sync database connection string (Celery) |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `SPACY_MODEL` | `en_core_web_sm` | spaCy model for NER |
| `API_PROXY_TARGET` | `http://localhost:8000` | Backend URL for frontend proxy |

## License

This project is provided as-is for educational and research purposes.
