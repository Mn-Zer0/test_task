from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import DeleteResponse, SearchResponse
from app.services.documents import delete_document
from app.services.search import search_documents

router = APIRouter(prefix="/documents", tags=["documents"])

# Поиск документов по текту
@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    total, documents = await search_documents(session, q, limit=limit)
    return SearchResponse(total=total, items=documents)


# Удаление документа по id из БД и из поискового индекса
@router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete(
    doc_id: int,
    session: AsyncSession = Depends(get_session),
):
    # delete_document удаляет и из БД, и из ES, True если документ был
    deleted = await delete_document(session, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return DeleteResponse(id=doc_id)