"""
Rota da tela Perfil.

Só existe escrita. O formulário envia o perfil inteiro (dado estruturado +
restrições) e o POST responde com o que foi gravado — é assim que o
salvamento é confirmado, já que não há rota de leitura.

Validação de contrato (tipos, faixas, relação renda x gasto, 1–5 restrições)
é toda feita pelo PerfilRequest (app/schemas.py) antes de chegar aqui: dado
inválido nunca entra nesta função, o FastAPI já devolve 422 sozinho.
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from app.schemas import PerfilRequest
from app.perfil import salvar_perfil
from app.config import FRONTEND_DIR

router = APIRouter(tags=["perfil"])

@router.get("/perfil")
def perfil_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "html" / "perfil.html")

@router.post("/perfil")
def perfil(request: PerfilRequest) -> dict:
    return salvar_perfil(request)
