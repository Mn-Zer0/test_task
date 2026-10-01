from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# Документ в ответе API - все поля из БД
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    created_date: datetime
    rubrics: list[str]


# Ответ поиска - общее число совпадений и список документов
class SearchResponse(BaseModel):
    total: int
    items: list[DocumentOut]


# Ответ удаления документа
class DeleteResponse(BaseModel):
    id: int
    status: str = Field(default="deleted")