FROM python:3.7.1-alpine3.8

ARG unprivileged_user=app
ARG sources_root=/usr/src/${unprivileged_user}

# common for all microservices
RUN apk update \
  && apk add --no-cache bash openssh \
  && rm -rf /var/lib/apt/lists/*

RUN adduser -u 1001 -D ${unprivileged_user}

WORKDIR ${sources_root}

COPY requirements.txt ./

RUN apk add --virtual build-deps gcc python3-dev python-dev build-base musl-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del build-deps \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN chown -R ${unprivileged_user} ${sources_root}

ENV PYTHONPATH="${sources_root}"

USER ${unprivileged_user}

CMD python src/main.py
