FROM python:3.9.1

RUN apt-get update && apt install -y locales libcurl4-openssl-dev libssl-dev \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app/

RUN pip install poetry==1.1.5
COPY pyproject.toml poetry.lock /app/
RUN poetry config virtualenvs.create false && poetry install --no-interaction #!COMMIT

ENV PYTHONUNBUFFERED 1

COPY . /app/

LABEL CONSUL_SERVICE_NAME consul-docker-autosync
LABEL CONSUL_SERVICE_PORT 14400
LABEL CONSUL_SERVICE_CHECK_HTTP http://localhost:14400/health
LABEL CONSUL_SERVICE_CHECK_SUCCESS_BEFORE_PASSING 3
LABEL CONSUL_SERVICE_CHECK_FAILURES_BEFORE_CRITICAL 3
ENV LOGURU_LEVEL INFO
EXPOSE 14400

ENTRYPOINT ["poetry", "run", "cli"]
