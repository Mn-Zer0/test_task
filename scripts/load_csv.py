import argparse
import ast
import asyncio
import csv
from datetime import datetime

from sqlalchemy import delete, select

from app.config import settings
from app.db import async_session, engine, init_db
from app.es_client import close_es, get_es_client, init_es
from app.models import Document
from app.utils import row_hash


# Парсит строку в список строк
def parse_rubrics(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        value = ast.literal_eval(raw)
        if isinstance(value, list):
            return [str(v) for v in value]
    except (ValueError, SyntaxError):
        pass
    return [raw]


# Парсит дату в одном из поддерживаемых форматов
def parse_date(raw: str) -> datetime:
    raw = (raw or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Не удалось распарсить дату: {raw!r}")


# Определяет разделитель CSV по первой строке - таб, запятая или ;
def detect_delimiter(sample: str) -> str:
    counts = {"\t": sample.count("\t"), ",": sample.count(","), ";": sample.count(";")}
    return max(counts, key=counts.get)


# Полная очистка - удаляет индекс ES и все строки из БД
async def reset_data() -> None:
    client = get_es_client()
    await client.options(ignore_status=404).indices.delete(index=settings.ELASTIC_INDEX)
    await init_es()
    async with async_session() as session:
        await session.execute(delete(Document))
        await session.commit()
    print("Данные очищены (БД и ES)")


# Загружает CSV в PostgreSQL и Elasticsearch
async def load_csv(path: str, fresh: bool = False) -> None:
    await init_db()
    await init_es()
    client = get_es_client()

    if fresh:
        await reset_data()

    with open(path, "rb") as f:
        raw = f.read()
    print(f"Размер файла: {len(raw)} байт")

    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            content = raw.decode(enc)
            print(f"Кодировка: {enc}")
            break
        except UnicodeDecodeError:
            continue
    else:
        print("Не удалось определить кодировку")
        return

    # Разделитель определяем по первой строке (заголовку)
    first_line = content.splitlines()[0]
    delimiter = detect_delimiter(first_line)
    print(f"Разделитель: {delimiter!r}")

    reader = csv.DictReader(content.splitlines(), delimiter=delimiter)
    print(f"Заголовки: {reader.fieldnames}")

    count = 0
    skipped = 0

    async with async_session() as session:
        for i, row in enumerate(reader, start=1):
            text = (row.get("text") or "").strip()
            created_raw = (row.get("created_date") or "").strip()
            rubrics_raw = (row.get("rubrics") or "").strip()

            # Пропускаем строки без обязательных полей
            if not text or not created_raw:
                skipped += 1
                continue

            try:
                created_date = parse_date(created_raw)
            except ValueError:
                skipped += 1
                continue

            rubrics = parse_rubrics(rubrics_raw)
            h = row_hash(text, created_date, rubrics)

            # Дедупликация, если хеш уже в БД - пропускаем
            exists = await session.execute(
                select(Document.id).where(Document.text_hash == h)
            )
            if exists.scalar_one_or_none() is not None:
                skipped += 1
                continue

            doc = Document(
                text=text,
                text_hash=h,
                created_date=created_date,
                rubrics=rubrics,
            )
            session.add(doc)
            # flush нужен чтобы получить doc.id для индексации в ES
            await session.flush()

            await client.index(
                index=settings.ELASTIC_INDEX,
                id=doc.id,
                document={"id": doc.id, "text": doc.text},
            )
            count += 1

        await session.commit()
        # refresh делает свежезагруженные документы видимыми для поиска сразу
        await client.indices.refresh(index=settings.ELASTIC_INDEX)

    print(f"Загружено: {count}, пропущено: {skipped}")

    await close_es()
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Путь к CSV")
    parser.add_argument("--fresh", action="store_true", help="Очистить данные перед загрузкой")
    args = parser.parse_args()
    asyncio.run(load_csv(args.path, fresh=args.fresh))