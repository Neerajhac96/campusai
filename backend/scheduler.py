import os
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from database import execute, fetch_all, log_audit
from ingest import ingest_document


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

_scheduler: AsyncIOScheduler | None = None


def _resolve_upload_dir() -> Path:
    path = Path(UPLOAD_DIR)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


async def reindex_auto_refresh_documents() -> None:
    documents = await fetch_all(
        """
        SELECT id, college_id, file_name, original_name, category
        FROM documents
        WHERE auto_refresh = 1
        """
    )

    if not documents:
        await log_audit("scheduler_reindex", '{"message":"No auto_refresh documents found"}')
        return

    upload_dir = _resolve_upload_dir()
    successes = 0
    failures = 0
    for item in documents:
        file_path = upload_dir / item["file_name"]
        if not file_path.exists():
            failures += 1
            continue

        result = await ingest_document(
            file_path=str(file_path),
            college_id=item["college_id"],
            doc_id=item["id"],
            doc_name=item["original_name"],
            category=item["category"],
        )
        if result["success"]:
            successes += 1
            await execute(
                """
                UPDATE documents
                SET status = ?, chunk_count = ?, last_indexed = ?
                WHERE id = ?
                """,
                (
                    "active",
                    result["chunks"],
                    datetime.now(timezone.utc).isoformat(),
                    item["id"],
                ),
            )
        else:
            failures += 1
            await execute(
                """
                UPDATE documents
                SET status = ?, last_indexed = ?
                WHERE id = ?
                """,
                (
                    "error",
                    datetime.now(timezone.utc).isoformat(),
                    item["id"],
                ),
            )

    await log_audit(
        "scheduler_reindex",
        (
            f'{{"message":"Auto refresh completed","total":{len(documents)},'
            f'"successes":{successes},"failures":{failures}}}'
        ),
    )


async def cleanup_temp_uploads() -> None:
    upload_dir = _resolve_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).timestamp()
    deleted_count = 0

    for file_path in upload_dir.iterdir():
        if not file_path.is_file():
            continue
        file_age_seconds = now - file_path.stat().st_mtime
        if file_age_seconds > 3600:
            file_path.unlink(missing_ok=True)
            deleted_count += 1

    await log_audit(
        "scheduler_cleanup_uploads",
        f'{{"message":"Upload cleanup completed","deleted_files":{deleted_count}}}',
    )


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = AsyncIOScheduler()
    scheduler.add_job(reindex_auto_refresh_documents, trigger="cron", hour=2, minute=0)
    scheduler.add_job(cleanup_temp_uploads, trigger="cron", minute=0)
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
