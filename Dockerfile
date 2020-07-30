FROM ubuntu:18.04
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install \
  -y --no-install-recommends \
	curl \
	lsof \
	python3 \
	python3-alembic \
	python3-gunicorn \
	python3-pip \
	python3-setuptools \
	python3-wheel \
	tzdata

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
