FROM python:3.11.4-alpine3.18

RUN apk update
RUN apk add git
RUN apk add --no-cache --virtual .pynacl_deps build-base python3-dev libffi-dev

RUN python -m pip install --upgrade pip

ARG MPYL_VERSION=198.2313
RUN pip install mpyl
RUN pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple mpyl==$MPYL_VERSION