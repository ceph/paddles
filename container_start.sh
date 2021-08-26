#!/usr/bin/env bash
set -ex
pecan populate config.py
CURRENT=$(alembic current)
if [ -z "$CURRENT" ]; then
  echo "No current revision; assuming no migration necessary"
  alembic stamp head
else
  echo "Current revision: $CURRENT - will attempt to migrate"
  alembic upgrade head
fi
gunicorn_pecan config.py
