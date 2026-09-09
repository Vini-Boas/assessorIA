# AssessorIA

Projeto escolar de Inteligência Artificial: um assessor financeiro conversacional construído com **FastAPI**, **LangChain** e **LangGraph**, com roteamento entre múltiplos agentes especialistas, memória de conversa persistente e busca de FAQ por similaridade vetorial.

## Como funciona

Cada mensagem do usuário passa por um grafo de execução ([app/graph.py](app/graph.py)) que:

1. Aplica um **guardrail de entrada** (anonimização de PII e validação da mensagem);
2. Passa por um **roteador** que decide qual agente especialista deve responder;
3. Encaminha para o agente adequado, cada um com seu próprio prompt e ferramentas ([app/agents.py](app/agents.py)):
   - **Financeiro** — consultas e operações financeiras;
   - **Agenda** — compromissos e lembretes;
   - **FAQ** — respostas baseadas no PDF de perguntas frequentes, buscado por similaridade vetorial;
   - **Orquestrador** — combina respostas quando mais de um agente é acionado;
4. Aplica um **guardrail de saída** antes de devolver a resposta;
5. Persiste o histórico da sessão para dar continuidade à conversa.

### Modelos de linguagem

- **Gemini 2.5 Flash** (Google) como modelo principal para os agentes especialistas, com **fallback automático** para o Groq (`openai/gpt-oss-120b`) em caso de falha;
- **Groq** (`openai/gpt-oss-20b`) como modelo rápido para roteamento e orquestração.

### Armazenamento

| Serviço | Uso |
|---|---|
| **PostgreSQL** | Dados relacionais (financeiro/agenda) |
| **MongoDB Atlas** | Histórico e resumos de sessões de conversa |
| **Qdrant** | Busca vetorial para o FAQ e memória de longo prazo, usando embeddings do Gemini |

## Estrutura do projeto

```
app/
├── main.py              # Ponto de entrada FastAPI
├── config.py            # Configuração, variáveis de ambiente e validação
├── graph.py             # Grafo LangGraph que orquestra os agentes
├── agents.py            # Definição dos agentes especialistas
├── llms.py              # Instâncias dos modelos (Gemini / Groq)
├── db.py                # Conexões com Postgres, MongoDB e Qdrant
├── memory.py            # Persistência e recuperação de sessões
├── guardrail.py         # Guardrails de entrada/saída e anonimização de PII
├── prompts.py           # Prompts dos agentes
├── schemas.py           # Modelos Pydantic da API
├── routes/              # Rotas HTTP (chat e sessões)
└── tools/               # Ferramentas usadas pelos agentes (financeiro, FAQ, memória)
data/
├── FAQ_assessor_v1.1.pdf
└── inject_faq.py        # Script de ingestão do FAQ no Qdrant
frontend/                # Interface web estática servida pela própria API
```

## Pré-requisitos

- Python 3.11+
- Uma instância PostgreSQL
- Um cluster MongoDB Atlas
- Uma instância Qdrant (Cloud ou local)
- Chaves de API do **Google Gemini** e da **Groq**

Este projeto não possui `requirements.txt`/`pyproject.toml` no momento; as principais dependências usadas são:

```
fastapi uvicorn python-dotenv pydantic
langchain langchain-core langchain-community langchain-text-splitters
langchain-google-genai langchain-groq langgraph
psycopg2-binary pymongo qdrant-client groq
```

## Configuração

Crie um arquivo `.env` na raiz do projeto (veja `app/config.py` para a lista validada em runtime):

```env
# LLMs
GEMINI_API_KEY=
GROQ_API_KEY=

# Qdrant (FAQ e memória vetorial)
QDRANT_ENDPOINT=
QDRANT_API_KEY=

# MongoDB Atlas (sessões de conversa)
ATLAS_URI=

# PostgreSQL — informe as partes OU a URL completa em URL_DB
HOST_DB=
PORT_DB=
USERNAME_DB=
PASSWORD_DB=
DEFAULT_DB=
# URL_DB=postgresql://usuario:senha@host:porta/banco
```

> ⚠️ Nunca faça commit do `.env`. Ele já está no `.gitignore`.

## Executando o projeto

```bash
# 1. Instale as dependências (ver lista acima)
pip install fastapi uvicorn python-dotenv pydantic \
  langchain langchain-core langchain-community langchain-text-splitters \
  langchain-google-genai langchain-groq langgraph \
  psycopg2-binary pymongo qdrant-client groq

# 2. (Uma vez, ou sempre que o PDF do FAQ mudar) ingira o FAQ no Qdrant
python -m data.inject_faq

# 3. Suba a API
uvicorn app.main:app --reload
```

A aplicação sobe em `http://localhost:8000` e serve o frontend estático em `/`, além de expor `/health` para checar se todas as variáveis de ambiente e recursos necessários estão configurados.

## Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| `GET`  | `/health` | Status da aplicação e problemas de configuração |
| `POST` | `/chat?user_id=` | Envia uma mensagem ao assessor |
| `GET`  | `/chat/{user_id}` | Recupera o histórico ativo da sessão |
| `POST` | `/sessions/{user_id}/iniciar` | Inicia uma sessão |
| `POST` | `/sessions/{user_id}/encerrar` | Encerra a sessão e gera um resumo |
| `GET`  | `/sessions/{user_id}/passadas` | Lista sessões anteriores e seus resumos |

## Licença

Distribuído sob a licença MIT — veja [LICENSE](LICENSE).
