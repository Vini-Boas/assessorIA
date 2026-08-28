// ============================================================
// Configuração
// ============================================================
// Ajuste para a URL onde o FastAPI está rodando.
const API_BASE = "http://localhost:8000";
const CHAT_ENDPOINT = `${API_BASE}/chat`;

// ============================================================
// Elementos
// ============================================================
const thread = document.getElementById("thread");
const threadEmpty = document.getElementById("thread-empty");
const composer = document.getElementById("composer");
const inputPergunta = document.getElementById("pergunta");
const botaoEnviar = document.getElementById("enviar");
const sessionIdEl = document.getElementById("session-id");
const resetButton = document.getElementById("reset-session");
const statusDot = document.getElementById("status-dot");
const hint = document.getElementById("hint");

// ============================================================
// Sessão
// ============================================================
const SESSION_STORAGE_KEY = "assistente_session_id";

async function getIP() {
  try {
    const response = await fetch("https://ipinfo.io/json");
    const data = await response.json();
    return data.ip || null;
  } catch (error) {
    console.error("Erro ao obter o IP:", error);
    return null;
  }
}

function gerarSessionIdTemporario() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback para contextos sem crypto.randomUUID (ex.: http:// não-localhost).
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// O IP é a identidade permanente da pessoa;
async function obterSessionId() {
  const ip = await getIP();
  if (ip) {
    localStorage.setItem(SESSION_STORAGE_KEY, ip);
    return ip;
  }

  const emCache = localStorage.getItem(SESSION_STORAGE_KEY);
  if (emCache) return emCache;

  const temporario = gerarSessionIdTemporario();
  localStorage.setItem(SESSION_STORAGE_KEY, temporario);
  return temporario;
}

async function registrarSessaoNoBackend(id) {
  try {
    await fetch(`${API_BASE}/sessions/${encodeURIComponent(id)}/iniciar`, { method: "POST" });
  } catch (error) {
    console.error("Erro ao iniciar sessão no backend:", error);
  }
}

async function encerrarSessaoNoBackend(id) {
  try {
    await fetch(`${API_BASE}/sessions/${encodeURIComponent(id)}/encerrar`, { method: "POST" });
  } catch (error) {
    console.error("Erro ao encerrar sessão no backend:", error);
  }
}

// Carrega o histórico da conversa em andamento
async function carregarHistorico(id) {
  try {
    const response = await fetch(`${API_BASE}/chat/${encodeURIComponent(id)}`);
    if (!response.ok) {
      throw new Error("Erro ao buscar histórico do servidor");
    }
    const mensagens = await response.json();
    mensagens.forEach(({ role, content }) => {
      adicionarMensagem({ tipo: role === "human" ? "user" : "assistant", texto: content });
    });
  } catch (error) {
    console.error("Erro ao carregar histórico:", error);
  }
}

async function carregarConversas(id) {
  try {
    const response = await fetch(`${API_BASE}/sessions/${encodeURIComponent(id)}/passadas`);
    if (!response.ok) {
      throw new Error("Erro ao buscar conversas do servidor");
    }
    const conversas = await response.json();
    sidebarList.innerHTML = "";
    conversas.forEach(({ session_id, resumo }) => {
      if (resumo != "")
        adicionarConversa({ session_id, resumo });
    });
  } catch (error) {
    console.error("Erro ao carregar conversas:", error);
  }
}

// "Nova sessão" não troca a identidade (o IP) — apenas encerra a
// conversa atual (gerando o resumo que alimenta a memória de longo prazo) e
// abre uma conversa nova para a mesma pessoa com um UUID aleatório
async function iniciarNovaSessao() {
  setHint("Encerrando conversa anterior...");
  await encerrarSessaoNoBackend(sessionId);

  thread.innerHTML = "";
  thread.appendChild(threadEmpty);
  threadEmpty.style.display = "block";

  await registrarSessaoNoBackend(sessionId);
  await carregarConversas(sessionId);
  setHint("Nova conversa iniciada.");
}

function exibirSessionId(id) {
  sessionIdEl.textContent = id.length > 12 ? id.slice(0, 8) + "…" : id;
  sessionIdEl.title = id;
}

let sessionId = null;

(async function inicializarSessao() {
  sessionId = await obterSessionId();
  exibirSessionId(sessionId);
  await registrarSessaoNoBackend(sessionId);
  await carregarHistorico(sessionId);
  await carregarConversas(sessionId);
})();

resetButton.addEventListener("click", () => {
  iniciarNovaSessao();
});

// ============================================================
// Utilidades de UI
// ============================================================
function setHint(texto, comoErro = false) {
  hint.textContent = texto || "";
  hint.classList.toggle("is-error", comoErro);
}

function marcarStatus(online) {
  statusDot.classList.toggle("is-offline", !online);
}

function escaparHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

function rolarParaFinal() {
  thread.scrollTop = thread.scrollHeight;
}

function adicionarMensagem({ tipo, texto, agentes }) {
  threadEmpty.style.display = "none";

  const wrapper = document.createElement("div");
  wrapper.className = `message message--${tipo}`;

  const label = document.createElement("div");
  label.className = "message__label";
  label.textContent = tipo === "user" ? "você" : tipo === "error" ? "erro" : "assistente";
  wrapper.appendChild(label);

  const bubble = document.createElement("div");
  bubble.className = "message__bubble";
  bubble.innerHTML = escaparHtml(texto);
  wrapper.appendChild(bubble);

  if (agentes && agentes.length > 0) {
    const agentesEl = document.createElement("div");
    agentesEl.className = "message__agents";
    agentes.forEach((nome) => {
      const tag = document.createElement("span");
      tag.className = "agent-tag";
      tag.textContent = nome;
      agentesEl.appendChild(tag);
    });
    wrapper.appendChild(agentesEl);
  }

  thread.appendChild(wrapper);
  rolarParaFinal();
  return wrapper;
}

const sidebarList = document.querySelector(".sidebar__list");

function adicionarConversa({ session_id, resumo }) {
  const wrapper = document.createElement("li");
  wrapper.className = `sidebar__item`;

  const button = document.createElement("button");
  button.className = "sidebar__item-button";
  button.setAttribute("type", "button");
  wrapper.appendChild(button);

  const id = document.createElement("span");
  id.className = "sidebar__item-id";
  id.textContent = session_id;
  button.appendChild(id);

  const resumo_item = document.createElement("span");
  resumo_item.className = "sidebar__item-resumo";
  resumo_item.textContent = resumo;
  button.appendChild(resumo_item);

  sidebarList.appendChild(wrapper);
}

function adicionarIndicadorDigitando() {
  const wrapper = document.createElement("div");
  wrapper.className = "message message--assistant";
  wrapper.id = "typing-indicator";

  const label = document.createElement("div");
  label.className = "message__label";
  label.textContent = "assistente";
  wrapper.appendChild(label);

  const bubble = document.createElement("div");
  bubble.className = "message__bubble";
  bubble.innerHTML = `<span class="typing"><span></span><span></span><span></span></span>`;
  wrapper.appendChild(bubble);

  thread.appendChild(wrapper);
  rolarParaFinal();
}

function removerIndicadorDigitando() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

// ============================================================
// Textarea: auto-resize + enviar com Enter
// ============================================================
inputPergunta.addEventListener("input", () => {
  inputPergunta.style.height = "auto";
  inputPergunta.style.height = Math.min(inputPergunta.scrollHeight, 140) + "px";
});

inputPergunta.addEventListener("keydown", (evento) => {
  if (evento.key === "Enter" && !evento.shiftKey) {
    evento.preventDefault();
    composer.requestSubmit();
  }
});

// ============================================================
// Envio da pergunta
// ============================================================
composer.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  const pergunta = inputPergunta.value.trim();
  if (!pergunta) return;

  adicionarMensagem({ tipo: "user", texto: pergunta });
  inputPergunta.value = "";
  inputPergunta.style.height = "auto";
  adicionarIndicadorDigitando();
  botaoEnviar.disabled = true;

  try {
    if (!sessionId) {
      sessionId = await obterSessionId();
      exibirSessionId(sessionId);
      await registrarSessaoNoBackend(sessionId);
    }

    // Fetch para o endpoint /chat com session_id e a mensagem no corpo
    const response = await fetch(`${CHAT_ENDPOINT}?session_id=${encodeURIComponent(sessionId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: pergunta }),
    });

    if (!response.ok) {
      throw new Error("Erro ao buscar dados do servidor");
    }

    const data = await response.json();
    removerIndicadorDigitando();
    adicionarMensagem({ tipo: "assistant", texto: data.response });
    marcarStatus(true);
  } catch (error) {
    console.error("Erro na requisição:", error);
    removerIndicadorDigitando();
    adicionarMensagem({ tipo: "error", texto: "Não foi possível obter resposta do assistente." });
    marcarStatus(false);
  } finally {
    botaoEnviar.disabled = false;
    inputPergunta.focus();
  }
});

// Foco inicial
inputPergunta.focus();
