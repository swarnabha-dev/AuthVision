"""Run the `app` via Hypercorn with graceful shutdown.

Usage:
  python -m model_service.run_hypercorn

Optional environment variable:
  HYPERCORN_BIND  - bind address (default: "localhost:8080")
"""
import asyncio
import signal
import os
from typing import Any

from hypercorn.config import Config
from hypercorn.asyncio import serve

# Import the FastAPI app. Use absolute import so the script can be executed
# directly (python model_service/run_hypercorn.py) or as a module.
try:
    # Preferred absolute import when the project root is on sys.path
    from model_service.main import app
except Exception:
    # Fallback: try relative import when running as a package
    try:
        from .main import app  # type: ignore
    except Exception:
        # Last resort: import via importlib after ensuring cwd is on sys.path
        import importlib
        import sys
        import os

        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())
        mod = importlib.import_module("model_service.main")
        app = getattr(mod, "app")


async def main() -> None:
    bind = os.environ.get("HYPERCORN_BIND", "localhost:8080")
    config = Config()
    config.bind = [bind]

    shutdown_event: asyncio.Event = asyncio.Event()

    def _signal_handler(*_: Any) -> None:
        # set the event to trigger shutdown
        shutdown_event.set()

    loop = asyncio.get_event_loop()

    # Prefer add_signal_handler (not available in some Windows loops)
    try:
        loop.add_signal_handler(signal.SIGINT, _signal_handler)
        loop.add_signal_handler(signal.SIGTERM, _signal_handler)
    except (NotImplementedError, AttributeError):
        # Fallback for Windows where add_signal_handler may not be implemented
        signal.signal(signal.SIGINT, lambda *_: _signal_handler())
        try:
            signal.signal(signal.SIGTERM, lambda *_: _signal_handler())
        except Exception:
            # Some Windows environments may not support SIGTERM
            pass

    # Run Hypercorn and pass the shutdown trigger (waits until event is set)
    await serve(app, config, shutdown_trigger=shutdown_event.wait)


if __name__ == "__main__":
    asyncio.run(main())
