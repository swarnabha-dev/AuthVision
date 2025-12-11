"""Package entry point for running the model_service via ``python -m model_service``.

This simply delegates to the existing `run_hypercorn.main()` coroutine so the
service can be started from the package namespace. Using ``-u`` with Python
only affects IO buffering and works the same; for example:

  python -m model_service
  python -u -m model_service

"""
import asyncio

# Try relative import when executed as a package (python -m model_service).
# If the file is executed directly (python model_service), fall back to an
# absolute import via importlib so the module can be found when cwd is on sys.path.
try:
  from .run_hypercorn import main
except Exception:
  # Fallback: import by module name
  import importlib, sys, os

  if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())
  mod = importlib.import_module("model_service.run_hypercorn")
  main = getattr(mod, "main")


def _main() -> None:
  asyncio.run(main())


if __name__ == "__main__":
  _main()
