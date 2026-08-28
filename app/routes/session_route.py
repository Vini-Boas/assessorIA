"""
As rotas do ciclo de vida da sessão.

Antes: quem encerrava a sessão era o `while True` do script — o usuário digitava
"sair", o laço chamava encerrar_sessao() e imprimia o resumo. Na migração para a
API esse laço sumiu, e com ele o único ponto do sistema que fechava sessões.
Resultado: nenhuma sessão ganhava resumo, e como buscar_historico() só enxerga
sessões COM resumo, a memória de longo prazo ficava permanentemente vazia.

Agora: o navegador decide. O botão "nova sessão" chama POST /sessions/{id}/encerrar
antes de sortear um novo UUID — é o equivalente HTTP de digitar "sair".

Repare que este arquivo, como o chat.py, é fino de propósito: ele recebe o
pedido, chama quem sabe fazer o trabalho (app.memory) e devolve o resultado.
Toda a lógica de resumo mora no memory.py.
"""

from fastapi import APIRouter

from app.memory import encerrar_sessao, iniciar_sessao, recuperar_historico
from app.schemas import SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/{session_id}/iniciar", response_model=SessionResponse)
def iniciar(session_id: str) -> SessionResponse:
    iniciar_sessao(session_id)
    return SessionResponse(session_id=session_id, resumo=None)

@router.post("/{session_id}/encerrar", response_model=SessionResponse)
def encerrar(session_id: str) -> SessionResponse:
    resumo = encerrar_sessao(session_id)
    return SessionResponse(session_id=session_id, resumo=resumo or None)

@router.get("/{session_id}/passadas", response_model=list[SessionResponse])
def listar_passadas(session_id: str) -> list[SessionResponse]:
    passadas = recuperar_historico(session_id=session_id, limite= 20)
    return [
        SessionResponse(session_id=doc.get("doc_id"), resumo=doc.get("resumo"))
        for doc in passadas
    ]
