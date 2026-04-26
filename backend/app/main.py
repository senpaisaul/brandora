"""FastAPI entry point."""
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import brands
from app.routers import ads, brands, competitors, ideas

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Brandora API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve cached ad images to the frontend. Mount is idempotent — directory is
# created by the image cache on first scrape if it doesn't exist.
cache_dir = Path("cache/images")
cache_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(cache_dir)), name="images")

app.include_router(brands.router)
app.include_router(competitors.router)
app.include_router(ads.router)
app.include_router(ideas.router)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}