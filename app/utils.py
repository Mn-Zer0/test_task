import hashlib
from datetime import datetime

# Хеш всей строки - text + created_date + rubrics (отсортированные)
def row_hash(text: str, created_date: datetime, rubrics: list[str]) -> str:
    payload = f"{text}|{created_date.isoformat()}|{sorted(rubrics)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()