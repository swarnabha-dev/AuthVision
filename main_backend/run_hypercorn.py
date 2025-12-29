import asyncio
import os
import sys
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Ensure current working directory is on sys.path so imports resolve correctly
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

try:
    from main_backend.main import app
except Exception:
    import importlib
    mod = importlib.import_module('main_backend.main')
    app = getattr(mod, 'app')


async def main():
    bind = os.environ.get('HYPERCORN_BIND', '0.0.0.0:8002')
    cfg = Config()
    cfg.bind = [bind]
    await serve(app, cfg)


if __name__ == '__main__':
    asyncio.run(main())
