FROM alpine:3.24 AS repo

ARG ALPINE_VERSION=v3.24

RUN apk add --no-cache rsync

RUN mkdir -p /repo/${ALPINE_VERSION}/main/x86_64 \
                 /repo/${ALPINE_VERSION}/community/x86_64 \
 && rsync -a \
    rsync://rsync.alpinelinux.org/alpine/${ALPINE_VERSION}/main/x86_64/ \
    /repo/${ALPINE_VERSION}/main/x86_64/ \
 && rsync -a \
    rsync://rsync.alpinelinux.org/alpine/${ALPINE_VERSION}/community/x86_64/ \
    /repo/${ALPINE_VERSION}/community/x86_64/


# Eventually this stage becomes:
#
# FROM repo AS converted
# COPY my-package-converter /usr/local/bin/
# RUN convert-entire-repository /repo /converted-repo


FROM nginx:alpine

COPY --from=repo /repo /srv/alpine
COPY default.conf.template /etc/nginx/templates/default.conf.template