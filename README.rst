paddles
=======
A very simple ``JSON`` based API to store and report back on test
results from Ceph tests.


``/runs/``
========

Read
----
On ``GET`` operations it will display the latest 100 runs with a ``JSON``
object of all recent jobs reported.

::

    {
        "teuthology-2013-09-25_23:00:06-rados-master-testing-basic-plana": {
            "href": "http://paddles/runs/teuthology-2013-09-25_23:00:06-rados-master-testing-basic-plana/",
            "status": "pass"
        },
        "teuthology-2013-09-26_01:30:26-upgrade-fs-next-testing-basic-plana": {
            "href": "http://paddles/teuthology-2013-09-26_01:30:26-upgrade-fs-next-testing-basic-plana",
            "status": "failed"
        },
        "teuthology-2013-09-26_01:30:26-rados-next-testing-basic-plana": {
            "href": "http://paddles/runs/teuthology-2013-09-26_01:30:26-rados-next-testing-basic-plana/",
            "status": "pending"
        }
    }

The example above gives returns the three statuses available for jobs:
``pass``, ``failed``, and ``pending`` with its respective links.

Create
------
These operations *create* new entries for runs, it is only required to ``POST``
a ``JSON`` object that has a name key and the actual name of the run as the
value::

    { "name": "teuthology-2013-09-01_23:59:59-rados-master-testing-basic-plana" }

HTTP responses:

* **200**: Success.
* **400**: Invalid request.


``/runs/{name}/``
=================

Read
----
To read information for a specific run a ``GET`` needs to be requested. On
valid requests (for existing runs) a ``JSON`` object with all the jobs
scheduled for that specific run are returned. Below is an example of a valid
request::

    {
        "1500": {
            "href": "http://paddles/runs/foo/1500/",
            "status": "pass"
        },
        "1501": {
            "href": "http://paddles/runs/foo/1501/",
            "status": "failed"
        },
        "1502": {
            "href": "http://paddles/runs/foo/1502/",
            "status": "pending"
        }
    }

    

HTTP responses:

* **200**: Success.
* **404**: The requested run was not found.


Update
------
For updates to the status of a run clients should send a ``PUT`` request with
the new status of the run. By default all new runs are created with
a ``"pending"`` status. A valid ``JSON`` object for this operation would look
like::

    { "status": "failed" }


* **200**: Success.
* **400**: Invalid request.
* **404**: The requested run was not found.


jobs
====

Read
----

Create
------

Update
------

