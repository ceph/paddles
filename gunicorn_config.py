import os
import multiprocessing

workers = os.environ.get("PADDLES_WORKER_COUNT", multiprocessing.cpu_count())
max_requests = 10000
timeout = 60
# loglevel = 'debug'
# accesslog = os.path.expanduser("~/paddles.access.log")
# errorlog = os.path.expanduser("~/paddles.error.log")
