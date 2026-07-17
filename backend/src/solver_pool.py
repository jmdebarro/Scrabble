from __future__ import annotations

import json
import os
import queue
import selectors
import subprocess
import threading
from pathlib import Path
from typing import Any


class SolverError(RuntimeError):
    pass


class SolverProcess:
    def __init__(self, executable: Path, working_directory: Path):
        self.executable = executable
        self.working_directory = working_directory
        self.process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        if not self.executable.exists():
            raise SolverError(f"Solver binary is missing: {self.executable}")
        self.process = subprocess.Popen(
            [str(self.executable)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.working_directory,
            text=True,
            bufsize=1,
        )

    def solve(self, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        for attempt in range(2):
            self.start()
            assert self.process is not None and self.process.stdin and self.process.stdout
            try:
                self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
                self.process.stdin.flush()
                selector = selectors.DefaultSelector()
                selector.register(self.process.stdout, selectors.EVENT_READ)
                try:
                    if not selector.select(timeout):
                        raise SolverError(f"Solver exceeded its {timeout:g}-second timeout.")
                finally:
                    selector.close()
                response = self.process.stdout.readline()
                if not response:
                    detail = self.process.stderr.read().strip() if self.process.stderr else ""
                    raise SolverError(detail or "Solver exited without returning a move.")
                return json.loads(response)
            except (BrokenPipeError, OSError, ValueError, SolverError):
                self.stop()
                if attempt == 1:
                    raise
        raise SolverError("Solver request failed.")

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None


class SolverPool:
    def __init__(self, size: int | None = None):
        source_directory = Path(__file__).resolve().parent
        configured_size = size or int(os.environ.get("SCRABBLE_SOLVER_POOL_SIZE", "2"))
        self.timeout = float(os.environ.get("SCRABBLE_SOLVER_TIMEOUT", "15"))
        self.processes = [
            SolverProcess(source_directory / "gaddag_solver", source_directory)
            for _ in range(max(1, configured_size))
        ]
        self.available: queue.LifoQueue[SolverProcess] = queue.LifoQueue()
        for process in self.processes:
            self.available.put(process)
        self._closed = False
        self._close_lock = threading.Lock()

    def solve(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise SolverError("Solver pool is closed.")
        try:
            process = self.available.get(timeout=self.timeout)
        except queue.Empty as exc:
            raise SolverError("All bot workers are busy.") from exc
        try:
            return process.solve(payload, self.timeout)
        finally:
            self.available.put(process)

    def close(self) -> None:
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
            for process in self.processes:
                process.stop()
