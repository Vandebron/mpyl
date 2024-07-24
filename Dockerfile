ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim AS base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

RUN apt-get -y update && apt-get -y install git curl apt-transport-https gnupg unzip zip

# Install Docker
RUN curl -fsSL https://get.docker.com -o get-docker.sh && sh ./get-docker.sh

# Install java and sbt
RUN curl -s "https://get.sdkman.io?rcupdate=false" | bash
RUN bash -c "source /root/.sdkman/bin/sdkman-init.sh && sdk install java && sdk install sbt"
ENV PATH=/root/.sdkman/candidates/java/current/bin:$PATH
ENV PATH=/root/.sdkman/candidates/sbt/current/bin:$PATH

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

# Run the application.
ENTRYPOINT ["/entrypoint.sh"]
