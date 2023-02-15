#!/bin/zsh

if [ $# -lt 2 ]; then
    echo >&2 "Usage: $0 project-name image-name [version]"
    exit 1
fi

PROJECT_NAME="$1"
IMAGE_NAME="$2"
IMAGE_VERSION="${3:-latest}"

FULL_IMAGE_NAME=gitlab-registry.nrp-nautilus.io/c3lab/$PROJECT_NAME/$IMAGE_NAME:$IMAGE_VERSION

set -e

echo "Building image $FULL_IMAGE_NAME ..."
(set -x; docker build -t $FULL_IMAGE_NAME .)

echo Done
echo "Run this to push to registry:"
echo "docker push $FULL_IMAGE_NAME"

