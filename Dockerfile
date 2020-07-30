FROM ubuntu:18.04
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install \
  -y --no-install-recommends python python-pip python-setuptools python-wheel gunicorn tzdata curl lsof alembic

# Install dependencies:
COPY requirements.txt .
ADD . /paddles
RUN pip3 install -r requirements.txt
RUN pip3 install /paddles/.

# Run the application:
COPY config.py.in /paddles/config.py
COPY alembic.ini.in /paddles/alembic.ini
WORKDIR /paddles
CMD pecan populate config.py && alembic stamp head && gunicorn_pecan config.py
