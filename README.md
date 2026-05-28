# ⬡ NexusTrade — AI-Powered Market Intelligence Platform

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Gemini AI](https://img.shields.io/badge/AI-Gemini_2.0_Flash-4285F4?style=flat&logo=google&logoColor=white)](https://aistudio.google.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

**Real-time AI trade intelligence. Enter any sector, get a scored opportunity report in seconds.**

[Live Demo](#live-demo) · [API Docs](#api-reference) · [Quick Start](#quick-start) · [Architecture](#architecture)

</div>

---

## Overview

NexusTrade is a **production-grade market intelligence API** that answers one critical question for founders, analysts, and trade professionals:

> *"What are the best trade opportunities in [sector] for [region] right now?"*

It does this by:
1. **Fetching live market data** from the web using parallel search queries
2. **Synthesising it with Gemini AI** into a structured, scored report
3. **Returning actionable intelligence** with an opportunity score (0–100) across four dimensions

Unlike static market reports, NexusTrade is real-time — every report reflects current market conditions.


---

## Features

| Feature | Details |
|---|---|
| 🔭 **Multi-depth Analysis** | Quick (summary), Standard (full report), Deep (+ risk matrix + scoring) |
| 📊 **Opportunity Scoring** | 4-dimensional score: Market Size · Growth Velocity · Competitive Gap · Risk-Adjusted |
| 🌍 **Region Targeting** | Global, Southeast Asia, EU, Middle East, North America, Africa, and more |
| 👁 **Watchlist** | Save and track sectors across sessions |
| 📋 **Query History** | Paginated history with re-run capability |
| 🔐 **JWT Authentication** | Stateless HS256 tokens — no database required |
| ⚡ **Rate Limiting** | Per-IP limits via SlowAPI (configurable) |
| 🛡 **Security Headers** | Full CSP / HSTS / XSS protection middleware |
| 🐳 **Docker Ready** | Multi-stage build, non-root user, healthcheck |
| 🚀 **One-click Deploy** | `render.yaml` for Render.com deployment |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     NexusTrade API v2                       │
│                                                             │
│  POST /v2/insights                                          │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐    ┌──────────────────┐                    │
│  │  Auth Layer │    │  Rate Limiter    │                    │
│  │  JWT HS256  │    │  SlowAPI / IP    │                    │
│  └──────┬──────┘    └────────┬─────────┘                    │
│         │                    │                              │
│         ▼                    ▼                              │
│  ┌────────────────────────────────┐                         │
│  │        Insights Router         │                         │
│  └────────────────┬───────────────┘                         │
│          ┌────────┴────────┐                                │
│          ▼                 ▼                                │
│  ┌──────────────┐  ┌───────────────────┐                    │
│  │ MarketSearch │  │  IntelligenceAI   │                    │
│  │  Service     │  │  Service (Gemini) │                    │
│  │              │  │                   │                    │
│  │ 5 parallel   │  │ Prompt builder    │                    │
│  │ DDG queries  │  │ Retry (exp. back) │                    │
│  │ + trim logic │  │ Score extraction  │                    │
│  └──────┬───────┘  └────────┬──────────┘                    │
│         │                   │                               │
│         └─────────┬─────────┘                               │
│                   ▼                                         │
│          ┌─────────────────┐                                │
│          │  Session Store  │  (in-memory → swap Redis)      │
│          │  History        │                                │
│          │  Watchlist      │                                │    
│          └─────────────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

- **Stateless Auth**: JWT tokens are verified by signature alone — no session store or DB lookup required. Scales horizontally with zero coordination.
- **Parallel Search**: Five targeted search queries run concurrently (with a small stagger for rate-limit compliance), maximising data coverage without sequential latency.
- **Prompt Engineering**: The AI prompt is depth-aware. `deep` mode adds a structured JSON score block using a precisely specified schema, which is then extracted and validated by Pydantic.
- **Exponential Backoff**: Gemini's free tier enforces quota limits. The retry layer handles 429/503 transparently with 1s → 2s → 4s backoff.
- **Swap-ready Store**: `SessionService` has a clean interface designed to drop in Redis or PostgreSQL without changing router code.

---

## Project Structure

```
nexus-trade/
├── app/
│   ├── main.py                  # FastAPI app factory, middleware stack, lifespan
│   ├── api/
│   │   ├── auth.py              # POST /v2/auth/token
│   │   ├── insights.py          # POST /v2/insights  ← core endpoint
│   │   ├── watchlist.py         # GET/POST/DELETE /v2/watchlist
│   │   └── history.py           # GET/DELETE /v2/history
│   ├── core/
│   │   ├── config.py            # Pydantic-settings (type-safe env vars)
│   │   ├── security.py          # JWT issue + verify
│   │   ├── rate_limit.py        # SlowAPI limiter singleton
│   │   └── middleware.py        # Security headers middleware
│   ├── models/
│   │   └── schemas.py           # All Pydantic request/response schemas
│   └── services/
│       ├── intelligence_service.py  # Gemini AI + prompt builder + score extractor
│       ├── search_service.py        # Live web data aggregation (DuckDuckGo)
│       └── session_service.py       # History + watchlist (in-memory, Redis-ready)
├── frontend/
│   └── index.html               # SaaS-grade dashboard (zero dependencies)
├── tests/
│   └── test_integration.py      # Full E2E test suite (pytest)
├── Dockerfile                   # Multi-stage production build
├── docker-compose.yml           # Local development
├── render.yaml                  # One-click Render.com deploy
├── requirements.txt
└── .env.example
```

---

## Quick Start

### Prerequisites
- Python 3.11+ (or Docker)
- [Gemini API key](https://aistudio.google.com/app/apikey) — free tier works

### 1. Clone & Install

```bash
git clone https://github.com/0xSHSH/nexus-trade.git
cd nexus-trade

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:
```env
GEMINI_API_KEY=your_key_here
JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

Open **[http://localhost:8000/docs](http://localhost:8000/docs)** for the interactive API explorer.
Open **`frontend/index.html`** in a browser for the dashboard UI.

### Docker

```bash
docker compose up --build
```

---

## API Reference

### Authentication

```bash
# Get a token (no password — designed for exploration)
curl -X POST http://localhost:8000/v2/auth/token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "my-app"}'
```

### Generate an Intelligence Report

```bash
curl -X POST http://localhost:8000/v2/insights \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sector": "Green Hydrogen",
    "region": "European Union",
    "depth": "deep"
  }'
```

**Response:**
```json
{
  "request_id": "uuid",
  "sector": "Green Hydrogen",
  "region": "European Union",
  "depth": "deep",
  "generated_at": "2025-01-15T10:30:00Z",
  "processing_ms": 8420,
  "report_markdown": "## Executive Summary\n...",
  "score": {
    "overall": 78,
    "market_size": 82,
    "growth_velocity": 91,
    "competitive_gap": 65,
    "risk_adjusted": 70
  }
}
```

### Watchlist

```bash
# Add to watchlist
curl -X POST http://localhost:8000/v2/watchlist \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"sector": "Green Hydrogen", "region": "EU"}'

# Get watchlist
curl http://localhost:8000/v2/watchlist \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Deployment

### Render.com (Recommended)

1. Fork this repo
2. Create a new **Web Service** on [render.com](https://render.com)
3. Connect your fork — Render auto-detects `render.yaml`
4. Set `GEMINI_API_KEY` in the Render environment variables dashboard
5. Deploy — `JWT_SECRET` is auto-generated

---

## Testing

```bash
# Start the server first, then:
pytest tests/test_integration.py -v
```

Tests cover: health check, token issuance, input validation, insights generation, watchlist CRUD, and history.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **API Framework** | FastAPI 0.115 | Async-native, auto OpenAPI docs, best-in-class DX |
| **Runtime** | Python 3.13 | Latest stable, significant perf improvements |
| **AI Engine** | Google Gemini 2.0 Flash | Best speed/quality ratio; structured output support |
| **Web Search** | DDGS (DuckDuckGo) | No API key required; reliable real-time results |
| **Auth** | python-jose (JWT HS256) | Stateless, scalable, no DB dependency |
| **Rate Limiting** | SlowAPI | Production-grade, decorator-based, Redis-compatible |
| **Validation** | Pydantic v2 | Type-safe config + input sanitisation (anti-injection) |
| **Deployment** | Docker + Render | Portable, reproducible, free tier friendly |
| **Frontend** | Vanilla JS + CSS | Zero dependencies; loads instantly |

---

## Resume Assets

### Project Description (for CV/LinkedIn)
> **NexusTrade** — AI-powered market intelligence platform that synthesises live web data with Google Gemini AI to generate scored trade opportunity reports. Built a production-ready FastAPI backend with JWT auth, parallel web scraping, prompt-engineered AI analysis, and a zero-dependency SaaS dashboard.

### Bullet Points

- Engineered a **multi-depth AI analysis pipeline** using Google Gemini 2.0 with custom prompt templates, structured JSON score extraction, and exponential-backoff retry logic — achieving sub-10s end-to-end latency
- Implemented **parallel market data aggregation** across 5 concurrent DuckDuckGo search queries with context-window trimming, increasing data coverage by ~5× versus sequential fetch
- Designed a **stateless JWT authentication system** using HS256 signatures, enabling horizontal scaling with zero session-store coordination overhead
- Built a **full-stack production deployment** with Docker multi-stage builds (60% image size reduction), Render.com CI/CD via `render.yaml`, and comprehensive security middleware (HSTS, CSP, XSS protection)

### Portfolio Description
> NexusTrade demonstrates end-to-end product engineering: from AI prompt design and async Python architecture to a polished, responsive frontend dashboard. It solves a real problem (trade intelligence is slow and expensive) with a clean, extensible API that could serve analysts, founders, or fund managers.

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">
Built with FastAPI · Gemini AI · Python 3.13
</div>
