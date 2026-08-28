from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse, ChatHistory
from app.graph import executar_fluxo_assessor
from app.memory import recuperar_mensagens_ativas

router = APIRouter(tags=["chat"])

@router.post("/chat")
def chat(session_id: str, request: ChatRequest) -> ChatResponse:
    chat_response = executar_fluxo_assessor(request.message, session_id)
    return ChatResponse(response=chat_response)

@router.get("/chat/{session_id}")
def getHistory(session_id: str) -> list[ChatHistory]:
    return recuperar_mensagens_ativas(session_id)