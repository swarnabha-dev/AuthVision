"""Module entrypoint for `python -m main_backend`.

This will start the Hypercorn runner defined in run_hypercorn.py.
"""
import asyncio
import sys

try:
    from .run_hypercorn import main as _main
except Exception:
    # If package run as module from elsewhere, ensure CWD on sys.path then import
    import importlib
    if "" not in sys.path:
        sys.path.insert(0, "")
    mod = importlib.import_module("main_backend.run_hypercorn")
    _main = getattr(mod, "main")


if __name__ == "__main__":
    asyncio.run(_main())
