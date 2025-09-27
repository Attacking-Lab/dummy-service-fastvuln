import multiprocessing
from os import environ

worker_class = "uvicorn.workers.UvicornWorker"
default_workers = min(8, multiprocessing.cpu_count())
workers = int(environ.get("WORKER_COUNT", default_workers))
bind = "0.0.0.0:8000"
timeout = int(environ.get("WORKER_TIMEOUT", 90))
keepalive = 3600
preload_app = True
