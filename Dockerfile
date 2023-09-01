FROM python:3.11-alpine
EXPOSE 8080
ENV TZ="UTC"
RUN apk add curl tzdata && \
  pip install -U pip

# Install dependencies:
COPY requirements.txt .
ADD . /paddles
RUN pip3 install -r requirements.txt
RUN pip3 install /paddles/.

# Run the application:
COPY config.py.in /paddles/config.py
COPY alembic.ini.in /paddles/alembic.ini
COPY container_start.sh /paddles/container_start.sh
WORKDIR /paddles
CMD sh container_start.sh
