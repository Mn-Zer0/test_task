from elasticsearch import AsyncElasticsearch

from app.config import settings

_es_client: AsyncElasticsearch | None = None


# Маппинг индекса: только id и text
INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "text": {
                "type": "text",
                "analyzer": "russian",
            },
        }
    },
    "settings": {
        "analysis": {
            "analyzer": {
                "russian": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "russian_stop", "russian_stemmer"],
                }
            },
            "filter": {
                "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                "russian_stemmer": {"type": "stemmer", "language": "russian"},
            },
        }
    },
}

# Инициализация клиента
def get_es_client() -> AsyncElasticsearch:
    global _es_client
    if _es_client is None:
        _es_client = AsyncElasticsearch(hosts=[settings.ELASTIC_HOST])
    return _es_client


# Создаём индекс с русским анализатором если его ещё нет
async def init_es() -> None:
    client = get_es_client()
    exists = await client.indices.exists(index=settings.ELASTIC_INDEX)
    if not exists:
        await client.indices.create(index=settings.ELASTIC_INDEX, body=INDEX_MAPPING)


# Закрывает клиент и сбрасывает глобальную ссылку
# P.S (Сброс нужен, чтобы в следующем event loop клиент создался заново)
async def close_es() -> None:
    global _es_client
    if _es_client is not None:
        await _es_client.close()
        _es_client = None