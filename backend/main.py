import os

import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    port = int(os.environ.get("PORT", settings.port))
    is_production = settings.app_env.strip().lower() == "production"
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=port,
        reload=settings.debug and not is_production,
    )
