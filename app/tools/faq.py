from langchain.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import FAQ_PDF_PATH, GEMINI_API_KEY, DATA_DIR

FAQ_INDEX_DIR = DATA_DIR / "faiss_faq_index"

embeddings = GoogleGenerativeAIEmbeddings(
    model = "gemini-embedding-2-preview",
    google_api_key = GEMINI_API_KEY
)

if (FAQ_INDEX_DIR / "index.faiss").exists():
    db = FAISS.load_local(
        str(FAQ_INDEX_DIR), embeddings, allow_dangerous_deserialization=True
    )
else:
    loader = PyPDFLoader(FAQ_PDF_PATH)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
    chunks = splitter.split_documents(docs)
    db = FAISS.from_documents(chunks, embeddings)
    FAQ_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    db.save_local(str(FAQ_INDEX_DIR))

@tool
def faq_retriever(question: str) -> str:
    """Busca no FAQ oficial os trechos mais relevantes para responder a pergunta."""
    results = db.similarity_search(question, k=6)
    return "\n\n".join([result.page_content for result in results])

TOOLS = [faq_retriever]