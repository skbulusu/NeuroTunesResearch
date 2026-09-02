# ====================================================================
# gunicorn.conf.py  —  Production WSGI server config for NeuroTunes ML
# --------------------------------------------------------------------
# Usage (see Dockerfile.netraiML):
#   gunicorn -c gunicorn.conf.py wsgi:app
#
# Design notes:
#  * workers = 1 (IMPORTANT). app.py starts a background retraining
#    scheduler thread and (in coordinator mode) an in-process federation
#    coordinator holding round state in memory. Running multiple worker
#    processes would spawn duplicate schedulers and fragment that state.
#    A single worker with multiple THREADS preserves the exact runtime
#    behaviour of the previous `flask run` dev server while still giving
#    real production hardening (process supervision, graceful timeouts,
#    request limits) over the Werkzeug dev server.
#  * All values are overridable via environment variables so the same
#    image works across the web-ml machine and any future scaling.
# ====================================================================

import os

# Network
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Concurrency — single process, multiple threads (see note above).
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")

# Preload the app so the scheduler/federation init runs once in the master
# before workers are forked (harmless with a single worker, correct if the
# operator ever raises the worker count for a stateless deployment).
preload_app = os.getenv("GUNICORN_PRELOAD", "true").lower() in ("1", "true", "yes")

# Timeouts — music generation + MIDI synthesis can take a few seconds.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Recycle workers periodically to bound memory growth from ML libs.
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# Logging to stdout/stderr for docker log drivers.
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
