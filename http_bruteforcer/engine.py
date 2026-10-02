"""Asynchronous worker pool, work queue manager, and execution engine."""

from __future__ import annotations

import asyncio
from typing import Iterator, List, Optional

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from http_bruteforcer.analyzer import Analyzer
from http_bruteforcer.models import EndpointResult
from http_bruteforcer.reporter import Reporter
from http_bruteforcer.requester import Requester


class BruteForceEngine:
    """Coordinates producer-consumer pipeline with asyncio.Queue and concurrency pool."""

    def __init__(
        self,
        requester: Requester,
        analyzer: Analyzer,
        reporter: Reporter,
        concurrency: int = 50,
        queue_size: int = 2000,
        show_progress: bool = True,
    ):
        self.requester = requester
        self.analyzer = analyzer
        self.reporter = reporter
        self.concurrency = max(1, concurrency)
        self.queue_size = max(100, queue_size)
        self.show_progress = show_progress
        self.results: List[EndpointResult] = []

    async def _producer(self, queue: asyncio.Queue[Optional[str]], paths_generator: Iterator[str]) -> None:
        """Stream paths from generator into the bounded queue."""
        for path in paths_generator:
            await queue.put(path)
        # Put sentinels to signal all workers to exit
        for _ in range(self.concurrency):
            await queue.put(None)

    async def _worker(
        self,
        queue: asyncio.Queue[Optional[str]],
        progress: Optional[Progress],
        task_id: Optional[int],
    ) -> None:
        """Worker task consuming paths from queue, making requests, and analyzing responses."""
        while True:
            path = await queue.get()
            if path is None:
                queue.task_done()
                break

            try:
                res = await self.requester.request(path)
                if res is not None:
                    # Note: filter_regex check if needed
                    if self.analyzer.is_valid(res):
                        self.results.append(res)
                        if progress is not None:
                            # Print through progress console to keep bar clean
                            old_console = self.reporter.console
                            self.reporter.console = progress.console
                            self.reporter.print_result_line(res)
                            self.reporter.console = old_console
                        else:
                            self.reporter.print_result_line(res)
            except Exception:
                pass
            finally:
                queue.task_done()
                if progress is not None and task_id is not None:
                    progress.advance(task_id, 1)

    async def run(
        self,
        paths_generator: Iterator[str],
        total_count: Optional[int] = None,
    ) -> List[EndpointResult]:
        """Execute the brute-force scan across the supplied paths."""
        self.results.clear()
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue(maxsize=self.queue_size)

        if self.show_progress:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}[/bold blue]"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=self.reporter.console,
                transient=False,
            )
            progress.start()
            task_id = progress.add_task("Scanning endpoints", total=total_count)
        else:
            progress = None
            task_id = None

        producer_task = asyncio.create_task(self._producer(queue, paths_generator))
        worker_tasks = [
            asyncio.create_task(self._worker(queue, progress, task_id))
            for _ in range(self.concurrency)
        ]

        try:
            await producer_task
            await queue.join()
            await asyncio.gather(*worker_tasks)
        except (asyncio.CancelledError, KeyboardInterrupt):
            producer_task.cancel()
            for w in worker_tasks:
                w.cancel()
            await asyncio.gather(*worker_tasks, return_exceptions=True)
            raise
        finally:
            if progress is not None:
                progress.stop()

        return self.results
