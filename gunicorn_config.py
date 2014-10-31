import os
import multiprocessing
_home = os.environ['HOME']

workers = multiprocessing.cpu_count() * 2
workers = 10
max_requests = 10000
#loglevel = 'debug'
accesslog = os.path.join(_home, "paddles.access.log")
#errorlog = os.path.join(_home, "paddles.error.log")
