"""Interface for communicating with external Stratego bots."""

from __future__ import annotations

import select
import subprocess
from typing import List, Optional


class BotController:
    """Wraps a subprocess running a Stratego bot following the evaluator protocol."""

    def __init__(self, bot_path: str, name: str, timeout: float = 2.0) -> None:
        self.name = name
        self.timeout = timeout
        self.process = subprocess.Popen(
            [bot_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,  # line buffering
        )

    # ------------------------------------------------------------------
    # utility helpers
    def _send_line(self, line: str) -> None:
        if self.process.stdin is None:
            return
        try:
            self.process.stdin.write(line + "\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            pass

    def _read_line(self, timeout: Optional[float] = None) -> Optional[str]:
        if timeout is None:
            timeout = self.timeout
        assert self.process.stdout is not None
        rlist, _, _ = select.select([self.process.stdout], [], [], timeout)
        if rlist:
            return self.process.stdout.readline().rstrip("\n")
        return None

    def _read_lines(self, count: int, timeout: Optional[float] = None) -> List[str]:
        """Read a fixed number of lines, waiting for the first one."""

        first = self._read_line(timeout)
        if first is None:
            raise TimeoutError("Bot did not respond in time")

        lines = [first]
        for _ in range(count - 1):
            line = self.process.stdout.readline().rstrip("\n")
            if line == "":
                raise TimeoutError("Bot closed the pipe unexpectedly")
            lines.append(line)
        return lines

    # ------------------------------------------------------------------
    # protocol steps
    def setup(self, color: str, width: int, height: int, opponent: str = "bot") -> str:
        """Send setup information and read the placement response."""

        self._send_line(f"{color} {opponent} {width} {height}")
        rows = self._read_lines(4)
        return "\n".join(rows)

    def request_move(self, last_move: str, outcome: str, board_state: List[str]) -> str:
        """Request a move from the bot given the current board."""

        if last_move == "START":
            self._send_line("START")
        else:
            self._send_line(f"{last_move} {outcome}")
        for row in board_state:
            self._send_line(row)
        line = self._read_line()
        if line is None:
            raise TimeoutError("Bot did not return a move")
        return line

    def confirm_result(self, move: str, outcome: str) -> None:
        """Send the outcome of the previously issued move."""

        self._send_line(f"{move} {outcome}")

    def end_game(self, result: str = "") -> None:
        """Terminate the bot process by sending QUIT."""

        if result:
            self._send_line(f"QUIT {result}")
        else:
            self._send_line("QUIT")
        try:
            self.process.terminate()
            self.process.wait(timeout=0.5)
        except Exception:
            pass

