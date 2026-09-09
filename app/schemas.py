from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

class ChatRequest(BaseModel):
    message: str = Field(..., description="The message to send to the chatbot")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The chatbot's response to the user's message")

class ChatHistory(BaseModel):
    role:    str = Field(..., description="Quem enviou a mensagem: 'human' ou 'assistant'")
    content: str = Field(..., description="O conteúdo da mensagem")

class SessionResponse(BaseModel):
    session_id: str
    resumo:     str | None = None

class PerfilRequest(BaseModel):
    """
    Contrato exato enviado pela tela Perfil (frontend/js/perfil.js).
    Não renomear nem tornar opcional nenhum campo: o front já garante o
    formato, esta classe garante o conteúdo.
    """
    user_id:            str = Field(..., min_length=1, description="Identificador estável do usuário, o mesmo usado no chat.")
    renda_mensal:        float = Field(..., gt=0, description="Renda mensal; deve ser maior que zero.")
    gasto_fixo_mensal:   float = Field(..., ge=0, description="Gasto fixo mensal; deve ser >= 0 e menor que a renda.")
    horizonte_meses:     int = Field(..., ge=1, le=120, description="Horizonte de uso do dinheiro, em meses (1 a 120).")
    perfil_investidor:   Literal["conservador", "moderado", "arrojado"]
    restricoes:          list[str] = Field(..., min_length=1, max_length=5, description="1 a 5 frases livres, cada uma independente.")

    @field_validator("restricoes")
    @classmethod
    def _restricoes_nao_vazias(cls, valor: list[str]) -> list[str]:
        limpas = [texto.strip() for texto in valor if texto.strip()]
        if not limpas:
            raise ValueError("Informe ao menos uma restrição não vazia.")
        return limpas

    @model_validator(mode="after")
    def _gasto_menor_que_renda(self) -> "PerfilRequest":
        if self.gasto_fixo_mensal >= self.renda_mensal:
            raise ValueError("gasto_fixo_mensal deve ser menor que renda_mensal.")
        return self