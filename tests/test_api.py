import pytest_asyncio
from datetime import datetime
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

import app.es_client as es_module
from app.config import settings
from app.db import async_session, engine, init_db
from app.es_client import close_es, get_es_client, init_es
from app.main import app
from app.models import Document
from app.utils import row_hash


# HTTP-клиент к приложению без запуска uvicorn
@pytest_asyncio.fixture
async def client():
    es_module._es_client = None

    await init_db()
    await init_es()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await close_es()
    await engine.dispose()


# Создаёт тестовый документ в БД и ES, удаляет после теста
@pytest_asyncio.fixture
async def sample_document():
    text = "Тестовый документ"
    created_date = datetime(2026, 1, 1, 12, 0, 0)
    rubrics = ["test", "python"]
    h = row_hash(text, created_date, rubrics)

    # убираем возможный старый тестовый документ из БД
    async with async_session() as session:
        await session.execute(delete(Document).where(Document.text_hash == h))
        await session.commit()

    async with async_session() as session:
        doc = Document(
            text=text,
            text_hash=h,
            created_date=created_date,
            rubrics=rubrics,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

    es_client = get_es_client()
    await es_client.index(
        index=settings.ELASTIC_INDEX,
        id=doc.id,
        document={"id": doc.id, "text": doc.text},
    )
    await es_client.indices.refresh(index=settings.ELASTIC_INDEX)

    yield doc

    # удаляем только тестовый документ (БД + ES по id)
    async with async_session() as session:
        await session.execute(delete(Document).where(Document.id == doc.id))
        await session.commit()

    es_client = get_es_client()
    await es_client.options(ignore_status=404).delete(
        index=settings.ELASTIC_INDEX, id=doc.id
    )

# Поиск по слову из текста возвращает созданный документ
async def test_search_finds_document(client, sample_document):
    response = await client.get("/documents/search", params={"q": "Python"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["id"] == sample_document.id for item in data["items"])


# Пустой q не проходит валидацию FastAPI (min_length=1)
async def test_search_empty_query(client):
    response = await client.get("/documents/search", params={"q": ""})
    assert response.status_code == 422


# Первое удаление возвращает 200, повторное - 404
async def test_delete_document(client, sample_document):
    response = await client.delete(f"/documents/{sample_document.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    response = await client.delete(f"/documents/{sample_document.id}")
    assert response.status_code == 404