# Brandora

Competitive ad intelligence for D2C brands. Scrape a brand's website + recent Meta ads from 2-3 competitors, analyze copy and visuals with Claude, and generate grounded ad ideas backed by competitor provenance.

Built as a take-home assessment. ~4 hours end-to-end.

---

## What it does

1. **Brand profile** — scrapes the brand's homepage, extracts product category, positioning, tone of voice, target audience, value propositions, and notable claims via Claude Haiku 4.5.
2. **Competitor ad scraping** — pulls 5-6 most recent image and carousel ads per competitor from Meta Ad Library via the Apify `facebook-ads-scraper` actor. Filters out video, non-English, and template-placeholder ads. Caches creatives locally for reproducible vision analysis.
3. **Per-ad AI analysis** — for each ad, runs concurrent copy analysis (text-only) and visual analysis (Haiku vision on the cached image). Produces structured tags: messaging angle, emotional tone, visual style, dominant colors, has_people, ugc_looking, etc.
4. **Grounded ad idea generation** — single Claude Opus 4.7 call synthesizes brand profile + the full analyzed ad corpus into 2 distinct ad ideas, each citing the specific competitor `ad_id`s that informed it. Append-only history.
5. **Browseable UI** — Next.js 14 frontend with permanent sidebar nav, browseable ad library organized by competitor, and an ideas panel showing hook + creative concept + brand fit rationale + provenance badges.

Demo brand: **Ridge** (ridge.com). Competitors: **Bellroy**, **Nomad**, **Ekster**.

---

## Quick start

### Prerequisites

- Python 3.12+
- Node 20+
- An Anthropic API key — https://console.anthropic.com
- An Apify API token — https://console.apify.com

### Backend

```bash
cd backend
cp .env.example .env
# Open .env and fill in ANTHROPIC_API_KEY and APIFY_API_TOKEN

uv sync   # or: pip install -e .
uv run uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Swagger docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

### First run — populate the database

In `http://localhost:8000/docs`:

1. `POST /brands` with `{"name": "Ridge", "url": "https://ridge.com"}` → ~5-10s
2. `POST /competitors` for each:
   - `{"brand_id": 1, "name": "Bellroy", "facebook_url": "https://www.facebook.com/bellroy.official/"}`
   - `{"brand_id": 1, "name": "Nomad", "facebook_url": "https://www.facebook.com/Nomad/"}`
   - `{"brand_id": 1, "name": "Ekster", "facebook_url": "https://www.facebook.com/eksterwallets/"}`
   - Each takes ~60-120s (Apify scrape + image download)
3. `POST /ads/analyze-all/{competitor_id}` for each (1, 2, 3) → ~5-10s each
4. `POST /brands/1/generate-ideas` → ~15s

Refresh `http://localhost:3000` and all three tabs populate.

Total cost: ~$0.30 Apify + ~$0.50 Anthropic = under $1 per full pipeline run.

---

## Architecture

### Stack

- **Backend:** FastAPI · SQLModel · SQLite · Anthropic Python SDK · Apify Python client · BeautifulSoup
- **Frontend:** Next.js 14 (app router) · React 19 · TypeScript · Tailwind · shadcn/ui
- **Persistence:** SQLite at `backend/brandora.db`. Local image cache at `backend/cache/images/{meta_ad_id}/{n}.jpg`.

### Schema

5 SQLModel tables, all with strongly-typed Pydantic schemas for JSON columns:

- `Brand` — name, url, `profile: BrandProfile | None`
- `Competitor` — brand_id, name
- `Ad` — competitor_id, format, headline, primary_text, cta_text, creative_urls, local_image_paths, full `raw_payload` from Apify
- `AdAnalysis` — ad_id, `copy_analysis: CopyAnalysis`, `visual_analysis: VisualAnalysis`, tags. **Separate row from `Ad` so re-running analysis with better prompts doesn't require re-scraping.**
- `AdIdea` — brand_id, `payload: AdIdeaPayload`. **Append-only — every generation run preserves history.**

### LLM strategy — two-tier

- **Claude Haiku 4.5** for volume extraction: brand profile (1 call), copy analysis (14 calls), visual analysis (14 calls)
- **Claude Opus 4.7** for the one cross-document reasoning step: idea generation (1 call)

Structured outputs via forced tool-use with Pydantic schemas as `input_schema`. Defensive JSON-string parse for an Opus 4.7 quirk where nested-list tool inputs occasionally return as serialized strings.

