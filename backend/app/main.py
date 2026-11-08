from fastapi import FastAPI, HTTPException

from app.api.auth import router as auth_router
from app.api.circulation import router as circulation_router
from app.api.catalog import router as catalog_router
from app.api.members import router as members_router
from app.api.admin import router as admin_router
from app.core.config import settings
from app.db.session import check_database

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AISYS synthetic RFID Library Management prototype",
)

app.include_router(auth_router)
app.include_router(circulation_router)
app.include_router(catalog_router)
app.include_router(members_router)
app.include_router(admin_router)


@app.get("/api/v1/health/live")
def health_live():
    return {
        "status": "alive",
        "service": "aisys-library-api",
    }


@app.get("/api/v1/health/ready")
def health_ready():
    try:
        check_database()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    return {"status": "ready", "database": "connected"}
