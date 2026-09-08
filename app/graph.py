import operator
from typing import Annotated
from groq import BadRequestError as GroqBadRequestError
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import RemoveMessage
from app.agents import (
    router_app,
    agenda_app,
    financeiro_app,
    orquestrador_app,
    faq_app
)
from app.guardrail import (
    guardrail_saida,
    guardrail_entrada,
    anonimizar_entrada
)
from app.memory import salvar_mensagem, recuperar_mensagens_ativas

# ==============================================================================
# ESTADO
# MessagesState já traz: messages: Annotated[list[AnyMessage], add_messages]
# O checkpointer propaga automaticamente para os subgrafos adicionados via add_node
# ==============================================================================
class Estado(MessagesState):
    agentes_chamados: Annotated[list[str], operator.add]
    rota:             str
    mapa_pii:         dict
    

# ==============================================================================
# NÓ ROTEADOR — necessário apenas para extrair a rota sem poluir messages
# ==============================================================================
TENTATIVAS_ROTEADOR = 3

def _mensagens_para_roteador(mensagens: list) -> list:
    """
    Remove do histórico as tool calls/tool results dos especialistas antes de
    repassar ao roteador.

    O grafo compartilha um único `messages` entre roteador e especialistas
    (agenda, financeiro, faq), cada um com seu próprio conjunto de tools. Se
    uma AIMessage com tool_calls de um especialista (ex.: faq_retriever)
    ficar no histórico, o modelo do roteador pode "repetir" esse tool_call ao
    rotear a pergunta seguinte — e como essa tool não está no bind do
    roteador, a Groq recusa a geração com 400 tool_use_failed. O roteador só
    precisa dos turnos human/assistant para decidir a rota, não do rastro
    interno de tools dos especialistas.
    """
    return [
        m for m in mensagens
        if not getattr(m, "tool_calls", None) and m.type != "tool"
    ]

def no_roteador(estado: Estado, config: RunnableConfig) -> dict:
    saida = None
    mensagens = _mensagens_para_roteador(estado["messages"])
    for tentativa in range(1, TENTATIVAS_ROTEADOR + 1):
        try:
            saida = router_app.invoke({"messages": mensagens}, config=config)
            break
        except GroqBadRequestError as erro:
            # Instabilidade conhecida dos modelos gpt-oss no Groq: o parser do
            # formato "harmony" às vezes gruda o token de canal (<|channel|>...)
            # no nome da tool, gerando um tool call inválido (tool_use_failed).
            # Costuma ser transitório — vale tentar de novo antes de desistir.
            print(f"[roteador] tool_use_failed na tentativa {tentativa}/{TENTATIVAS_ROTEADOR}: {erro}")
            if tentativa == TENTATIVAS_ROTEADOR:
                return {
                    "agentes_chamados": ["roteador"],
                    "rota":             "fim",
                    "messages":         [{
                        "role":    "assistant",
                        "content": "Desculpe, tive um problema ao processar sua mensagem. Pode tentar novamente?",
                    }],
                }

    texto = saida["messages"][-1].text

    if "ROUTE=" not in texto:
        return {
            "agentes_chamados": ["roteador"],
            "rota":             "fim",
            "messages":         [{"role": "assistant", "content": texto}],
        }

    rota = "fim"
    for linha in texto.splitlines():
        if linha.startswith("ROUTE="):
            rota = linha.split("=", 1)[1].strip()
            break

    return {
        "agentes_chamados": ["roteador", rota],
        "rota":             rota,
    }

# ==============================================================================
# NÓ ORQUESTRADOR — wrapper para capturar agentes_chamados via rota
# ==============================================================================

def no_orquestrador(estado: Estado) -> dict:
    # Pega a última resposta do especialista (última AIMessage com conteúdo)
    ultima_especialista = ""
    for mensagem in reversed(estado["messages"]):
        if mensagem.type == "ai" and mensagem.content:
            ultima_especialista = mensagem.content
            break
    
    saida = orquestrador_app.invoke({
        "messages": {"role": "human", "content": ultima_especialista}
    })

    return {
        "agentes_chamados": ["orquestrador"],
        "messages":        [{"role": "assistant", "content": saida["messages"][-1].text}]
    }

