from elasticsearch import NotFoundError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.es_client import get_es_client
from app.models import Document


# Возвращает документы из БД по списку id, отсортированные по дате создания
async def get_documents_by_ids(session: AsyncSession, ids: list[int]) -> list[Document]:
    if not ids:
        return []
    result = await session.execute(
        select(Document).where(Document.id.in_(ids)).order_by(Document.created_date)
    )
    return list(result.scalars().all())


# Удаляет документ из Elasticsearch и из БД
async def delete_document(session: AsyncSession, doc_id: int) -> bool:
    client = get_es_client()
    try:
        await client.options(ignore_status=404).delete(
            index=settings.ELASTIC_INDEX, id=doc_id
        )
    except NotFoundError:
        pass

    # Затем удаляем из БД, rowcount > 0 означает, что строка действительно была
    result = await session.execute(delete(Document).where(Document.id == doc_id))
    await session.commit()
    return result.rowcount > 0