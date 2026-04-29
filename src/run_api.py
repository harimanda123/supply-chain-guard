import uvicorn
from src.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
        reload_excludes=["scripts/*", "data/*", "demo/*", "*.log"],
        log_level="info",
    )
