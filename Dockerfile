ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

RUN apt-get --allow-releaseinfo-change update
RUN apt-get install build-essential libssl-dev libffi-dev python3-dev cargo -y
RUN python -m pip install --upgrade pip
RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry install --without=dev --no-root

# PYTHONPATH set after install to prevent bugs
ENV PYTHONPATH="src"

COPY . .

ENTRYPOINT ["poetry", "run", "python", "src/main.py"]
