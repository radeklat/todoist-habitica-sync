ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y build-essential libssl-dev libffi-dev python3-dev rustc cargo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

# Doesn't build consistently for armv7
RUN pip install "cryptography" poetry

COPY pyproject.toml poetry.lock ./

RUN poetry install --without=dev --no-root

# PYTHONPATH set after install to prevent bugs
ENV PYTHONPATH="src"

COPY . .

ENTRYPOINT ["poetry", "run", "python", "src/main.py"]
