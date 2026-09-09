"""
Tools de leitura do perfil financeiro — usadas pelo especialista financeiro
para ancorar conselhos (quanto guardar, que risco faz sentido, etc.) no que
o usuário cadastrou na tela Perfil.

Duas tools, porque são duas fontes com naturezas diferentes:
  - consultar_perfil_financeiro : lookup direto no Mongo (números e escolha
    fechada). Não precisa de argumento de busca — é sempre "o perfil deste
    usuário".
  - buscar_restricoes_financeiras : busca semântica no Qdrant. Recebe a
    situação/pergunta do usuário como argumento, porque É disso que depende
    o que for relevante buscar (ex.: "travar dinheiro" deve encontrar uma
    restrição que fala em "reserva pro carro", sem termos em comum).

Só leitura: não existe tool de escrita/edição de perfil exposta ao agente.
Cadastrar ou mudar perfil é só pela tela — o chat nunca grava aqui.
"""

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.perfil import buscar_perfil_estruturado, buscar_restricoes_relevantes

def _user_id_da_config(config: RunnableConfig) -> str | None:
    configuravel = (config or {}).get("configurable", {})
    return configuravel.get("user_id") or configuravel.get("thread_id")

@tool
def consultar_perfil_financeiro(config: RunnableConfig) -> str:
    """Consulta o perfil financeiro estruturado do usuário: renda mensal,
    gasto fixo mensal, horizonte de tempo (em meses) e perfil de investidor
    (conservador/moderado/arrojado).

    Use ANTES de aconselhar quanto o usuário deveria guardar, investir ou
    quanto risco faz sentido para ele. Se a tool indicar que não há perfil
    cadastrado, NÃO invente números: oriente o usuário a preencher a tela
    Perfil antes de dar esse tipo de conselho.
    """
    user_id = _user_id_da_config(config)
    if not user_id:
        return "Não foi possível identificar o usuário para consultar o perfil."

    perfil = buscar_perfil_estruturado(user_id)
    if not perfil:
        return (
            "Nenhum perfil financeiro cadastrado para este usuário. "
            "Oriente-o a preencher a tela Perfil antes de aconselhar valores ou risco."
        )

    return (
        f"Renda mensal: R$ {perfil['renda_mensal']:.2f}\n"
        f"Gasto fixo mensal: R$ {perfil['gasto_fixo_mensal']:.2f}\n"
        f"Horizonte: {perfil['horizonte_meses']} meses\n"
        f"Perfil de investidor: {perfil['perfil_investidor']}"
    )

@tool
def buscar_restricoes_financeiras(situacao: str, config: RunnableConfig) -> str:
    """Busca, entre as restrições cadastradas pelo usuário na tela Perfil,
    as que forem relevantes para a situação descrita — mesmo que a
    restrição não use as mesmas palavras da pergunta (ex.: uma pergunta
    sobre travar dinheiro por muito tempo deve encontrar uma restrição que
    fala em manter reserva para um conserto).

    Use sempre que o conselho puder esbarrar numa restrição pessoal do
    usuário (liquidez, prazo, tolerância a risco, planos futuros).

    Args:
        situacao: a pergunta ou situação financeira em avaliação.
    """
    user_id = _user_id_da_config(config)
    if not user_id:
        return "Não foi possível identificar o usuário para consultar restrições."

    restricoes = buscar_restricoes_relevantes(user_id, situacao)
    if not restricoes:
        return "Nenhuma restrição cadastrada para este usuário."

    return "\n".join(f"- {texto}" for texto in restricoes)

TOOLS = [consultar_perfil_financeiro, buscar_restricoes_financeiras]
