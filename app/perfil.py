import uuid
from datetime import datetime, timezone
from typing import Optional

from qdrant_client import models

from app.db import (
    get_mongo_conn,
    get_qdrant_conn,
    gerar_embedding,
    gerar_embeddings_batch,
    garantir_colecao_qdrant,
    COLLECTION_PERFIL_RESTRICOES,
)
from app.schemas import PerfilRequest

# ==============================================================================
# CONEXÃO
# ==============================================================================

_mongo      = get_mongo_conn()
db          = _mongo["assessor"]
col_perfis  = db["perfis"]

_colecao_perfil_pronta = False

def _garantir_colecao_perfil() -> None:
    """
    Garante a collection do Qdrant sob demanda, no primeiro uso — não no
    import do módulo. Assim, um Qdrant fora do ar no boot não derruba o
    processo inteiro (e com ele finanças/agenda/FAQ/memória), só a
    funcionalidade de perfil na primeira chamada que precisar dela.
    """
    global _colecao_perfil_pronta
    if not _colecao_perfil_pronta:
        garantir_colecao_qdrant(COLLECTION_PERFIL_RESTRICOES, campos_indexados=["user_id"])
        _colecao_perfil_pronta = True

def _agora() -> datetime:
    return datetime.now(timezone.utc)

# ==============================================================================
# ESCRITA
# ==============================================================================

def salvar_perfil(perfil: PerfilRequest) -> dict:
    """
    Grava o perfil nos dois bancos a partir do mesmo ponto:
        1. Mongo   : substitui (upsert) o documento estruturado do user_id.
        2. Qdrant  : apaga TODAS as restrições antigas deste user_id e insere
                    as novas, uma por ponto — salvar de novo troca o conjunto
                    inteiro, nunca acumula ao lado do que já existia.

    Retorna o documento estruturado gravado (é a resposta da rota, já que
    não existe rota de leitura para confirmar o salvamento de outra forma).
    """
    agora = _agora()

    documento_estruturado = {
        "renda_mensal":        perfil.renda_mensal,
        "gasto_fixo_mensal":   perfil.gasto_fixo_mensal,
        "horizonte_meses":     perfil.horizonte_meses,
        "perfil_investidor":   perfil.perfil_investidor,
        "restricoes":          perfil.restricoes,
        "atualizado_em":       agora,
    }

    col_perfis.update_one(
        {"_id": perfil.user_id},
        {"$set": documento_estruturado},
        upsert=True,
    )

    _reindexar_restricoes(perfil.user_id, perfil.restricoes)

    return {"user_id": perfil.user_id, **documento_estruturado}

def _reindexar_restricoes(user_id: str, restricoes: list[str]) -> None:
    """Apaga as restrições antigas deste usuário e insere as novas, uma por ponto."""
    _garantir_colecao_perfil()
    qdrant = get_qdrant_conn()

    qdrant.delete(
        collection_name=COLLECTION_PERFIL_RESTRICOES,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    )
                ]
            )
        ),
    )

    if not restricoes:
        return

    vetores = gerar_embeddings_batch(restricoes)

    pontos = [
        models.PointStruct(
            id=str(uuid.uuid4()),
            vector=vetor,
            payload={"user_id": user_id, "texto": texto},
        )
        for vetor, texto in zip(vetores, restricoes)
    ]

    qdrant.upsert(collection_name=COLLECTION_PERFIL_RESTRICOES, points=pontos)

# ==============================================================================
# LEITURA
# ==============================================================================

def buscar_perfil_estruturado(user_id: str) -> Optional[dict]:
    """Retorna o dado estruturado do usuário, ou None se não houver cadastro."""
    return col_perfis.find_one({"_id": user_id})

def buscar_restricoes_relevantes(user_id: str, situacao: str, limite: int = 2) -> list[str]:
    """
    Busca semântica: retorna as restrições deste usuário ordenadas pela
    proximidade com `situacao`. Filtra por user_id — o perfil de um usuário
    nunca aparece na busca de outro.

    limite=2 por padrão.
    """
    _garantir_colecao_perfil()
    qdrant = get_qdrant_conn()
    vetor  = gerar_embedding(situacao)

    resultados = qdrant.query_points(
        collection_name=COLLECTION_PERFIL_RESTRICOES,
        query=vetor,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]
        ),
        limit=limite,
    )

    return [ponto.payload["texto"] for ponto in resultados.points]
