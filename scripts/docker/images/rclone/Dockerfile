FROM alpine:3.17.2
MAINTAINER Yibo Guo <nil.yibo@gmail.com>

ARG RCLONE_VERSION=1.61.1
ARG TMPDIR=/tmp/rclone-build

RUN apk add --update curl

# Source: https://rclone.org/install/

## Fetch and unpack
WORKDIR ${TMPDIR}
RUN curl -s -O https://downloads.rclone.org/v${RCLONE_VERSION}/rclone-v${RCLONE_VERSION}-linux-amd64.zip && \
    unzip rclone-v${RCLONE_VERSION}-linux-amd64.zip

WORKDIR ${TMPDIR}/rclone-v${RCLONE_VERSION}-linux-amd64

## Copy binary file
RUN cp rclone /usr/bin/ && \
    chown root:root /usr/bin/rclone && \
    chmod 755 /usr/bin/rclone

## Install manpage (not needed)
# RUN mkdir -p /usr/local/share/man/man1 && \
#     cp rclone.1 /usr/local/share/man/man1/ && \
#     mandb

## Clean up
RUN rm -rf ${TMPDIR}

## Show rclone configuration file location
RUN unset RCLONE_VERSION && rclone config file

ENTRYPOINT ["rclone"]