# ==============================================================================
# NÓ ENTRADA DE GUARDRAIL — Guardrail para a entrada
# ==============================================================================

def no_entrada_guardrail(estado: Estado) -> dict:
    # Pega a última resposta do especialista (última AIMessage com conteúdo)
    pergunta_usuario = estado["messages"][-1]

    pergunta_anonimizada, mapa_PII = anonimizar_entrada(pergunta_usuario.text)

    guardrail_saida = guardrail_entrada(pergunta_anonimizada)

    if guardrail_saida["bloqueado"]:
        return {
            "messages": [{"role": "assistant", "content": guardrail_saida["mensagem"]}],
            "rota": "fim"
        }
    else:
        return {
            "messages": [
                RemoveMessage(pergunta_usuario.id), 
                {"role": "human", "content": pergunta_anonimizada}
            ],
            "mapa_pii": mapa_PII,
            "rota":     "roteador"
        }

# ==============================================================================
# FUNÇÃO DE DECISÃO
# ==============================================================================
def decidir_especialista(estado: Estado) -> str:
    return estado["rota"] if estado["rota"] in ("financeiro", "agenda", "faq") else "fim"
def decidir_guardrail(estado: Estado) -> str:
    return estado["rota"]

# ==============================================================================
# GRAFO
# ==============================================================================
grafo = StateGraph(Estado)

grafo.add_node("roteador",          no_roteador)
grafo.add_node("guardrail_entrada", no_entrada_guardrail)
grafo.add_node("guardrail_saida",   guardrail_saida)
grafo.add_node("agenda",            agenda_app)   # subgrafo direto — checkpointer propaga
grafo.add_node("financeiro",        financeiro_app)   # subgrafo direto — checkpointer propaga
grafo.add_node("faq",               faq_app)           # subgrafo direto
grafo.add_node("orquestrador",      no_orquestrador)

grafo.set_entry_point("guardrail_entrada")

grafo.add_conditional_edges(
    "guardrail_entrada",
    decidir_guardrail,
    {
        "roteador": "roteador",
        "fim":      END,
    },
)

grafo.add_conditional_edges(
    "roteador",
    decidir_especialista,
    {
        "financeiro": "financeiro",
        "agenda":     "agenda",
        "faq":        "faq",
        "fim":        END,
    },
)

grafo.add_edge("financeiro",        "orquestrador")
grafo.add_edge("agenda",            "orquestrador")
grafo.add_edge("orquestrador",      END)
grafo.add_edge("faq",               END)

memory = MemorySaver()
fluxo_agentes = grafo.compile(checkpointer=memory)

# ==============================================================================
# FLUXO PRINCIPAL
# ==============================================================================
def executar_fluxo_assessor(pergunta_usuario: str, user_id: str) -> str:
    config = {"configurable": {"thread_id": user_id}}

    mensagens_previas = []
    if not fluxo_agentes.get_state(config).values.get("messages"):
        print("tentando pegar aí mano, será que foi?")
        mensagens_previas = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in recuperar_mensagens_ativas(user_id)
        ]

    print(f"mensagens_previas, {mensagens_previas}")

    estado_inicial = {
        "messages":         mensagens_previas + [{"role": "human", "content": pergunta_usuario}],
        "agentes_chamados": [],
        "rota":             "",
        "mapa_pii":         {},
    }

    texto_anonimizado, _ = anonimizar_entrada(pergunta_usuario)
    salvar_mensagem(user_id, "human", texto_anonimizado)

    estado_final = fluxo_agentes.invoke(
        estado_inicial,
        config={"configurable": {"thread_id": user_id}},
    )

    resposta_final = estado_final["messages"][-1].text

    salvar_mensagem(user_id, "assistant", resposta_final)

    print(f"[debug] agentes chamados: {estado_final['agentes_chamados']}")
    return resposta_final

# ==============================================================================
# Métodos
# ==============================================================================

def limpar_mensagens(user_id: str) -> None:
    """
    Remove todas as mensagens de uma sessão ativa do usuário.
    """
    estado = fluxo_agentes.get_state({"configurable": {"thread_id": user_id}})
    if estado.values.get("messages"):
        estado.values["messages"].clear()