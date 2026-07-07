import asyncio
from collections.abc import Coroutine
from concurrent.futures import TimeoutError as FutureTimeoutError
from threading import Lock, Thread
from typing import Any, TypeVar

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None
_thread: Thread | None = None
_lock = Lock()


def _run_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop, _thread
    with _lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            _thread = Thread(target=_run_loop, args=(_loop,), daemon=True)
            _thread.start()
        return _loop


def run_async(coro: Coroutine[Any, Any, T], *, timeout: float | None = None) -> T:
    future = asyncio.run_coroutine_threadsafe(coro, _get_loop())
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        future.cancel()
        raise
    except BaseException:
        future.cancel()
        raise
