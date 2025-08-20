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
            self.logger.warning("GEMINI_API_KEY not found in .env file. LLM features will be limited.")

        self.init_database()
        self.load_existing_data()
        self._initialized = True

    def init_database(self):
        """Initialize SQLite database for storing high-level metadata."""
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
        """Load existing knowledge graph."""
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
            self.logger.warning("OCR libraries not installed. Cannot process image.")
            return ""
        try:
            return pytesseract.image_to_string(Image.open(file_path))
        except Exception as e:
            self.logger.error(f"Error extracting text from image: {e}")
            return ""

    def transcribe_audio(self, file_path: str) -> str:
        if not whisper:
            self.logger.warning("Whisper library not installed. Cannot process audio.")
            return ""
        try:
            model = whisper.load_model("base")
            result = model.transcribe(file_path)
            return result["text"]
        except Exception as e:
            self.logger.error(f"Error transcribing audio: {e}")
            return ""

    def chunk_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size: return [text]
        chunks, start = [], 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end].strip()
            if chunk: chunks.append(chunk)
            start += self.chunk_size - self.chunk_overlap
        return chunks

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.embedding_model.encode(texts).tolist()

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
            '.mp3': self.transcribe_audio, '.wav': self.transcribe_audio, '.m4a': self.transcribe_audio,
        }

        if file_type not in text_extractors:
            raise ValueError(f"Unsupported file type: {file_type}")

        text = text_extractors[file_type](file_path)
        if not text.strip(): raise ValueError("No text could be extracted")

        content_hash = hashlib.md5(text.encode()).hexdigest()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE content_hash = ?", (content_hash,))
        if cursor.fetchone():
            self.logger.info(f"Document '{filename}' with same content already exists.")
            return None

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

        cursor.execute('INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (doc_id, filename, file_type, datetime.now().isoformat(), content_hash, len(chunks),
                        json.dumps(metadata or {})))
        self.conn.commit()

        self.update_knowledge_graph(doc_id, text, chunks, metadata)
        self.save_data()
        self.logger.info(f"Successfully ingested document: {filename} ({len(chunks)} chunks)")
        return doc_id

    def ingest_text_idea(self, idea_text: str, metadata: Dict = None) -> str:
        doc_id = str(uuid.uuid4())
        content_hash = hashlib.md5(idea_text.encode()).hexdigest()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE content_hash = ?", (content_hash,))
        if cursor.fetchone():
            self.logger.info("Idea with same content already exists.")
            return None

        full_text = f"Original Idea: {idea_text}"
        if self.llm_model:
            try:
                prompt = f"Analyze and expand the following idea: '{idea_text}'. Provide a refined description, key objectives, target audience, and potential challenges."
                response = self.llm_model.generate_content(prompt)
                full_text += f"\n\nExpanded Analysis:\n{response.text}"
            except Exception as e:
                self.logger.warning(f"LLM processing failed: {e}")

        chunks = self.chunk_text(full_text)
        embeddings = self.generate_embeddings(chunks)

        chunk_ids = [str(uuid.uuid4()) for _ in chunks]
        chunk_metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_meta = {'chunk_id': chunk_ids[i], 'document_id': doc_id, 'chunk_index': i,
                          'filename': 'text_idea',
                          'file_type': 'text', 'created_at': datetime.now().isoformat(), 'content_type': 'idea'}
            if metadata: chunk_meta.update(metadata)
            chunk_metadatas.append(chunk_meta)

        self.collection.add(embeddings=embeddings, documents=chunks, metadatas=chunk_metadatas, ids=chunk_ids)

        doc_metadata = metadata or {}
        doc_metadata.update({'content_type': 'idea', 'original_idea': idea_text})
        cursor.execute('INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (doc_id, 'text_idea', 'text', datetime.now().isoformat(), content_hash, len(chunks),
                        json.dumps(doc_metadata)))
        self.conn.commit()

        self.update_knowledge_graph(doc_id, full_text, chunks, doc_metadata)
        self.save_data()
        self.logger.info(f"Successfully ingested text idea ({len(chunks)} chunks)")
        return doc_id

    def query(self, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        if self.collection.count() == 0:
            return {'response': "The knowledge base is empty. Please ingest some documents first.",
                    'relevant_chunks': [], 'confidence_score': 0.0}

        query_embedding = self.generate_embeddings([query_text])
        results = self.collection.query(query_embeddings=query_embedding,
                                       n_results=min(top_k, self.collection.count()))

        relevant_chunks, context_text = [], ""
        if results['ids'][0]:
            for i in range(len(results['ids'][0])):
                score = 1.0 - results['distances'][0][i]
                relevant_chunks.append(
                    {'content': results['documents'][0][i], 'score': float(score),
                     'metadata': results['metadatas'][0][i]})
                context_text += f"{results['documents'][0][i]}\n\n"

        response_text = "No relevant information found in the knowledge base."
        if self.llm_model and context_text.strip():
            try:
                prompt = f"Based on the following context, answer the user's query.\n\nContext:\n{context_text}\n\nQuery: {query_text}\n\nAnswer:"
                response = self.llm_model.generate_content(prompt)
                response_text = response.text
            except Exception as e:
                self.logger.warning(f"LLM response generation failed: {e}")
                response_text = f"Based on the retrieved context:\n\n{context_text[:1500]}..."
        elif context_text.strip():
            response_text = f"Based on the retrieved context:\n\n{context_text[:1500]}..."

        avg_confidence = float(np.mean([c['score'] for c in relevant_chunks])) if relevant_chunks else 0.0

        interaction_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO interactions VALUES (?, ?, ?, ?, ?, ?)',
                       (interaction_id, query_text, response_text,
                        json.dumps([c['metadata']['chunk_id'] for c in relevant_chunks]),
                        datetime.now().isoformat(), avg_confidence))
        self.conn.commit()

        return {'response': response_text, 'relevant_chunks': relevant_chunks, 'confidence_score': avg_confidence}

    def update_knowledge_graph(self, doc_id: str, text: str, chunks: List[str], metadata: Dict = None):
        import re
        self.knowledge_graph.add_node(doc_id, node_type='document', content=text[:200] + "...",
                                     metadata=metadata or {})
        entities = set(re.findall(r'\b[A-Z][a-z]{2,}\b', text))
        for entity in list(entities)[:20]:
            entity_id = f"entity_{hashlib.md5(entity.encode()).hexdigest()[:8]}"
            self.knowledge_graph.add_node(entity_id, node_type='entity', name=entity)
            self.knowledge_graph.add_edge(doc_id, entity_id, relationship='contains_entity')
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            self.knowledge_graph.add_node(chunk_id, node_type='chunk', content=chunk, chunk_index=i)
            self.knowledge_graph.add_edge(doc_id, chunk_id, relationship='has_chunk')

    def visualize_knowledge_graph(self, output_file: str = None, max_nodes: int = 150) -> str:
        if self.knowledge_graph.number_of_nodes() == 0:
            return "Knowledge graph is empty. Ingest some documents first."

        if not output_file:
            output_file = f"knowledge_graph_{self.collection_name}.html"

        nodes_to_include = list(self.knowledge_graph.nodes())[:max_nodes]
        subgraph = self.knowledge_graph.subgraph(nodes_to_include)

        net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")

        color_map = {'document': '#ff6b6b', 'entity': '#4ecdc4', 'chunk': '#45b7d1'}

        for node, data in subgraph.nodes(data=True):
            node_type = data.get('node_type', 'unknown')
            label = data.get('name', str(node))[:30]
            title = f"Type: {node_type}\nID: {node}\n\n{str(data)}"
            net.add_node(node, label=label, color=color_map.get(node_type, '#95a5a6'), title=title)

        for source, target, data in subgraph.edges(data=True):
            net.add_edge(source, target, title=data.get('relationship', ''))

        net.set_options('{"physics": {"stabilization": {"iterations": 100}}}')
        try:
            with open(output_file, "w", encoding="utf-8") as file:
                file.write(net.html)
            return f"Knowledge graph visualization saved to '{output_file}'"
        except Exception as e:
            self.logger.error(f"Error writing visualization file: {e}")
            return f"Error writing visualization file: {e}"

    def get_stats(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM interactions")
        interaction_count = cursor.fetchone()[0]
        return {'documents': doc_count, 'chunks_in_db': self.collection.count(),
                'interactions': interaction_count, 'kg_nodes': self.knowledge_graph.number_of_nodes(),
                'kg_edges': self.knowledge_graph.number_of_edges(), 'collection_name': self.collection_name}

    def save_data(self):
        """Save knowledge graph to disk."""
        kg_path = f"{self.knowledge_graph_path.replace('.json', '')}_{self.collection_name}.json"
        graph_data = nx.node_link_data(self.knowledge_graph)
        with open(kg_path, 'w') as f:
            json.dump(graph_data, f, indent=2)

    def clear_database(self, collection_name: str):
        self.chroma_client.delete_collection(name=collection_name)
        self.knowledge_graph.clear()
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM interactions")
        cursor.execute("DELETE FROM documents")
        self.conn.commit()
        kg_path = f"{self.knowledge_graph_path.replace('.json', '')}_{collection_name}.json"
        if os.path.exists(kg_path):
            os.remove(kg_path)
        self.logger.info(f"Database collection '{collection_name}' cleared successfully.")


@mcp.tool()
def knowledge_base_manager_tool(
        action: str,
        collection_name: str = "default_collection",
        **kwargs: Any
) -> str:
    """
    A unified tool to manage the RAG knowledge base.
    It can perform the following actions:
    - 'ingest_document': Ingest a document from a file path. Requires 'file_path' in kwargs.
    - 'ingest_text': Ingest a piece of text. Requires 'text' in kwargs.
    - 'query': Query the knowledge base. Requires 'query_text' in kwargs.
    - 'get_stats': Get statistics about the knowledge base.
    - 'visualize': Generate a visualization of the knowledge graph.
    - 'clear': Clear a knowledge base collection. Requires 'confirm=True' in kwargs.

    Args:
        action (str): The action to perform, passed by the agent.
        collection_name (str): The name of the knowledge base collection, passed by the agent.
        **kwargs: Additional arguments for the specific action, all provided by the agent.
    """
    rag_core = RAGKnowledgeGraphCore(collection_name=collection_name)

    # All inputs like file_path, text, and query_text are now expected to be in kwargs,
    # which are dynamically populated by the agent calling the tool.
    if action == 'ingest_document':
        file_path = kwargs.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return f"Error: Agent must provide a valid 'file_path'. Path '{file_path}' not found."
        metadata = kwargs.get('metadata', {})
        doc_id = rag_core.ingest_document(file_path, metadata)
        return f"Document '{os.path.basename(file_path)}' ingested with ID: {doc_id}"

    elif action == 'ingest_text':
        text = kwargs.get('text')
        if not text:
            return "Error: Agent must provide non-empty 'text' to ingest."
        metadata = kwargs.get('metadata', {})
        doc_id = rag_core.ingest_text_idea(text, metadata)
        return f"Text ingested with ID: {doc_id}"

    elif action == 'query':
        query_text = kwargs.get('query_text')
        if not query_text:
            return "Error: Agent must provide 'query_text'."
        top_k = kwargs.get('top_k', 5)
        result = rag_core.query(query_text, top_k)
        return json.dumps(result)

    elif action == 'get_stats':
        stats = rag_core.get_stats()
        return json.dumps(stats)

    elif action == 'visualize':
        output_file = kwargs.get('output_file')
        max_nodes = kwargs.get('max_nodes', 150)
        return rag_core.visualize_knowledge_graph(output_file, max_nodes)

    elif action == 'clear':
        confirm = kwargs.get('confirm', False)
        if not confirm:
            return "Error: Agent must set confirm=True to clear the database."
        rag_core.clear_database(collection_name)
        return f"Knowledge base collection '{collection_name}' cleared successfully."

    else:
        return f"Error: Agent provided an unknown action '{action}'"
    

if __name__ == "__main__":
    mcp.run(transport="stdio")
