# import os
import multiprocessing

workers = multiprocessing.cpu_count()
max_requests = 10000
timeout = 60
# loglevel = 'debug'
# accesslog = os.path.expanduser("~/paddles.access.log")
# errorlog = os.path.expanduser("~/paddles.error.log")
