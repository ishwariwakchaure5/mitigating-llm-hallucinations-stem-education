# VERA — Verification Engine for Research and Academia

AI-powered claim verification system that checks whether statements are supported by an uploaded knowledge base using semantic NLI, symbolic math, and visual diagram analysis.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.7-DC244C)](https://qdrant.tech/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Table of Contents

1. [What is VERA](#1-what-is-vera)
2. [How It Works](#2-how-it-works)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Prerequisites](#5-prerequisites)
6. [Installation](#6-installation)
7. [Running the Project](#7-running-the-project)
8. [Running Tests](#8-running-tests)
9. [API Reference](#9-api-reference)
10. [Project Structure](#10-project-structure)
11. [Model Information](#11-model-information)
12. [Configuration](#12-configuration)
13. [Known Limitations](#13-known-limitations)
14. [Contributing](#14-contributing)
15. [License](#15-license)

---

## 1. What is VERA

VERA (Verification Engine for Research and Academia) is an AI-assisted fact-checking platform built for academic and research workflows. You upload PDF documents into a **knowledge base**. Each document is parsed, chunked, and indexed for text similarity, LaTeX equations, and diagram images. You then submit a **claim**—a single sentence or a full paragraph—and VERA returns:

- A **verdict**: `correct`, `wrong`, `mixed`, or `uncertain`
- A **confidence score** (0–1)
- **Evidence citations** pointing to the most relevant source chunks, equations, or diagrams

**Use cases**

- Academic fact-checking against lecture notes or papers
- Student self-assessment (“Is my summary accurate?”)
- Research verification before publication
- Textbook Q&A against uploaded course material

---

## 2. How It Works

VERA runs three independent verification paths on each atomic **claim unit** (sentence or equation), then fuses the results.

### Path A — Semantic (NLI)

Documents are split into overlapping chunks and embedded with **nomic-ai/nomic-embed-text-v1** (768-dim). The claim is embedded and **top-k** similar chunks are retrieved from **Qdrant**. Each retrieved chunk is scored with **cross-encoder/nli-deberta-v3-small** for entailment vs. contradiction. Cosine similarity and NLI scores are blended (70% NLI / 30% cosine). Thresholds: entailment > 0.45 → supported; contradiction > 0.60 → contradicted.

### Path B — Symbolic Math

LaTeX equations in documents are extracted from `$...$` and `$$...$$` delimiters, parsed with **latex2sympy2** (with **SymPy** `sympify` fallback), and stored in a **NetworkX** relationship graph per knowledge base. Claims containing math are parsed the same way and compared algebraically: exact match, variable substitution, or contradiction detection.

### Path C — Visual / Diagram

Diagram images extracted from PDFs are embedded with **CLIP ViT-B/32** (`openai/clip-vit-base-patch32`). Claim text is encoded with CLIP’s text encoder. Cosine similarity between text and image embeddings in Qdrant identifies diagram relevance for visual claims.

### Fusion and multi-sentence claims

**Dempster–Shafer fusion** (`DSFusion`) combines belief masses from all three paths into a per-unit verdict and confidence.

For paragraphs, `ClaimDecomposer` splits the text into units. Each unit is verified independently. A **weighted-confidence voting** scheme aggregates unit verdicts into an overall result (`correct` / `wrong` / `mixed` / `uncertain`).

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Next.js Frontend                   │
│         (Upload · Knowledge Base · Verify UI)        │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / REST
┌──────────────────────▼──────────────────────────────┐
│                 FastAPI Backend                       │
│   /auth  /knowledge-bases  /documents  /verify       │
└────┬──────────────┬───────────────────┬─────────────┘
     │              │                   │
┌────▼────┐  ┌──────▼──────┐  ┌────────▼────────┐
│PostgreSQL│  │Celery Worker│  │  Qdrant Vector  │
│  (users  │  │  (document  │  │   DB (text +    │
│   docs   │  │ processing  │  │  visual embeds) │
│   KBs)   │  │ + indexing) │  └─────────────────┘
└─────────┘  └──────┬──────┘
                    │
             ┌──────▼──────────────────────┐
             │       ML Model Layer         │
             │  nomic-embed-text (text)     │
             │  CLIP ViT-B/32 (visual)      │
             │  nli-deberta-v3-small (NLI)  │
             │  SymPy + NetworkX (math)     │
             └─────────────────────────────┘
```

---

## 4. Tech Stack

### Backend

| Library | Purpose |
|---------|---------|
| **FastAPI** | Async REST API |
| **SQLAlchemy + asyncpg** | Async ORM and PostgreSQL driver |
| **Alembic** | Database migrations |
| **Celery + Redis** | Async task queue for document processing |
| **Qdrant** | Vector database for semantic and visual search |
| **sentence-transformers** | nomic-embed-text and NLI cross-encoder |
| **transformers + torch** | CLIP visual embeddings |
| **PyMuPDF (fitz)** | PDF parsing and image extraction |
| **SymPy** | Symbolic math verification |
| **NetworkX** | Equation relationship graph |
| **Dempster–Shafer** (`DSFusion`) | Belief fusion across three paths |
| **python-jose + passlib/bcrypt** | JWT authentication |

### Frontend

| Library | Purpose |
|---------|---------|
| **Next.js 14** (App Router) | React framework and routing |
| **TypeScript** | Type-safe UI code |
| **Tailwind CSS** | Utility-first styling |
| **shadcn/ui** | Accessible UI primitives (Radix) |
| **Framer Motion** | Verdict animations and confidence bars |
| **Lucide React** | Icons |
| **TanStack Query** | Server state and caching |
| **Zustand** | Client auth state |
| **Axios** | API client with JWT interceptor |

### Infrastructure

| Service | Version |
|---------|---------|
| PostgreSQL | 15 (Alpine) |
| Redis | 7 (Alpine) |
| Qdrant | 1.7.4 |
| Docker Compose | 3.8 |

---

## 5. Prerequisites

| Requirement | Version / notes |
|-------------|-----------------|
| **Python** | 3.11 or 3.12 (**not** 3.13 — see limitations) |
| **Node.js** | 18+ |
| **Docker Desktop** | For PostgreSQL, Redis, Qdrant |
| **Git** | Clone and contribute |
| **Tesseract OCR** | Fallback for scanned PDFs ([install guide](https://github.com/tesseract-ocr/tesseract)) |
| **RAM** | 8 GB minimum; **16 GB** recommended for comfortable multi-model loading |

**Windows note:** Celery’s default `prefork` pool does not work on Windows. Always start the worker with `--pool=solo` (see [Running the Project](#7-running-the-project)).

**Python 3.13 note:** `latex2sympy2` depends on tooling that breaks on 3.13. VERA falls back to SymPy `sympify` for many equations, but 3.13 is not officially tested. Use **3.11 or 3.12**.

---

## 6. Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/vera.git
cd vera
```

### 2. Create and activate a virtual environment

```bash
cd backend
python -m venv venv
```

**Windows:**

```bash
venv\Scripts\activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install frontend dependencies

```bash
cd ../frontend
npm install
```

### 5. Set up environment variables

```bash
cd ../backend
cp .env.example .env
```

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Edit `backend/.env` and set at minimum:

- `VERA_SECRET_KEY` — paste the generated 64-character hex string
- `VERA_DATABASE_URL` — must match your Postgres credentials (see [Configuration](#12-configuration))

Copy `frontend/.env.example` to `frontend/.env.local` for the UI:

```bash
cd ../frontend
cp .env.example .env.local
```

> **Note:** The running backend loads settings from `backend/.env` using the `VERA_` prefix (see `backend/app/config.py`). Map values from `.env.example` accordingly—for example `DATABASE_URL` → `VERA_DATABASE_URL`, `REDIS_URL` → `VERA_REDIS_URL`.

### 6. Start Docker services

```bash
cd ..
docker compose up -d
docker compose ps
```

All three services (`postgres`, `redis`, `qdrant`) should report healthy.

### 7. Run database migrations

```bash
cd backend
alembic upgrade head
```

---

## 7. Running the Project

Start **four terminals** from the `vera/` root (with the backend venv activated in terminals 2–4).

**Terminal 1 — Frontend**

```bash
cd frontend
npm run dev
```

**Terminal 2 — API**

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 — Celery worker**

```bash
cd backend
celery -A app.tasks worker --loglevel=info --pool=solo
```

> On **macOS/Linux** you may omit `--pool=solo` and use the default prefork pool for better concurrency.

**Terminal 4 — (optional) watch logs**

```bash
docker compose logs -f
```

### First-run model downloads

Models download automatically from Hugging Face on first use and cache under `~/.cache/huggingface`:

| Trigger | Model | Approx. size |
|---------|-------|--------------|
| First document upload / indexing | `nomic-ai/nomic-embed-text-v1` | ~500 MB |
| First PDF with diagrams | `openai/clip-vit-base-patch32` | ~600 MB |
| First verification request | `cross-encoder/nli-deberta-v3-small` | ~500 MB |

### Access URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Web UI | http://localhost:3000 |

---

## 8. Running Tests

With the API, Celery worker, and Docker stack running:

```bash
cd vera
python tests/vera_pipeline_test.py
```

The pipeline test:

1. Registers (or logs in) a test user
2. Creates a knowledge base
3. Uploads `tests/vera_test_document.pdf`
4. Polls `/api/v1/documents/{id}/status` until `ready`
5. Asserts chunk, equation, and diagram counts on the KB
6. Runs **8 verification claims** (6 single-sentence + 2 multi-sentence mixed)
7. Deletes the knowledge base
8. Prints a pass/fail summary

**Expected output (representative):**

```
chunks:    56+   PASS
equations: 16+   PASS
diagrams:  3     PASS
...
Verdicts:  8/8 matched expected
OVERALL: PASS
```

Exact counts depend on PDF parsing; chunk count should exceed 50, equations above 15, and diagrams equal 3 for the bundled physics test PDF.

---

## 9. API Reference

All authenticated routes require header: `Authorization: Bearer <token>`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login, returns JWT |
| `GET` | `/api/v1/auth/me` | Current user profile |
| `GET` | `/api/v1/knowledge-bases/` | List knowledge bases |
| `POST` | `/api/v1/knowledge-bases/` | Create knowledge base |
| `GET` | `/api/v1/knowledge-bases/{id}` | Get KB with indexing stats |
| `DELETE` | `/api/v1/knowledge-bases/{id}` | Delete KB and vectors |
| `POST` | `/api/v1/knowledge-bases/{id}/upload` | Upload PDF (multipart) |
| `GET` | `/api/v1/documents/{id}/status` | Poll processing status |
| `POST` | `/api/v1/verify/{kb_id}` | Submit claim for verification |
| `GET` | `/api/v1/verify/{kb_id}/history` | Verification history |
| `GET` | `/health` | Health check |

### Example: verify a claim

**Request**

```http
POST /api/v1/verify/{kb_id}
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

```json
{
  "claim_text": "Newton's second law states that F = ma, where F is net force, m is mass, and a is acceleration"
}
```

**Response** `201 Created`

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "kb_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "claim_text": "Newton's second law states that F = ma, where F is net force, m is mass, and a is acceleration",
  "verdict": "correct",
  "confidence": 0.87,
  "conflict_score": 0.12,
  "path_a_score": 0.81,
  "path_b_score": 0.99,
  "path_c_score": 0.42,
  "explanation": "1/1 claims supported by the knowledge base.",
  "units": [
    {
      "unit_id": "u1",
      "text": "Newton's second law states that F = ma...",
      "unit_type": "text",
      "verdict": "correct",
      "confidence": 0.87,
      "path_a_score": 0.81,
      "path_b_score": 0.99,
      "path_c_score": 0.42,
      "evidence": [
        {
          "chunk_id": "c-12",
          "text": "Newton's second law: the net force on an object equals mass times acceleration, F = ma.",
          "page_number": 2,
          "score": 0.91
        }
      ]
    }
  ],
  "evidence": [
    {
      "chunk_id": "c-12",
      "text": "Newton's second law: the net force on an object equals mass times acceleration, F = ma.",
      "page_number": 2,
      "score": 0.91
    }
  ],
  "created_at": "2026-05-23T14:30:00Z"
}
```

---

## 10. Project Structure

```
vera/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── knowledge_base.py
│   │   │   ├── documents.py
│   │   │   └── verify.py
│   │   ├── services/
│   │   │   ├── document_parser.py
│   │   │   ├── chunker.py
│   │   │   ├── embedder.py
│   │   │   ├── equation_store.py
│   │   │   ├── visual_store.py
│   │   │   ├── semantic_verifier.py
│   │   │   ├── symbolic_verifier.py
│   │   │   ├── visual_verifier.py
│   │   │   ├── claim_decomposer.py
│   │   │   └── fusion.py
│   │   ├── models/              # SQLAlchemy ORM
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── tasks/
│   │   │   ├── __init__.py      # Celery app
│   │   │   ├── processing.py
│   │   │   └── dispatch.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env                     # git-ignored
│   └── uploads/                 # git-ignored runtime storage
├── frontend/
│   ├── app/                     # Next.js App Router
│   │   ├── (auth)/login/
│   │   ├── (auth)/register/
│   │   ├── dashboard/
│   │   └── kb/[id]/
│   ├── components/
│   │   ├── ui/                  # shadcn components
│   │   ├── upload/
│   │   ├── verify/
│   │   ├── kb/
│   │   └── layout/
│   ├── lib/
│   ├── hooks/
│   ├── store/
│   ├── .env.example
│   ├── .env.local               # git-ignored
│   └── node_modules/            # git-ignored
├── tests/
│   ├── vera_pipeline_test.py
│   ├── vera_test_document.pdf
│   └── vera_review_document.pdf
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 11. Model Information

| Model | Size | Purpose | Source |
|-------|------|---------|--------|
| `nomic-ai/nomic-embed-text-v1` | ~500 MB | Text embedding (dim=768) | Hugging Face |
| `cross-encoder/nli-deberta-v3-small` | ~500 MB | NLI entailment / contradiction | Hugging Face |
| `openai/clip-vit-base-patch32` | ~600 MB | Visual + text embedding (dim=512) | Hugging Face |

**Total first-run download:** ~1.6 GB  
**Cache location:** `~/.cache/huggingface` (not committed to git)  
**Hardware:** All inference runs on **CPU** — no GPU required

**Estimated inference times** (Ryzen 7 class CPU):

| Stage | Time |
|-------|------|
| Text embedding | ~0.5 s per chunk |
| NLI scoring | ~2–4 s per claim |
| CLIP encoding | ~1–2 s per image |

---

## 12. Configuration

### Backend (`backend/.env`)

The application reads variables with the **`VERA_`** prefix via Pydantic Settings (`backend/app/config.py`). Copy `backend/.env.example` and set values below.

#### App

| Variable | Description | Default |
|----------|-------------|---------|
| `VERA_SECRET_KEY` | JWT signing secret (required) | — |
| `VERA_ALGORITHM` | JWT algorithm | `HS256` |
| `VERA_ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | `1440` |
| `VERA_UPLOAD_DIR` | Uploaded PDF storage path | `./uploads` |
| `VERA_MAX_FILE_SIZE_MB` | Max upload size per file | `100` |
| `VERA_TESSERACT_CMD` | Path to Tesseract binary | OS-specific |

#### Database

| Variable | Description | Default |
|----------|-------------|---------|
| `VERA_DATABASE_URL` | Async SQLAlchemy URL | `postgresql+asyncpg://vera_user:...@localhost:5432/vera_db` |
| `VERA_DB_PASSWORD` | Postgres password (also used by Docker Compose) | `vera_secure_pass_123` |

#### Redis / Celery

| Variable | Description | Default |
|----------|-------------|---------|
| `VERA_REDIS_URL` | Broker and result backend | `redis://localhost:6379/0` |

#### Qdrant

| Variable | Description | Default |
|----------|-------------|---------|
| `VERA_QDRANT_HOST` | Qdrant hostname | `localhost` |
| `VERA_QDRANT_PORT` | Qdrant HTTP port | `6333` |

#### Models (reference — hardcoded in services today)

| Variable (`.env.example`) | Used by | Default in code |
|---------------------------|---------|-----------------|
| `TEXT_EMBED_MODEL` | `embedder.py` | `nomic-ai/nomic-embed-text-v1` |
| `NLI_MODEL` | `semantic_verifier.py` | `cross-encoder/nli-deberta-v3-small` |
| `CLIP_MODEL` | `visual_store.py` | `openai/clip-vit-base-patch32` |

#### Optional APIs

| Variable | Description |
|----------|-------------|
| `VERA_MATHPIX_APP_ID` | Mathpix OCR for difficult equations (optional) |
| `VERA_MATHPIX_APP_KEY` | Mathpix API key (optional) |
| `OPENAI_API_KEY` | Reserved for future LLM features (optional) |
| `GOOGLE_API_KEY` | Reserved for future features (optional) |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend base URL | `http://localhost:8000` |
| `NEXT_PUBLIC_APP_NAME` | Display name in UI | `VERA` |

---

## 13. Known Limitations

1. **Python 3.13 not supported** — `latex2sympy2` relies on tooling incompatible with 3.13. Use Python 3.11 or 3.12. SymPy `sympify` fallback handles many equations, but complex LaTeX may not parse.

2. **Scanned PDFs** — PyMuPDF cannot extract text from image-only scans. The Tesseract OCR fallback is basic; results on scanned textbooks will be significantly worse.

3. **Windows Celery** — You must use `--pool=solo`. Multiprocessing `fork` is not available on Windows, which limits true worker concurrency.

4. **Small NLI model calibration** — `nli-deberta-v3-small` produces compressed scores vs. larger models. Thresholds are tuned for this model (entailment > 0.45, contradiction > 0.60).

5. **Mixed verdict threshold** — Paragraphs with ≥ 20% wrong-weighted sentences return `mixed`. A long paragraph with one error among many correct sentences may still be labeled `mixed` rather than `correct`.

6. **CLIP diagram matching** — ViT-B/32 scores are lower than ViT-L/14. Abstract diagrams (schematics, plots) match less reliably than photos. The visual path weight is boosted in fusion to compensate.

7. **Equation extraction** — Only `$...$` and `$$...$$` LaTeX delimiters are indexed. `\begin{equation}` blocks are not extracted.

---

## 14. Contributing

1. Fork the repository
2. Create a branch: `feature/your-feature` or `fix/issue-description`
3. Make your changes
4. Run the pipeline test: `python tests/vera_pipeline_test.py`
5. Open a pull request

**Please do not commit:** `.env` files, model weights, `venv/`, `node_modules/`, or `backend/uploads/`.

---

## 15. License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for the full text.
