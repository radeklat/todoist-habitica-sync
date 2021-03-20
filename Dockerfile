FROM python:3.8.8-alpine

ARG unprivileged_user=app
ARG sources_root=/usr/src/${unprivileged_user}

RUN apk update \
  && apk add --no-cache bash openssl-dev gcc libffi-dev cargo \
  && rm -rf /var/lib/apt/lists/*

RUN adduser -u 1001 -D ${unprivileged_user}

WORKDIR ${sources_root}

COPY poetry.lock pyproject.toml poetry.toml ./

RUN apk add --virtual build-deps gcc python3-dev build-base musl-dev \
    && pip install -U pip poetry --no-cache-dir \
    && poetry install --no-dev --no-root \
    && apk del build-deps \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN chown -R ${unprivileged_user} ${sources_root}

ENV PYTHONPATH="${sources_root}"

USER ${unprivileged_user}

CMD poetry run python src/main.py
