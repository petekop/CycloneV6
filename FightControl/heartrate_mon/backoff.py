from __future__ import annotations

import asyncio
import random
from typing import Awaitable, Callable, Optional

StatusCB = Callable[[str], None]

async def retry_async(
    operation: Callable[[], Awaitable],
    *,
    status_update: Optional[StatusCB] = None,
    logger=None,
    initial_delay: float = 5.0,
    max_delay: float = 30.0,
    factor: float = 1.5,
    jitter: float = 0.1,   # ±10%
    max_attempts: Optional[int] = None,
):
    """
    Retry an async operation with backoff. On exceptions (excluding cancellation),
    wait and retry. status_update, if provided, is called with human text.
    """
    attempt = 0
    delay = initial_delay
    while True:
        attempt += 1
        try:
            return await operation()
        except asyncio.CancelledError:
            # Graceful shutdown
            raise
        except Exception as e:
            if logger:
                try:
                    logger.warning("Attempt %s failed: %s", attempt, getattr(e, "args", e))
                except Exception:
                    pass
            if max_attempts is not None and attempt >= max_attempts:
                if logger:
                    try:
                        logger.error("Giving up after %s attempts.", attempt)
                    except Exception:
                        pass
                raise
            # Backoff message
            if status_update:
                try:
                    status_update(f"RETRYING in {int(delay)}s")
                except Exception:
                    pass
            # Sleep with jitter
            j = delay * jitter
            sleep_for = max(0.0, delay + random.uniform(-j, j))
            await asyncio.sleep(sleep_for)
            delay = min(max_delay, delay * factor)