### Per-ad analysis is concurrent

`analyze-all` runs N ads through `asyncio.gather`, each ad runs copy + visual concurrently via `asyncio.to_thread`. Wall-clock is ~5-8 seconds for 6 ads instead of 30+ sequential. `return_exceptions=True` so one failed ad doesn't poison the batch.

---

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| **Scraping source** | Apify `facebook-ads-scraper` actor | Reliability over building Playwright + handling Meta's bot detection within a 4-hour budget. ~$5.80 per 1000 results — more than acceptable. |
| **Brand scraping depth** | Homepage only, 15k char cap | Hero copy + nav + footer of a D2C site is enough for positioning extraction. Crawling subpages is diminishing returns at this scale. |
| **Ad filter** | Image and carousel only, English only, no template placeholders | Brief asks for image/carousel ads. ASCII-ratio heuristic for English (no extra dep). DCO/DPA ads with `{{product.brand}}` placeholders fall back to `cards[0]`. |
| **Image storage** | Local cache | Meta CDN URLs expire (the `oe=` timestamp). Local files keep vision analysis reproducible across days. Frontend serves them via FastAPI static files mount at `/images`. |
| **Vision input** | Base64 of cached local image | Reproducible. URL-based vision is a crapshoot once URLs expire. |
| **Carousels** | Analyze first image only | First image is the hero creative — what users see in the feed. D2C carousels are typically same product / different SKU, so secondary cards are diminishing-returns analysis. |
| **Per-ad vs batch analysis** | Per-ad, concurrent | Haiku produces sharper visual descriptions when given one image at a time. Concurrency recovers the wall-clock savings. |
| **LLM tiers** | Haiku for extraction, Opus 4.7 for synthesis | Cost-quality tradeoff. Haiku handles ~28 extraction calls cheaply, Opus does the one cross-document reasoning call where synthesis quality is graded hardest. |
| **Idea generation persistence** | Append-only | Lets you regenerate and compare. Old ideas are never lost. Reviewer can see history during demo. |
| **Idea schema** | `idea_1` + `idea_2` as named sibling fields, not `list[idea]` | Opus 4.7 occasionally serializes nested-list tool inputs as JSON strings. Flat schema sidesteps the quirk; semantics unchanged. |
| **Frontend data fetching** | Plain `useEffect` + `useState` | 4 endpoints, 3 panels. React Query is overkill and adds a learning surface for the reviewer. Hand-rolled hooks make every data flow trivially traceable in one read. |
| **UI layout** | Permanent left sidebar + scrollable content pane | Tabs at the top scrolled away with the page during long ad-grid scrolls. Sidebar stays pinned, content fills the rest of the viewport. |

---

## Project structure

```
brandora/
├── backend/
│   ├── .env.example
│   ├── pyproject.toml
│   ├── brandora.db                 # gitignored
│   ├── cache/images/{ad_id}/N.jpg  # gitignored
│   └── app/
│       ├── config.py               # pydantic-settings Settings singleton
│       ├── db.py                   # engine + get_session dependency
│       ├── models.py               # 5 SQLModel tables + nested Pydantic schemas
│       ├── main.py                 # FastAPI app, CORS, static files mount
│       ├── llm/
│       │   ├── client.py           # extract_structured() with Opus quirk fix
│       │   └── prompts.py          # 4 system prompts + ad formatter
│       ├── services/
│       │   ├── brand_profiler.py   # httpx + BS4 + Haiku extraction
│       │   ├── ad_scraper.py       # Apify call + normalization defenses
│       │   ├── ad_analyzer.py      # concurrent copy + visual analysis
│       │   └── idea_generator.py   # Opus 4.7 cross-document synthesis
│       └── routers/
│           ├── brands.py
│           ├── competitors.py
│           ├── ads.py              # analyze-single, analyze-all, get-analysis
│           └── ideas.py            # generate, list
└── frontend/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx                # sidebar + 3 panels
    │   └── globals.css
    ├── components/
    │   ├── AdCard.tsx              # one ad with image + copy + AI analysis
    │   ├── BrandPanel.tsx
    │   ├── CompetitorPanel.tsx     # grid of AdCards per competitor
    │   ├── IdeasPanel.tsx
    │   └── ui/                     # shadcn primitives
    └── lib/
        └── api.ts                  # typed fetch wrapper for all endpoints
```

