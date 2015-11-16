import logging

from paddles.controllers.jobs import QueuedJobsController
from paddles.controllers.runs import QueuedRunsController

log = logging.getLogger(__name__)


class QueueController(object):

    jobs = QueuedJobsController()

    runs = QueuedRunsController()
