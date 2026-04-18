from __future__ import annotations

from pathlib import Path
from threading import Lock, Thread, current_thread
from typing import Callable

from backend.app.core.logging import get_app_logger, log_event
from backend.app.services.processing_service import ProcessingService


class InProcessBatchRunner:
    def __init__(
        self, *, session_factory: Callable[[], object], storage_root: Path | str
    ) -> None:
        self.session_factory = session_factory
        self.storage_root = Path(storage_root)
        self.logger = get_app_logger("processing_runner")
        self._lock = Lock()
        self._threads: dict[str, Thread] = {}

    def enqueue(self, batch_id: str) -> bool:
        with self._lock:
            current = self._threads.get(batch_id)
            if current is not None and current.is_alive():
                return False
            worker = Thread(
                target=self._run_batch,
                args=(batch_id,),
                name=f"batch-runner-{batch_id}",
                daemon=True,
            )
            self._threads[batch_id] = worker
            worker.start()
            return True

    def shutdown(self) -> None:
        with self._lock:
            finished = [
                batch_id
                for batch_id, thread in self._threads.items()
                if not thread.is_alive()
            ]
            for batch_id in finished:
                self._threads.pop(batch_id, None)

    def _run_batch(self, batch_id: str) -> None:
        session = self.session_factory()
        try:
            log_event(self.logger, "batch_enqueued", batch_id=batch_id)
            ProcessingService(
                session=session, storage_root=self.storage_root
            ).process_batch(batch_id)
            log_event(self.logger, "batch_completed", batch_id=batch_id)
        except Exception as exc:
            self.logger.exception(
                "batch processing crashed",
                extra={"batch_id": batch_id, "error": str(exc)},
            )
        finally:
            session.close()
            with self._lock:
                thread = self._threads.get(batch_id)
                if thread is not None and thread is current_thread():
                    self._threads.pop(batch_id, None)
