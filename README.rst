paddles
=======
A very simple ``JSON`` based API to store and report back on test
results from Ceph tests.


Setup
=====

To install and use paddles:

#. Install the following packages (names provided are based on an Ubuntu install): ``git python-dev python-virtualenv postgresql postgresql-contrib postgresql-server-dev-all supervisor``
#. Install and configure PostgreSQL on your system.
#. Create a database. Ours is called 'paddles'
#. Clone the `repository <https://github.com/ceph/paddles.git>`_
#. Inside the repository, create a virtualenv: ``virtualenv ./virtualenv``
#. Create a copy of the configuration template: ``cp config.py.in config.py``
#. Edit config.py to reflect your hostnames, database info, etc.
#. Activate the virtualenv: ``source ./virtualenv/bin/activate``
#. Install required python packages: ``pip install -r requirements.txt``
#. Run ``python setup.py develop``
#. Populate the database tables: ``pecan populate config.py``
#. Create a copy of the `alembic <http://alembic.readthedocs.org/en/latest/>`_ configuration template: ``cp alembic.ini.in alembic.ini``
#. Edit alembic.ini to reflect your database information.
#. Tell alembic that you have the latest database version: ``alembic stamp head``
#. To start the server for testing purposes, you may use ``pecan serve config.py`` - though for production use it's wise to use `a real server <http://pecan.readthedocs.org/en/latest/deployment.html>`_. We use `gunicorn <http://gunicorn.org/>`_ managed by `supervisord <http://supervisord.org/>`_. Sample config files are provided for `gunicorn <gunicorn_config.py>`_ and `supervisord <supervisord_paddles.conf>`_.
#. To get `teuthology <https://github.com/ceph/teuthology/>`_ talking to paddles add a line like this to your ``~/.teuthology.yaml``: ``results_server: http://paddles.example.com/``



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
            "status": "running",
            "results": {
                "pass": 10,
                "running": 15,
                "fail": 0
            }
        },
        "teuthology-2013-09-26_01:30:26-upgrade-fs-next-testing-basic-plana": {
            "href": "http://paddles/teuthology-2013-09-26_01:30:26-upgrade-fs-next-testing-basic-plana",
            "status": "running",
            "results": {
                "pass": 3,
                "running": 10,
                "fail": 1
            }
        },
        "teuthology-2013-09-26_01:30:26-rados-next-testing-basic-plana": {
            "href": "http://paddles/runs/teuthology-2013-09-26_01:30:26-rados-next-testing-basic-plana/",
            "status": "finished",
            "results": {
                "pass": 8,
                "running": 0,
                "fail": 2
            }
        }
    }

The example above gives returns the three result types available for jobs:
``pass``, ``fail``, and ``running`` with its respective links. These are built
from the information for every run as the results come in. They are read-only
values. It will also report on the overall status of the run: running or
finished.

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
            "href": "http://paddles/runs/teuthology-2013-09-01_23:59:59-rados-master-testing-basic-plana/1500/",
            "status": "running",
            "results": {
                "pass": 8,
                "running": 13,
                "fail": 2
            }
        },
        "1501": {
            "href": "http://paddles/runs/teuthology-2013-09-01_23:59:59-rados-master-testing-basic-plana/1501/",
            "status": "finished",
            "results": {
                "pass": 8,
                "running": 0,
                "fail": 4
            }
        },
        "1502": {
            "href": "http://paddles/runs/teuthology-2013-09-01_23:59:59-rados-master-testing-basic-plana/1502/",
            "status": "finished",
            "results": {
                "pass": 3,
                "running": 0,
                "fail": 17
            }
        }
    }


``/runs/{name}/jobs/``
======================

Read
----
``GET`` requests will return a full list of all the jobs associated with the
current ``run``.

If no jobs exist, an empty array is returned, otherwise this is how a single
object would look like::

    [

        {
            "archive_path": null,
            "kernel": null,
            "teuthology_branch": null,
            "tasks": null,
            "verbose": null,
            "description": null,
            "roles": null,
            "overrides": null,
            "pid": null,
            "success": null,
            "name": null,
            "targets": null,
            "owner": null,
            "last_in_suite": null,
            "os_type": null,
            "machine_type": null,
            "nuke_on_error": null,
            "duration": null,
            "flavor": null,
            "email": null,
            "job_id": "1"
        }

    ]

Create
------
``POST`` requests with valid metadata for a job can create new jobs. Keys that
are not part of the schema **will be ignored**. Keys that are saved to the
database are:

* name
* email
* archive_path
* description
* duration
* flavor
* job_id
* kernel
* last_in_suite
* machine_type
* mon.a_kernel_sha1 (note this key gets transformed to underscores)
* mon.b_kernel_sha1 (note this key gets transformed to underscores)
* nuke_on_error
* os_type
* overrides
* owner
* pid
* roles
* success
* targets
* tasks
* teuthology_branch
* verbose
* branch
* sha1
* suite_sha1
* pcp_grafana_url

For initial creation of a ``job`` associated to its ``run`` a ``job_id`` key is
**required**. It is the only key in the JSON body that *must* exist, otherwise
a 400 error is returned.


HTTP responses:

* **200**: Success.
* **400**: Invalid request.
* **404**: The requested run was not found.

.. note:: updates for the results of these runs are programatically calculated
          from individual jobs


``/runs/{name}/jobs/{job_id}/``
===============================

Read
----
On ``GET`` requests an object with all metadata saved from the actual job will
be returned.


Update
------
``PUT`` requests can contain *any* of the keys accepted for metadata, they get
updated accordingly **except** for ``job_id``. That is the one key that can
never be changed.

* **200**: Success.
* **400**: Invalid request.
* **404**: The requested run was not found.

