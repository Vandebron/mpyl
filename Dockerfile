ARG PYTHON_VERSION=3.11
FROM public.ecr.aws/vdb-public/python:${PYTHON_VERSION}-slim-bookworm AS base

USER root

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

RUN apt-get -y update && apt-get -y install git

# Switch to mpyl source code directory
WORKDIR /app/mpyl

COPY requirements.txt requirements.txt

# Install the dependencies.
RUN python -m pip install -r requirements.txt

# Copy the source code into the container.
COPY src/mpyl ./

# Set pythonpath for mpyl
ENV PYTHONPATH=/app

# Switch to the directory of the calling repo
WORKDIR /repo
COPY entrypoint.sh ../entrypoint.sh

# USER vdbnonroot  # Enable again after removing git from the src code

# Run the application.
ENTRYPOINT ["/entrypoint.sh"]
