# Justificativa — Perfil do Usuário

## 1. Quais arquivos você criou ou modificou?

**Criados**
- `app/perfil.py` -> persistência do perfil (Mongo + Qdrant).
- `app/routes/perfil_route.py` -> rota `POST /perfil`.
- `app/tools/perfil.py` -> as duas tools de leitura usadas pelo especialista financeiro.
- `JUSTIFICATIVA.md` -> este arquivo.

**Modificados**
- `app/schemas.py` -> `PerfilRequest`, com a validação do contrato.
- `app/db.py` -> constante `COLLECTION_PERFIL_RESTRICOES` e o helper `garantir_colecao_qdrant`.
- `app/routes/__init__.py` -> registro do `perfil_router`.
- `app/agents.py` -> as tools de perfil entram no `financeiro_app`.
- `app/prompts.py` -> regras e exemplos novos no `FINANCEIRO_PROMPT` (quando consultar o perfil, o que fazer sem cadastro, e a recusa de alterar perfil pelo chat).

Nenhum arquivo do frontend do chat (`frontend/js/app.js`, `frontend/html/index.html`, `frontend/css/style.css`) foi tocado.

## 2. Por onde o perfil entra, e onde cada parte dele é gravada?

Entra por um único ponto: `POST /perfil`, validado pelo `PerfilRequest`. A rota chama `app/perfil.py::salvar_perfil()`, que grava nos dois bancos a partir da mesma chamada: o dado estruturado (renda, gasto fixo, horizonte, perfil de investidor) vira um documento no Mongo (`_id = user_id`, upsert); as restrições em texto livre são reindexadas no Qdrant — apaga tudo que existia para aquele `user_id` e insere de novo, uma por ponto. Nenhuma outra rota ou tool grava nesses lugares.

## 3. Como o texto livre é indexado e consultado, e por que não é busca por palavra?

Cada restrição vira seu próprio ponto no Qdrant, com embedding individual e payload `{user_id, texto}`. A consulta (`buscar_restricoes_relevantes`) embeda a pergunta do usuário e busca por proximidade vetorial, filtrando por `user_id`. Não é busca por palavra porque o objetivo é encontrar uma restrição como "preciso guardar para consertar o carro" a partir de uma pergunta sobre "deixar o dinheiro travado por dois anos", não há palavra em comum entre as duas frases, só proximidade semântica, que é exatamente o que um índice lexical não captura.

## 4. Você criou uma tool ou duas? Por quê?

Duas: 
* `consultar_perfil_financeiro` -> lookup direto no Mongo, sem argumento
* `buscar_restricoes_financeiras` -> busca semântica no Qdrant, recebe a situação como argumento

São dois mecanismos de consulta com naturezas diferentes, um é leitura direta de um documento, o outro é busca vetorial. O uso de apenas uma tool só forçaria o custo de embedding mesmo quando a pergunta só precisa dos números.

## 5. O que garante que o perfil de um usuário não apareceria para outro?

O perfil de um usuário nunca aparecerá para outro pois `user_id` não é preenchido pelo modelo, vem do `RunnableConfig` da requisição. Toda leitura no Mongo é `find_one` pelo `_id`/`user_id`; toda busca no Qdrant carrega um filtro obrigatório `FieldCondition(key="user_id", match=user_id)`.

Nota: a tela Perfil hoje usa um `USER_ID` fixo no `perfil.js`, então, na prática, todo mundo que abrir a tela escreve no mesmo cadastro e nunca salva no seu próprio perfil. Isso é uma limitação de identidade da tela, não uma falha do backend. Backend isola corretamente por `user_id`, seja qual for o valor recebido no `POST`, e usa o `USER_ID` do configurable ao buscar nas tools. O ajuste necessário é mudar o `USER_ID` no `perfil.js` para utilizar o mesmo `USER_ID` do `app.js`

## 6. Sua tool consulta o banco diretamente ou faz HTTP na própria API? Por quê?

Direto. É o padrão já usado por todas as tools do projeto (`financeiro.py`, `faq.py`, `memory.py` chamam `get_pgsql_conn`/`get_qdrant_conn` diretamente). Uma tool chamando a própria API por HTTP dentro do mesmo processo seria redundante, sem ganho — só adiciona latência e um ponto de falha a mais.

## 7. Por que optamos por não criar um agente "perfil"?

Porque perfil não é uma intenção que o usuário expressa no chat — ninguém pergunta "sobre perfil"; ele aparece numa pergunta financeira ("quanto devo guardar?"). É dado de apoio do especialista que já aconselha dinheiro, não um domínio novo ao lado de finanças/agenda/FAQ. Um agente novo forçaria o roteador a decidir por uma rota que não existe na experiência real do usuário, e duplicaria lógica que já pertence ao financeiro.

## 8. Qual a vantagem do chat não alterar o cadastro?

Existe uma única fonte de verdade e um único caminho auditável de escrita (o formulário → `POST /perfil`). Isso evita que o modelo "negocie" mudanças de perfil dentro de uma conversa. Por exemplo, alguém tentando convencer o assistente a aumentar a renda cadastrada para liberar um conselho mais agressivo, além de manter a validação de contrato (tipos, faixas, relação renda × gasto) como o único portão de entrada para qualquer alteração.
