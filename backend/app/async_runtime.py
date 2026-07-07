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
    try:
        loop.run_forever()
    finally:
        _cancel_pending_tasks(loop)
        loop.close()


def _cancel_pending_tasks(loop: asyncio.AbstractEventLoop) -> None:
    pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
    for task in pending:
        task.cancel()
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.run_until_complete(loop.shutdown_asyncgens())


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


def reset_async_runtime() -> None:
    global _loop, _thread
    with _lock:
        loop = _loop
        _loop = None
        _thread = None
    if loop is None or loop.is_closed():
        return
    try:
        loop.call_soon_threadsafe(loop.stop)
    except RuntimeError:
        pass