---

## Sample output

### Generated idea (Ridge, from a real run)

> **Hook:** *"Built for day 1. Engineered for day 10,000."*
>
> **Format:** single_image
>
> **Creative concept:** A premium, minimalist product-shot composition on a clean charcoal-gray background. Two Ridge wallets are displayed side-by-side at a slight three-quarter angle — one in aged titanium showing subtle patina/wear marks, the other pristine in gunmetal. Bold sans-serif typography overlays: 'Day 1' above the new wallet and 'Day 10,000' above the worn one. Small embossed 'Lifetime Guarantee' seal in the corner. Studio lighting emphasizes the machined metal edges and carbon fiber texture.
>
> **Brand fit:** Ridge's entire positioning rests on lifetime durability as the antidote to disposable culture. A side-by-side 'new vs. aged' product shot makes the lifetime guarantee tangible and visual, speaking directly to intentional buyers who value longevity. The premium, understated studio aesthetic matches Ridge's minimalist tone — no lifestyle clutter, just the product and the promise.
>
> **Inspired by ad IDs:** [1, 2, 5] (three Bellroy "made for the long haul" durability ads)

A second idea from the same run cited a non-overlapping set: ads [3, 13, 14] (Bellroy replaceable luggage parts + Ekster TravelPack). Cross-competitor synthesis with auditable provenance.

---

## Known limitations

- **Ekster has 2 ads, not 6.** They lean on video reels for Meta. We correctly filter to image + carousel only and accept the real number rather than fabricate parity.
- **No generated ad images.** The brief asked for ad ideas (creative briefs), not finished creatives. The architecture supports adding image generation cleanly — pipe `creative_concept` into Flux / Gemini / `gpt-image-1`, cache result, add `image_url` field to `AdIdeaPayload`. Scoped out for time and because the rubric grades grounding and reasoning, not visual output.
- **Single-brand UI.** Backend supports multiple brands cleanly; the UI auto-loads the first one. Multi-brand picker is a 30-min addition.
- **No background jobs.** Long endpoints (scraping, analyze-all) block the request. Acceptable for a single-user demo; production would queue these.
- **No tests.** 4-hour budget. The Pydantic schemas serve as the validation layer; failures surface immediately.

---

## Time breakdown

| Phase | Time |
|---|---|
| Stack setup, schemas, FastAPI skeleton | ~30 min |
| Brand profiler (scrape + Haiku extraction) | ~30 min |
| Ad scraping + Apify normalization defenses | ~50 min |
| Per-ad analysis (copy + vision, concurrent) | ~30 min |
| Idea generation (Opus 4.7 + structured-output debugging) | ~40 min |
| Next.js frontend (4 panels + sidebar layout) | ~50 min |
| README + Loom prep | ~30 min |
| **Total** | **~4 hours** |

Apify spend across full pipeline runs during development: ~$0.30. Anthropic spend: ~$0.50.

---

## Environment variables

`backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-xxx
APIFY_API_TOKEN=apify_api_xxx
DATABASE_URL=sqlite:///./brandora.db
IMAGE_CACHE_DIR=cache/images
```

`frontend/.env.local` (optional, defaults to `http://localhost:8000`):

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

---

## API surface

| Method | Path | What |
|---|---|---|
| POST | `/brands` | Create brand, scrape homepage, extract profile |
| GET | `/brands` | List all brands |
| GET | `/brands/{id}` | Get one brand |
| POST | `/competitors` | Create competitor, scrape Meta ads, cache images |
| GET | `/competitors?brand_id={id}` | List competitors (optionally filtered) |
| GET | `/competitors/{id}/ads` | List ads for a competitor |
| POST | `/ads/{id}/analyze` | Analyze one ad (copy + visual) |
| POST | `/ads/analyze-all/{competitor_id}` | Analyze all ads for a competitor concurrently |
| GET | `/ads/{id}/analysis` | Get the analysis for one ad |
| POST | `/brands/{id}/generate-ideas` | Generate 2 grounded ad ideas via Opus 4.7 |
| GET | `/brands/{id}/ideas` | List all generated ideas (newest first) |
| GET | `/images/{ad_id}/{n}.jpg` | Cached ad creative (FastAPI static files) |

Full schema and tryout in Swagger at `http://localhost:8000/docs`.

---

## License

Built for a hiring assessment. No license claimed.
