"""
rag_service.py
---------------
Retrieval-Augmented Generation pipeline:
  PDF upload -> text extraction (pypdf) -> chunking (LangChain splitter)
  -> embeddings -> ChromaDB vector store -> similarity search at query time.

Each uploaded document gets its own Chroma "collection" so retrieval stays
scoped to the document(s) a chat session is linked to.
"""
import os
import uuid
from flask import current_app


class RAGServiceError(Exception):
    pass


def _get_embedding_function():
    """
    Uses a local sentence-transformer embedding model via Chroma's default
    embedding function so RAG works even without a paid embeddings API.
    """
    from chromadb.utils import embedding_functions
    return embedding_functions.DefaultEmbeddingFunction()


def _get_chroma_client():
    import chromadb
    persist_dir = current_app.config["CHROMA_PERSIST_DIR"]
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def extract_text_from_pdf(filepath: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RAGServiceError("pypdf is not installed.") from e

    reader = PdfReader(filepath)
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    text = "\n".join(text_parts).strip()

    if not text:
        raise RAGServiceError(
            "No extractable text found in this PDF (it may be a scanned image)."
        )
    return text


def chunk_text(text: str) -> list[str]:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as e:
        raise RAGServiceError("langchain-text-splitters is not installed.") from e

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=current_app.config["CHUNK_SIZE"],
        chunk_overlap=current_app.config["CHUNK_OVERLAP"],
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def ingest_document(filepath: str, filename: str, user_id: int) -> dict:
    """
    Full ingestion pipeline for one uploaded PDF.
    Returns {"collection_name": str, "chunk_count": int}
    """
    text = extract_text_from_pdf(filepath)
    chunks = chunk_text(text)
    if not chunks:
        raise RAGServiceError("Document produced no usable chunks after splitting.")

    collection_name = f"user{user_id}_{uuid.uuid4().hex[:10]}"

    client = _get_chroma_client()
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=_get_embedding_function(),
        metadata={"source_filename": filename, "user_id": str(user_id)},
    )

    ids = [f"{collection_name}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"chunk_index": i, "source": filename} for i in range(len(chunks))]

    # Batch add (Chroma handles embedding generation internally)
    collection.add(documents=chunks, ids=ids, metadatas=metadatas)

    return {"collection_name": collection_name, "chunk_count": len(chunks)}


def retrieve_context(collection_name: str, query: str, k: int | None = None) -> str:
    """Retrieve the top-k most relevant chunks for a query and join them
    into a single context block for the LLM prompt."""
    k = k or current_app.config["RETRIEVAL_K"]
    client = _get_chroma_client()

    try:
        collection = client.get_collection(
            name=collection_name, embedding_function=_get_embedding_function()
        )
    except Exception as e:
        raise RAGServiceError(f"Vector collection '{collection_name}' not found.") from e

    results = collection.query(query_texts=[query], n_results=k)
    documents = results.get("documents", [[]])[0]

    if not documents:
        return ""

    return "\n\n---\n\n".join(documents)


def delete_document_collection(collection_name: str) -> None:
    try:
        client = _get_chroma_client()
        client.delete_collection(name=collection_name)
    except Exception:
        pass  # best-effort cleanup