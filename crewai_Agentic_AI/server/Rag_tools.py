import os
import json
import logging
import hashlib
from typing import List, Dict, Any
from datetime import datetime
import uuid
import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
import PyPDF2
from docx import Document

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

try:
    import whisper
except ImportError:
    whisper = None

# Knowledge Graph
import networkx as nx
from pyvis.network import Network

# LLM integration
import google.generativeai as genai
from dotenv import load_dotenv

# Database
import sqlite3
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("rag_and_markdown_tools")


# ------------------- Core RAG + Knowledge Graph -------------------
class RAGKnowledgeGraphCore:
    """Core RAG and Knowledge Graph functionality for CrewAI tools."""

    _instances = {}

    def __new__(cls, collection_name: str = "default_collection", **kwargs):
        if collection_name not in cls._instances:
            instance = super(RAGKnowledgeGraphCore, cls).__new__(cls)
            cls._instances[collection_name] = instance
            instance._initialized = False
        return cls._instances[collection_name]

    def __init__(self,
                 collection_name: str = "default_collection",
                 vector_db_path: str = "./vector_db",
                 knowledge_graph_path: str = "./knowledge_graph.json",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):

        if hasattr(self, '_initialized') and self._initialized:
            return

        self.collection_name = collection_name
        self.vector_db_path = vector_db_path
        self.knowledge_graph_path = knowledge_graph_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.embedding_model = SentenceTransformer(embedding_model)

        os.makedirs(self.vector_db_path, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=self.vector_db_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        self.knowledge_graph = nx.DiGraph()

        if os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.llm_model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.llm_model = None
            self.logger.warning("GEMINI_API_KEY not found. LLM features disabled.")

        self.init_database()
        self.load_existing_data()
        self._initialized = True

    def init_database(self):
        """Initialize SQLite database for metadata."""
        self.db_path = os.path.join(self.vector_db_path, f"metadata_{self.collection_name}.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, filename TEXT, file_type TEXT,
                upload_date TEXT, content_hash TEXT, chunk_count INTEGER, metadata TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY, query TEXT, response TEXT,
                relevant_chunks TEXT, timestamp TEXT, confidence_score REAL
            )
        ''')
        self.conn.commit()

    def load_existing_data(self):
        try:
            self.logger.info(f"Connected to ChromaDB collection '{self.collection.name}' with {self.collection.count()} items.")
            kg_path = f"{self.knowledge_graph_path.replace('.json', '')}_{self.collection_name}.json"
            if os.path.exists(kg_path):
                with open(kg_path, 'r') as f:
                    graph_data = json.load(f)
                    self.knowledge_graph = nx.node_link_graph(graph_data)
                self.logger.info(f"Loaded knowledge graph with {self.knowledge_graph.number_of_nodes()} nodes")
        except Exception as e:
            self.logger.error(f"Error loading existing data: {e}")

    # --- Extractors (pdf, docx, image OCR, audio, etc.) ---
    def extract_text_from_pdf(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return "".join(page.extract_text() + "\n" for page in pdf_reader.pages)
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def extract_text_from_docx(self, file_path: str) -> str:
        try:
            doc = Document(file_path)
            return "".join(paragraph.text + "\n" for paragraph in doc.paragraphs)
        except Exception as e:
            self.logger.error(f"Error extracting text from DOCX: {e}")
            return ""

    def extract_text_from_image(self, file_path: str) -> str:
        if not pytesseract or not Image:
            return ""
        try:
            return pytesseract.image_to_string(Image.open(file_path))
        except Exception as e:
            self.logger.error(f"Error extracting text from image: {e}")
            return ""

    def transcribe_audio(self, file_path: str) -> str:
        if not whisper:
            return ""
        try:
            model = whisper.load_model("base")
            result = model.transcribe(file_path)
            return result["text"]
        except Exception as e:
            self.logger.error(f"Error transcribing audio: {e}")
            return ""

    # --- Chunking + Embeddings ---
    def chunk_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]
        chunks, start = [], 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end].strip()
            if chunk: chunks.append(chunk)
            start += self.chunk_size - self.chunk_overlap
        return chunks

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.embedding_model.encode(texts).tolist()

    # --- Ingestion Methods ---
    def ingest_document(self, file_path: str, metadata: Dict = None) -> str:
        doc_id = str(uuid.uuid4())
        filename = os.path.basename(file_path)
        file_type = os.path.splitext(filename)[1].lower()

        text_extractors = {
            '.pdf': self.extract_text_from_pdf,
            '.docx': self.extract_text_from_docx,
            '.txt': lambda p: open(p, 'r', encoding='utf-8').read(),
            '.jpg': self.extract_text_from_image, '.jpeg': self.extract_text_from_image,
            '.png': self.extract_text_from_image,
            '.mp3': self.transcribe_audio, '.wav': self.transcribe_audio,
        }

        if file_type not in text_extractors:
            raise ValueError(f"Unsupported file type: {file_type}")

        text = text_extractors[file_type](file_path)
        if not text.strip():
            raise ValueError("No text could be extracted")

        chunks = self.chunk_text(text)
        embeddings = self.generate_embeddings(chunks)
        chunk_ids = [str(uuid.uuid4()) for _ in chunks]
        chunk_metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_meta = {
                'chunk_id': chunk_ids[i], 'document_id': doc_id, 'chunk_index': i,
                'filename': filename, 'file_type': file_type, 'created_at': datetime.now().isoformat(),
            }
            if metadata: chunk_meta.update(metadata)
            chunk_metadatas.append(chunk_meta)

        self.collection.add(embeddings=embeddings, documents=chunks, metadatas=chunk_metadatas, ids=chunk_ids)

        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (doc_id, filename, file_type, datetime.now().isoformat(),
                        hashlib.md5(text.encode()).hexdigest(), len(chunks), json.dumps(metadata or {})))
        self.conn.commit()

        return doc_id

    def ingest_text_idea(self, idea_text: str, metadata: Dict = None) -> str:
        doc_id = str(uuid.uuid4())
        chunks = self.chunk_text(idea_text)
        embeddings = self.generate_embeddings(chunks)
        chunk_ids = [str(uuid.uuid4()) for _ in chunks]
        self.collection.add(embeddings=embeddings, documents=chunks, ids=chunk_ids)
        return doc_id

    def query(self, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        if self.collection.count() == 0:
            return {"response": "Empty KB."}
        query_embedding = self.generate_embeddings([query_text])
        results = self.collection.query(query_embeddings=query_embedding, n_results=top_k)
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            'documents': self.collection.count(),
            'collection_name': self.collection_name,
            'kg_nodes': self.knowledge_graph.number_of_nodes(),
            'kg_edges': self.knowledge_graph.number_of_edges()
        }


# ------------------- Tool Definition -------------------
@mcp.tool()
def knowledge_base_manager_tool(
        action: str,
        collection_name: str = "default_collection",
        file_path: str = None,
        text: str = None,
        query_text: str = None,
        metadata: str = None,
        top_k: int = 5,
        output_file: str = None,
        max_nodes: int = 150,
        confirm: bool = False
) -> str:
    """
    Manage the RAG knowledge base:
    - ingest_document (needs file_path)
    - ingest_text (needs text)
    - query (needs query_text)
    - get_stats
    - visualize
    - clear
    """
    rag_core = RAGKnowledgeGraphCore(collection_name=collection_name)

    if metadata and isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}

    if action == 'ingest_document':
        if not file_path or not os.path.exists(file_path):
            return f"Error: invalid file path {file_path}"
        doc_id = rag_core.ingest_document(file_path, metadata)
        return f"Document ingested with ID: {doc_id}"

    elif action == 'ingest_text':
        if not text:
            return "Error: missing text"
        doc_id = rag_core.ingest_text_idea(text, metadata)
        return f"Text ingested with ID: {doc_id}"

    elif action == 'query':
        if not query_text:
            return "Error: missing query_text"
        result = rag_core.query(query_text, top_k)
        return json.dumps(result)

    elif action == 'get_stats':
        return json.dumps(rag_core.get_stats())

    elif action == 'visualize':
        return rag_core.visualize_knowledge_graph(output_file, max_nodes)

    elif action == 'clear':
        if not confirm:
            return "Error: confirm=True required"
        rag_core.clear_database(collection_name)
        return f"Knowledge base '{collection_name}' cleared successfully"

    return f"Error: unknown action '{action}'"


if __name__ == "__main__":
    mcp.run(transport="stdio")
