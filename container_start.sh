#!/usr/bin/env bash
set -ex
trap exit TERM
pecan populate config.py
CURRENT=$(alembic current)
if [ -z "$CURRENT" ]; then
  echo "No current revision; assuming no migration necessary"
  alembic stamp head
else
  echo "Current revision: $CURRENT - will attempt to migrate"
  alembic upgrade head
fi
gunicorn_pecan -c gunicorn_config.py config.py
