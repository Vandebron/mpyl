FROM python:3.9.16-slim
WORKDIR /
COPY . ./
RUN pip install pipenv
RUN pipenv install --skip-lock --dev
RUN pipenv run build
