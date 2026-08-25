FROM alpine:3.24 AS repo

ARG ALPINE_VERSION=v3.24

RUN apk add --no-cache rsync

RUN mkdir -p /repo/${ALPINE_VERSION}/main/x86_64
RUN rsync -a \
    rsync://rsync.alpinelinux.org/alpine/${ALPINE_VERSION}/main/x86_64/ \
    /repo/${ALPINE_VERSION}/main/x86_64/

# RUN mkdir -p /repo/${ALPINE_VERSION}/community/x86_64
# RUN rsync -a \
#     rsync://rsync.alpinelinux.org/alpine/${ALPINE_VERSION}/community/x86_64/ \
#     /repo/${ALPINE_VERSION}/community/x86_64/


FROM alpine:3.24 AS converter

RUN apk add --no-cache uv zip

WORKDIR /app

# Keep dependency resolution cached until the project metadata changes.
COPY pyproject.toml ./
RUN uv sync --no-install-project --no-dev

# Installing the project is a separate layer, so source changes do not cause
# dependencies to be resolved and downloaded again.
COPY README.md ./
COPY src/ ./src/
RUN uv sync --no-dev

COPY --from=repo /repo /repo
RUN uv run --no-sync apk2zpk /repo


FROM nginx:alpine

COPY --from=converter /repo /srv/alpine
COPY default.conf.template /etc/nginx/templates/default.conf.template
