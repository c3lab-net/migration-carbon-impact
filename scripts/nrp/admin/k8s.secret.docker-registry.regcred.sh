#!/bin/zsh

# instructions: https://docs.pacificresearchplatform.org/userdocs/development/private-repos/

DOCKER_SERVER=gitlab-registry.nrp-nautilus.io
# DOCKER_SERVER=gitlab-registry.nrp-nautilus.io/c3lab/common
DOCKER_USERNAME=gitlab+deploy-token-XXX
read -s DOCKER_PASSWORD

kubectl create -n c3lab secret docker-registry regcred --docker-server=$DOCKER_SERVER --docker-username=$DOCKER_USERNAME --docker-password=$DOCKER_PASSWORD
