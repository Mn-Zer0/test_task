from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.es_client import close_es, init_es
from app.routers import documents


# Управление ресурсами приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_es()
    yield
    await close_es()


app = FastAPI(
    title="Search Service",
    description="Поисковик по текстам документов с использованием Elasticsearch",
    version="1.0.0",
    lifespan=lifespan,
)

# Все эндпоинты документов существуют в отдельном роутере /documents
app.include_router(documents.router)


# Проверка живости сервиса (для мониторинга и healthcheck в Docker)
@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}