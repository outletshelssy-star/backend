from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.lifespan import lifespan

settings = get_settings()

app = FastAPI(
    lifespan=lifespan,
    debug=settings.debug,
    title=settings.app_name,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://frontend-hyrg.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix="/api/v1",
)


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    return {"message": "Hello FastAPI"}
