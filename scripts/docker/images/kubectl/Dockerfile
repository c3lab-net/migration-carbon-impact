FROM alpine:3.17.2
MAINTAINER Yibo Guo <nil.yibo@gmail.com>

ARG K8S_VERSION=v1.23.14
ARG INSTALL_DIR=/tmp/install

RUN apk add --update curl

WORKDIR ${INSTALL_DIR}
RUN curl -sLO "https://dl.k8s.io/release/${K8S_VERSION}/bin/linux/amd64/kubectl"
RUN curl -sLO "https://dl.k8s.io/${K8S_VERSION}/bin/linux/amd64/kubectl.sha256" && \
    echo "$(cat kubectl.sha256)  kubectl" | sha256sum -c - || exit 1
RUN install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

RUN kubectl version --client

WORKDIR /
RUN rm -rf ${INSTALL_DIR}
RUN apk del --purge curl
