# Hypercorn 0.18.0 Configuration for Production
# Usage: hypercorn -c hypercorn_config.py main:app

import multiprocessing
import os

# Server Socket
bind = [f"{os.getenv('BACKEND_HOST', '0.0.0.0')}:{os.getenv('BACKEND_PORT', '8000')}"]

# Worker Processes (for production, use multiple workers)
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "asyncio"

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stdout
loglevel = os.getenv('LOG_LEVEL', 'info')

# Keep-alive
keep_alive_timeout = 5

# Timeouts
graceful_timeout = 10
shutdown_timeout = 60

# Connection limits
backlog = 100

# HTTP/2 Support (Hypercorn 0.18.0)
alpn_protocols = ["h2", "http/1.1"]

# WebSocket Configuration (Improved in 0.18.0)
websocket_ping_interval = 20  # seconds
websocket_max_message_size = 16 * 1024 * 1024  # 16MB

# SSL/TLS (uncomment for HTTPS)
# certfile = "/path/to/cert.pem"
# keyfile = "/path/to/key.pem"

# Performance tuning
# worker_connections = 1000
# max_requests = 10000  # Restart worker after this many requests
# max_requests_jitter = 1000

# Development mode
if os.getenv('DEBUG', 'false').lower() == 'true':
    use_reloader = True
    reload_includes = ["*.py", ".env"]
    loglevel = "debug"
