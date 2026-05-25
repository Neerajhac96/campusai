import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
from dotenv import load_dotenv

try:
    import chromadb  # type: ignore
except Exception:  # noqa: BLE001
    chromadb = None

try:
    import fitz  # type: ignore
except Exception:  # noqa: BLE001
    fitz = None

try:
    from docx import Document as DocxDocument
except Exception:  # noqa: BLE001
    DocxDocument = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # noqa: BLE001
    SentenceTransformer = None  # type: ignore


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = os.getenv("CHROMA_DIR", "./db")
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

_embedding_model: Any | None = None
_chroma_client: Any | None = None
_fallback_store_lock = Lock()


def _resolve_dir(path_value: str) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str((BASE_DIR / path).resolve())


class LocalPersistentCollection:
    def __init__(self, store_file: Path, collection_name: str):
        self.store_file = store_file
        self.collection_name = collection_name

    def _load_store(self) -> dict[str, Any]:
        if not self.store_file.exists():
            return {"collections": {}}
        try:
            return json.loads(self.store_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {"collections": {}}

    def _save_store(self, data: dict[str, Any]) -> None:
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        self.store_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def add(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        with _fallback_store_lock:
            store = self._load_store()
            collections = store.setdefault("collections", {})
            items = collections.setdefault(self.collection_name, [])
            ids_set = set(ids)
            items = [item for item in items if item["id"] not in ids_set]

            for idx, entry_id in enumerate(ids):
                items.append(
                    {
                        "id": entry_id,
                        "document": documents[idx],
                        "embedding": [float(v) for v in embeddings[idx]],
                        "metadata": metadatas[idx],
                    }
                )

            collections[self.collection_name] = items
            self._save_store(store)

    def delete(self, where: dict[str, Any] | None = None) -> None:
        with _fallback_store_lock:
            store = self._load_store()
            collections = store.setdefault("collections", {})
            items = collections.setdefault(self.collection_name, [])
            if not where:
                collections[self.collection_name] = []
                self._save_store(store)
                return

            doc_id = where.get("doc_id")
            if doc_id is not None:
                items = [item for item in items if item.get("metadata", {}).get("doc_id") != doc_id]
            collections[self.collection_name] = items
            self._save_store(store)

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int = 6,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        include = include or ["documents", "metadatas", "distances"]
        with _fallback_store_lock:
            store = self._load_store()
            items = store.get("collections", {}).get(self.collection_name, [])

        if not items:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        documents_result: list[list[str]] = []
        metadatas_result: list[list[dict[str, Any]]] = []
        distances_result: list[list[float]] = []
        ids_result: list[list[str]] = []

        embeddings_matrix = np.array([item["embedding"] for item in items], dtype=np.float32)
        doc_norms = np.linalg.norm(embeddings_matrix, axis=1)

        for query_embedding in query_embeddings:
            q = np.array(query_embedding, dtype=np.float32)
            q_norm = float(np.linalg.norm(q))

            if q_norm == 0:
                cosine_similarities = np.zeros(len(items), dtype=np.float32)
            else:
                denom = doc_norms * q_norm
                numer = embeddings_matrix @ q
                cosine_similarities = np.divide(
                    numer,
                    denom,
                    out=np.zeros_like(numer),
                    where=denom != 0,
                )

            distances = 1.0 - cosine_similarities
            ranked_indices = np.argsort(distances)[:n_results]

            ids_result.append([items[i]["id"] for i in ranked_indices])
            documents_result.append([items[i]["document"] for i in ranked_indices])
            metadatas_result.append([items[i]["metadata"] for i in ranked_indices])
            distances_result.append([float(distances[i]) for i in ranked_indices])

        result: dict[str, Any] = {"ids": ids_result}
        if "documents" in include:
            result["documents"] = documents_result
        if "metadatas" in include:
            result["metadatas"] = metadatas_result
        if "distances" in include:
            result["distances"] = distances_result
        return result


def get_embedding_model() -> Any:
    global _embedding_model
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is not installed")
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embedding_model


def get_chroma_client() -> Any | None:
    global _chroma_client
    if chromadb is None or not hasattr(chromadb, "PersistentClient"):
        return None
    if _chroma_client is None and chromadb is not None:
        try:
            resolved = _resolve_dir(CHROMA_DIR)
            Path(resolved).mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=resolved)
        except Exception:  # noqa: BLE001
            _chroma_client = None
    return _chroma_client


def get_collection(college_id: str) -> Any:
    collection_name = f"col_{college_id}"
    client = get_chroma_client()
    if client is not None:
        return client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

    store_file = Path(_resolve_dir(CHROMA_DIR)) / "fallback_vectors.json"
    return LocalPersistentCollection(store_file=store_file, collection_name=collection_name)


def extract_text(file_path: str) -> list[dict[str, Any]]:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return _extract_pdf_text(path)
    if ext == ".docx":
        return _extract_docx_text(path)
    if ext == ".txt":
        return _extract_txt_text(path)
    raise ValueError("Unsupported file type. Allowed: PDF, DOCX, TXT")


def _extract_pdf_text(path: Path) -> list[dict[str, Any]]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")

    pages: list[dict[str, Any]] = []
    with fitz.open(path) as pdf:
        for index, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page": index, "text": text})
    return pages


def _extract_docx_text(path: Path) -> list[dict[str, Any]]:
    if DocxDocument is None:
        raise RuntimeError("python-docx is not installed")

    document = DocxDocument(path)
    combined_lines: list[str] = []
    for paragraph in document.paragraphs:
        value = paragraph.text.strip()
        if value:
            combined_lines.append(value)

    if not combined_lines:
        return []
    return [{"page": 1, "text": "\n".join(combined_lines)}]


def _extract_txt_text(path: Path) -> list[dict[str, Any]]:
    content = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not content:
        return []
    return [{"page": 1, "text": content}]


def smart_chunk(
    pages: list[dict[str, Any]], chunk_size: int = 400, overlap: int = 60
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    step = chunk_size - overlap
    for page_data in pages:
        text = " ".join(page_data["text"].split())
        if not text:
            continue
        words = text.split(" ")
        start = 0
        while start < len(words):
            end = start + chunk_size
            piece_words = words[start:end]
            if not piece_words:
                break
            chunk_text = " ".join(piece_words).strip()
            if len(chunk_text) >= 50:
                chunks.append({"text": chunk_text, "page": page_data["page"]})
            start += step
    return chunks


async def ingest_document(
    file_path: str,
    college_id: str,
    doc_id: str,
    doc_name: str,
    category: str,
) -> dict[str, Any]:
    try:
        pages = await asyncio.to_thread(extract_text, file_path)
        if not pages:
            return {"success": False, "chunks": 0, "message": "No extractable text found in file"}

        chunks = await asyncio.to_thread(smart_chunk, pages)
        if not chunks:
            return {"success": False, "chunks": 0, "message": "No valid chunks generated"}

        texts = [item["text"] for item in chunks]
        model = get_embedding_model()
        embeddings = await asyncio.to_thread(
            model.encode,
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        collection = get_collection(college_id)

        await asyncio.to_thread(collection.delete, where={"doc_id": doc_id})

        timestamp = datetime.now(timezone.utc).isoformat()
        ids = [f"{doc_id}_{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "college_id": college_id,
                "doc_id": doc_id,
                "doc_name": doc_name,
                "category": category,
                "page": chunk["page"],
                "indexed_at": timestamp,
            }
            for chunk in chunks
        ]
        await asyncio.to_thread(
            collection.add,
            ids=ids,
            documents=texts,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )
        return {"success": True, "chunks": len(chunks), "message": "Document indexed successfully"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "chunks": 0, "message": f"Indexing failed: {exc}"}


async def delete_document_vectors(college_id: str, doc_id: str) -> bool:
    try:
        collection = get_collection(college_id)
        await asyncio.to_thread(collection.delete, where={"doc_id": doc_id})
        return True
    except Exception:  # noqa: BLE001
        return False
