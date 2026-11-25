from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, health, interview, questions, resume, users
from app.utils.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered interview preparation platform API",
    version="0.2.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(resume.router, prefix="/api/v1")
app.include_router(questions.router, prefix="/api/v1")
app.include_router(interview.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": f"Welcome to {settings.app_name} API",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
