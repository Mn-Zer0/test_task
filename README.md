Поисковик по текстам документов. Принимает произвольный текстовый
запрос, ищет по тексту в Elasticsearch и возвращает первые 20 документов со
всеми полями из PostgreSQL, упорядоченные по дате создания.

## Стек

- **Python 3.12**
- **FastAPI** - REST API, автоматическая генерация OpenAPI
- **PostgreSQL 16** + **SQLAlchemy 2.x (async)** - хранение документов
- **Elasticsearch 8.13** - полнотекстовый поиск (русский анализатор)
- **Docker** + **docker-compose** - запуск всех сервисов
- **pytest** + **pytest-asyncio** - тесты

## Быстрый старт

Требуется установленный Docker Desktop (или Docker + docker-compose на Linux).

```bash
# 1. Клонировать репозиторий и перейти в папку
git clone https://github.com/Mn-Zer0/test_task.git
cd test_task

# 2. Поднять сервисы
docker-compose up --build -d

# 3. Дождаться, пока все контейнеры станут Healthy
docker-compose ps

# 4. Загрузить CSV с данными
docker-compose exec app python -m scripts.load_csv /app/data/posts.csv

# 5. Открыть Swagger UI
# http://localhost:8000/docs
```

### Перезагрузка данных

Скрипт загрузки идемпотентен: повторный запуск не создаёт дубликатов.

```bash
# Обычная загрузка (пропустит уже загруженные документы)
docker-compose exec app python -m scripts.load_csv /app/data/posts.csv

# Полная перезагрузка (очистит БД и индекс перед загрузкой)
docker-compose exec app python -m scripts.load_csv /app/data/posts.csv --fresh
```

## API

### Поиск документов

```
GET /documents/search?q=<запрос>&limit=20
```

**Параметры:**

q (string) - Поисковый запрос, минимум 1 символ

limit (int) - Количество результатов (1–100, по умолчанию 20) 

**Пример:**

```bash
curl "http://localhost:8000/documents/search?q=BMW"
```

**Ответ:**

```json
{
  "total": 2,
  "items": [
    {
      "id": 701,
      "text": "За прошедшую неделю...",
      "created_date": "2019-05-21T03:10:01",
      "rubrics": ["VK-1603736028819866", "VK-62576435928"]
    }
  ]
}
```

total - всего совпадений в индексе

items - до 20 документов с полями из БД, отсортированных по created_date (ASC)

### Удаление документа

```
DELETE /documents/{doc_id}
```

Удаляет документ и из PostgreSQL, и из Elasticsearch.

**Пример:**

```bash
curl -X DELETE "http://localhost:8000/documents/701"
```

**Ответ:**

```json
{"id": 701, "status": "deleted"}
```

Если документ не найден - 404 {"detail": "Document not found"}.

### Health check

```
GET /health
```

Возвращает {"status": "ok"}.

## OpenAPI

Документация в формате OpenAPI лежит в файле docs.json в корне репозитория.

Сгенерировать заново:

```bash
curl http://localhost:8000/openapi.json -o docs.json
```

Или открыть Swagger UI: http://localhost:8000/docs

## Тесты

```bash
docker-compose exec app pytest -v
```

Покрытие:

- поиск находит документ по тексту
- пустой запрос возвращает 422
- удаление убирает документ из БД и ES, повторное удаление - 404

Тесты изолированы: создают временный документ и удаляют его после себя.
Продакшен-данные не затрагиваются.

## Архитектурные решения

### Слоистая структура

```
app/
├── routers/     - HTTP-эндпоинты (тонкий слой, только приём запроса)
├── services/    - логика (поиск, удаление)
├── models.py    - SQLAlchemy-модели
├── schemas.py   - Pydantic-схемы для валидации и ответов
├── es_client.py - клиент Elasticsearch
└── db.py        - подключение к PostgreSQL
```

Роутеры не содержат логики - только вызывают сервисы.

### Идемпотентная загрузка CSV

При загрузке для каждой строки считается SHA-256 хеш от text + created_date + rubrics.
Если документ с таким хешем уже есть в БД - строка пропускается (исключает дубликаты).

### Поиск и сортировка

Elasticsearch возвращает top-20 самых релевантных документов (size=limit).
Сервис подтягивает их полные данные из PostgreSQL по id и сортирует
по created_date по возрастанию.

### Асинхронность

Все слои приложения асинхронные:
- FastAPI - async def;
- SQLAlchemy - AsyncSession + asyncpg;
- Elasticsearch - AsyncElasticsearch.

PowerShell + curl.exe могут неправильно кодировать кириллицу в URL:
curl "http://localhost:8000/documents/search?q=привет" может вернуть
`nvalid HTTP request received.

Вместо этого можно использовать Swagger UI: http://localhost:8000/docs

## Остановка

```bash
# Остановить контейнеры (данные сохранятся)
docker-compose down

# Остановить и удалить данные (БД и ES)
docker-compose down -v
```

## Структура проекта

```
.
├── app/
│   ├── main.py              - точка входа FastAPI
│   ├── config.py            - настройки из .env
│   ├── db.py                - подключение к PostgreSQL
│   ├── models.py            - модель Document
│   ├── schemas.py           - Pydantic-схемы
│   ├── es_client.py         - клиент Elasticsearch
│   ├── utils.py             - row_hash для дедупликации
│   ├── routers/
│   │   └── documents.py     - эндпоинты /documents
│   └── services/
│       ├── search.py        - логика поиска
│       └── documents.py     - логика удаления
├── scripts/
│   └── load_csv.py          - загрузка CSV в БД и ES
├── tests/
│   └── test_api.py          - функциональные тесты
├── data/
│   └── posts.csv            - тестовый массив данных
├── docker-compose.yml
├── Dockerfile
├── requirements.txt         - зависимости
├── pytest.ini
├── .env
├── docs.json                - OpenAPI-спецификация
└── README.md
```
