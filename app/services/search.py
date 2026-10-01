from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.es_client import get_es_client
from app.models import Document
from app.services.documents import get_documents_by_ids


# Поиск документов по тексту
async def search_documents(
    session: AsyncSession, query: str, limit: int = 20
) -> tuple[int, list[Document]]:
    if not query.strip():
        return 0, []

    client = get_es_client()
    es_response = await client.search(
        index=settings.ELASTIC_INDEX,
        query={"match": {"text": query}},
        size=limit,
    )

    hits = es_response["hits"]["hits"]
    ids = [hit["_source"]["id"] for hit in hits]
    # total - сколько всего совпадений в индексе
    total = es_response["hits"]["total"]["value"]

    documents = await get_documents_by_ids(session, ids)
    return total, documents