from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse, ChatHistory
from app.graph import executar_fluxo_assessor
from app.memory import recuperar_mensagens_ativas

router = APIRouter(tags=["chat"])

@router.post("/chat")
def chat(user_id: str, request: ChatRequest) -> ChatResponse:
    chat_response = executar_fluxo_assessor(request.message, user_id)
    return ChatResponse(response=chat_response)

@router.get("/chat/{user_id}")
def getHistory(user_id: str) -> list[ChatHistory]:
    return recuperar_mensagens_ativas(user_id)