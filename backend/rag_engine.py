import os
import time
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from ingest import get_collection, get_embedding_model
from language import build_system_prompt, detect_language, low_confidence_message, no_result_message


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL_NAME = "llama3-8b-8192"
LOW_CONFIDENCE_DISTANCE = 0.82
TOP_K = 6

_groq_client: Groq | None = None


def get_groq_client() -> Groq | None:
    global _groq_client
    if not GROQ_API_KEY:
        return None
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def _format_sources(metadatas: list[dict[str, Any]]) -> list[str]:
    sources: list[str] = []
    for metadata in metadatas:
        doc_name = metadata.get("doc_name", "Unknown Document")
        page = metadata.get("page", "N/A")
        source = f"{doc_name} (Page {page})"
        if source not in sources:
            sources.append(source)
    return sources


def _build_context(documents: list[str], metadatas: list[dict[str, Any]]) -> str:
    context_parts: list[str] = []
    for doc_text, meta in zip(documents, metadatas):
        doc_name = meta.get("doc_name", "Unknown Document")
        page = meta.get("page", "N/A")
        category = meta.get("category", "general")
        context_parts.append(
            f"[Document: {doc_name} | Category: {category} | Page: {page}]\n{doc_text}"
        )
    return "\n\n".join(context_parts)


def _append_source_if_missing(answer: str, sources: list[str]) -> str:
    if not sources:
        return answer
    if "source:" in answer.lower():
        return answer
    return f"{answer.rstrip()}\n\nSource: {', '.join(sources)}"


async def get_answer(query: str, college_id: str, college_name: str) -> dict[str, Any]:
    start_time = time.perf_counter()
    language = detect_language(query)

    try:
        model = get_embedding_model()
        query_embedding = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0].tolist()

        collection = get_collection(college_id)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=TOP_K,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        if not documents:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "answer": no_result_message(language),
                "sources": [],
                "language": language,
                "confidence": "uncertain",
                "escalate": True,
                "response_time_ms": elapsed_ms,
            }

        best_distance = float(distances[0]) if distances else 1.0
        if best_distance > LOW_CONFIDENCE_DISTANCE:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "answer": low_confidence_message(language),
                "sources": _format_sources(metadatas),
                "language": language,
                "confidence": "low",
                "escalate": True,
                "response_time_ms": elapsed_ms,
            }

        sources = _format_sources(metadatas)
        context = _build_context(documents, metadatas)
        system_prompt = build_system_prompt(language=language, college_name=college_name)
        user_prompt = (
            f"Use ONLY this context to answer.\n\nContext:\n{context}\n\n"
            f"Student Question: {query}\n\n"
            "If the exact information is not present, follow the fallback rule from system prompt."
        )

        client = get_groq_client()
        if client is None:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            fallback = (
                "Mujhe pakki jaankari nahi — Admin Office se confirm karein"
                if language == "hindi"
                else "I don't have reliable info on this. Please contact Admin Office"
            )
            return {
                "answer": fallback,
                "sources": sources,
                "language": language,
                "confidence": "uncertain",
                "escalate": True,
                "response_time_ms": elapsed_ms,
            }

        chat_completion = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.1,
            max_tokens=700,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = (chat_completion.choices[0].message.content or "").strip()
        answer = _append_source_if_missing(answer, sources)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "answer": answer,
            "sources": sources,
            "language": language,
            "confidence": "high",
            "escalate": False,
            "response_time_ms": elapsed_ms,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        fallback_answer = (
            "Mujhe temporary technical issue aa rahi hai. Admin Office se confirm karein."
            if language == "hindi"
            else "I am facing a temporary technical issue. Please contact Admin Office."
        )
        return {
            "answer": fallback_answer,
            "sources": [],
            "language": language,
            "confidence": "uncertain",
            "escalate": True,
            "response_time_ms": elapsed_ms,
            "error": str(exc),
        }
