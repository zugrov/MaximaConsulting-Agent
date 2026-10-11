from __future__ import annotations

import time
from typing import Callable, Dict, List, Tuple

MAX_TRACKED_KEYS = 10_000


class LoginLimiter:
    """Ограничивает неудачные попытки входа: на пару (ip, email) и на ip целиком.

    Состояние хранится в памяти процесса: backend запускается одним воркером uvicorn,
    после перезапуска счётчики обнуляются.
    """

    def __init__(
        self,
        max_per_account: int = 5,
        max_per_ip: int = 20,
        window_sec: int = 900,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_per_account = max_per_account
        self.max_per_ip = max_per_ip
        self.window_sec = window_sec
        self.clock = clock
        self._failures: Dict[Tuple[str, str], List[float]] = {}

    def _recent(self, key: Tuple[str, str]) -> List[float]:
        threshold = self.clock() - self.window_sec
        recent = [t for t in self._failures.get(key, []) if t > threshold]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def retry_after(self, ip: str, email: str) -> int:
        """Секунд до разблокировки; 0, если вход разрешён."""
        waits = []
        for key, limit in (
            (("acc", f"{ip}|{email.lower()}"), self.max_per_account),
            (("ip", ip), self.max_per_ip),
        ):
            recent = self._recent(key)
            if len(recent) >= limit:
                waits.append(int(self.window_sec - (self.clock() - recent[0])) + 1)
        return max(waits, default=0)

    def register_failure(self, ip: str, email: str) -> None:
        if len(self._failures) > MAX_TRACKED_KEYS:
            for key in list(self._failures):
                self._recent(key)
        now = self.clock()
        for key in (("acc", f"{ip}|{email.lower()}"), ("ip", ip)):
            self._failures.setdefault(key, []).append(now)

    def reset_account(self, ip: str, email: str) -> None:
        self._failures.pop(("acc", f"{ip}|{email.lower()}"), None)
