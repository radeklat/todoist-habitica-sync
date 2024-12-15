ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

RUN apt-get --allow-releaseinfo-change update
RUN apt-get install build-essential libssl-dev libffi-dev python3-dev -y
RUN python -m pip install --upgrade pip

# Doesn't build consistently for armv7
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
RUN pip install "cryptography<3.5" poetry

COPY pyproject.toml poetry.lock ./

RUN poetry install --only=main --no-root

# PYTHONPATH set after install to prevent bugs
ENV PYTHONPATH="src"

COPY . .

ENTRYPOINT ["poetry", "run", "python", "src/main.py"]
