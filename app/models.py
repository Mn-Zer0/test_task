from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    rubrics: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)