ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim AS base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

RUN apt-get -y update && apt-get -y install git

WORKDIR /app/mpyl

COPY requirements.txt requirements.txt

RUN python -m pip install -r requirements.txt

# Copy the source code into the container.
COPY src/mpyl ./

ENV PYTHONPATH=/app

WORKDIR /repo

# Run the application.
ENTRYPOINT ["python", "/app/mpyl/__main__.py"]
