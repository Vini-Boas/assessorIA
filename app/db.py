from app.config import (
    URL_DB,
    MONGODB_URI,
    QDRANT_ENDPOINT, 
    QDRANT_API_KEY, 
    GEMINI_API_KEY
)
from qdrant_client import QdrantClient
from qdrant_client import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse
from langchain_google_genai import GoogleGenerativeAIEmbeddings

import psycopg2
from pymongo import MongoClient

COLLECTION_MEMORIA           = "memoria_conversas"
COLLECTION_FAQ               = "faq_chunks"
COLLECTION_PERFIL_RESTRICOES = "perfil_restricoes"
EMBEDDING_DIM                = 768

_pgsql_conn = None
_mongo_conn = None
_qdrant_conn = None

_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-2-preview",
    google_api_key=GEMINI_API_KEY,
)

def get_pgsql_conn():
    global _pgsql_conn
    if _pgsql_conn is None or _pgsql_conn.closed:
        _pgsql_conn = psycopg2.connect(URL_DB)
    return _pgsql_conn

def get_mongo_conn():
    global _mongo_conn
    if _mongo_conn is None:
        _mongo_conn = MongoClient(MONGODB_URI)
    return _mongo_conn

def get_qdrant_conn():
    global _qdrant_conn
    if _qdrant_conn is None:
        _qdrant_conn = QdrantClient(url=QDRANT_ENDPOINT, api_key=QDRANT_API_KEY)
    return _qdrant_conn

def garantir_colecao_qdrant(nome: str, dim: int = EMBEDDING_DIM, campos_indexados: list[str] | None = None) -> None:
    """
    Garante que uma collection exista no Qdrant, criando-a se necessário.

    Usa a MESMA instância Qdrant já configurada (não sobe nada novo) — só
    cria a collection na primeira vez que alguém grava nela.

    `campos_indexados`: campos de payload (tipo keyword) usados em filtros
    (ex.: "user_id"). O Qdrant Cloud recusa `query_filter`/`delete` por um
    campo sem índice — sem isso, filtrar por user_id vira 400.
    """
    qdrant = get_qdrant_conn()
    try:
        qdrant.get_collection(nome)
        return
    except UnexpectedResponse:
        qdrant.create_collection(
            collection_name=nome,
            vectors_config=qdrant_models.VectorParams(
                size=dim,
                distance=qdrant_models.Distance.COSINE,
            ),
        )

    for campo in campos_indexados or []:
        qdrant.create_payload_index(
            collection_name=nome,
            field_name=campo,
            field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
        )

def pgsql_disconnect():
    global _pgsql_conn
    if _pgsql_conn is not None:
        _pgsql_conn.close()
        _pgsql_conn = None

def mongo_disconnect():
    global _mongo_conn
    if _mongo_conn is not None:
        _mongo_conn.close()
        _mongo_conn = None

def gerar_embedding(texto: str) -> list[float]:
    """Gera um vetor de 768 dimensões para o texto informado."""
    return _embeddings.embed_query(texto, output_dimensionality=EMBEDDING_DIM)

def gerar_embeddings_batch(textos: list[str]) -> list[list[float]]:
    """Gera embeddings para uma lista de textos de uma vez (mais eficiente)."""
    return _embeddings.embed_documents(textos, output_dimensionality=EMBEDDING_DIM)